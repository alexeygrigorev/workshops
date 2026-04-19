# Deploy Your AI Agent Project to Production with FastAPI and a Vector DB

This workshop is a part of [AI Shipping Labs](https://luma.com/j1zzd47e).

- Event: https://luma.com/j1zzd47e
- Video: [TODO: Add YouTube link]

Most AI projects stop at "it works in my notebook". In this workshop we
turn a RAG/agent prototype into a small but production-shaped backend:

- A FastAPI service that exposes clean endpoints
- A vector database (Qdrant) as the retrieval layer
- An ingestion/indexing pipeline for documents
- A grounded `/ask` endpoint powered by an LLM
- Containerization and a deployment path

By the end you will have a deployable skeleton you can extend with your
own data, agents, and tools.


## Prerequisites

- Python 3.13+
- Docker
- OpenAI API key


## What We Will Build

We will build an FAQ assistant around the
[DataTalks.Club zoomcamp FAQ documents](https://raw.githubusercontent.com/DataTalksClub/llm-zoomcamp/refs/heads/main/03-evaluation/search_evaluation/documents-with-ids.json),
but the same structure works for any corpus.

Architecture:

```
[ documents ] --> [ ingest.py ] --> [ Qdrant ]
                                       ^
                                       |
[ client ] -->  [ FastAPI /search /ask /index ] --> [ OpenAI ]
```


## Environment Setup

Initialize the project with [uv](https://docs.astral.sh/uv/):

```bash
uv init agent-fastapi-vectordb
cd agent-fastapi-vectordb
uv add fastapi uvicorn openai qdrant-client fastembed requests
uv add --dev jupyter
```

Export your OpenAI key:

```bash
export OPENAI_API_KEY="sk-..."
```


## Start Qdrant

We will use [Qdrant](https://qdrant.tech/) as the vector database. The
easiest way to get it running locally is Docker:

```bash
docker run -d --name qdrant -p 6333:6333 \
    -v $(pwd)/qdrant_storage:/qdrant/storage \
    qdrant/qdrant:latest
```

Open the dashboard at http://localhost:6333/dashboard to confirm it is
up.


## From Prototype to Service

A typical RAG prototype looks like this:

```python
def rag(question):
    results = search(question)
    prompt = build_prompt(question, results)
    return llm(prompt)
```

That works in a notebook, but in production we need:

- A **persistent** retrieval layer (not a dict we rebuild every run)
- **Typed** inputs and outputs
- **Stable** endpoints that clients can call
- A way to **re-index** documents without restarting

FastAPI + Qdrant give us all four.


## Ingestion Pipeline

Create [`ingest.py`](ingest.py) that:

1. Loads FAQ documents
2. Creates a Qdrant collection
3. Embeds each document and upserts it with its payload

```python
import requests
from qdrant_client import QdrantClient, models

DOCS_URL = (
    "https://raw.githubusercontent.com/DataTalksClub/llm-zoomcamp/"
    "refs/heads/main/03-evaluation/search_evaluation/documents-with-ids.json"
)

COLLECTION_NAME = "faq"
EMBEDDING_MODEL = "jinaai/jina-embeddings-v2-small-en"
EMBEDDING_DIM = 512


def load_documents():
    return requests.get(DOCS_URL).json()


def recreate_collection(client):
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=EMBEDDING_DIM,
            distance=models.Distance.COSINE,
        ),
    )


def index_documents(client, documents):
    points = []
    for i, doc in enumerate(documents):
        text = f"{doc['question']}\n\n{doc['text']}"
        point = models.PointStruct(
            id=i,
            vector=models.Document(text=text, model=EMBEDDING_MODEL),
            payload=doc,
        )
        points.append(point)

    client.upsert(collection_name=COLLECTION_NAME, points=points)
```

`qdrant-client` with `fastembed` computes embeddings locally for us.
No extra embedding API is required.

Run it:

```bash
uv run python ingest.py
```


## A Minimal FastAPI App

Start with the simplest possible app in `app.py`:

```python
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="faq-agent")

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9696)
```

Run it:

```bash
uv run uvicorn app:app --host 0.0.0.0 --port 9696 --reload
```

Docs are available at http://localhost:9696/docs — free with FastAPI.


## The `/search` Endpoint

The first real endpoint: vector search over the FAQ collection.

```python
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from qdrant_client import QdrantClient, models

qdrant = QdrantClient("http://localhost:6333")


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1)
    course: Optional[str] = None
    limit: int = Field(5, ge=1, le=20)


class SearchHit(BaseModel):
    id: int
    score: float
    question: str
    text: str
    section: str
    course: str


class SearchResponse(BaseModel):
    hits: list[SearchHit]


def search_qdrant(query, course, limit):
    query_filter = None
    if course:
        query_filter = models.Filter(
            must=[models.FieldCondition(
                key="course",
                match=models.MatchValue(value=course),
            )]
        )

    results = qdrant.query_points(
        collection_name="faq",
        query=models.Document(text=query, model=EMBEDDING_MODEL),
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    )

    hits = []
    for point in results.points:
        payload = point.payload or {}
        hits.append(SearchHit(
            id=int(point.id),
            score=float(point.score),
            question=payload.get("question", ""),
            text=payload.get("text", ""),
            section=payload.get("section", ""),
            course=payload.get("course", ""),
        ))
    return hits


@app.post("/search")
def search(req: SearchRequest) -> SearchResponse:
    hits = search_qdrant(req.query, req.course, req.limit)
    return SearchResponse(hits=hits)
```

Pydantic models give us:

- **Input validation** — bad requests get a 422 automatically
- **Typed responses** — OpenAPI schema is generated for free
- **`extra="forbid"`** — catches typos in client code early


## The `/ask` Endpoint — Grounded Answers

Now wire an LLM on top of search to get a grounded answer:

```python
from openai import OpenAI

openai_client = OpenAI()

INSTRUCTIONS = (
    "You're a course teaching assistant. Answer the QUESTION using only "
    "facts from the CONTEXT. If the context is not sufficient, say so."
)


def build_prompt(question, hits):
    context = "\n\n".join(
        f"section: {h.section}\nquestion: {h.question}\nanswer: {h.text}"
        for h in hits
    )
    return f"<QUESTION>\n{question}\n</QUESTION>\n\n<CONTEXT>\n{context}\n</CONTEXT>"


def llm(question, hits):
    response = openai_client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": build_prompt(question, hits)},
        ],
    )
    return response.output_text


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1)
    course: Optional[str] = None
    limit: int = Field(5, ge=1, le=20)


class AskResponse(BaseModel):
    answer: str
    sources: list[SearchHit]


@app.post("/ask")
def ask(req: AskRequest) -> AskResponse:
    hits = search_qdrant(req.question, req.course, req.limit)
    answer = llm(req.question, hits)
    return AskResponse(answer=answer, sources=hits)
```

We return the sources alongside the answer — this makes the service
auditable, and makes it possible for a frontend to show citations.


## The `/index` Endpoint — Adding Documents at Runtime

A production-ready service should let you add new documents without
redeploying:

```python
class IndexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    question: str
    text: str
    section: str
    course: str


@app.post("/index")
def index(doc: IndexRequest):
    point = models.PointStruct(
        id=doc.id,
        vector=models.Document(
            text=f"{doc.question}\n\n{doc.text}",
            model=EMBEDDING_MODEL,
        ),
        payload=doc.model_dump(),
    )
    qdrant.upsert(collection_name="faq", points=[point])
    return {"status": "indexed", "id": doc.id}
```

The full app is in [`app.py`](app.py).


## Testing the Service

Create [`test.py`](test.py):

```python
import requests

URL = "http://localhost:9696"

resp = requests.post(f"{URL}/ask", json={
    "question": "I just discovered the course, can I still join?",
    "course": "data-engineering-zoomcamp",
})
print(resp.json())
```

Run it:

```bash
uv run python test.py
```

You can also hit the endpoints from the auto-generated docs at
http://localhost:9696/docs.


## Containerize the App

[`Dockerfile`](Dockerfile):

```dockerfile
FROM python:3.13.5-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /code

ENV PATH="/code/.venv/bin:$PATH"

COPY "pyproject.toml" "uv.lock" ".python-version" ./
RUN uv sync --locked

COPY "app.py" ./

EXPOSE 9696

ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9696"]
```

Build it:

```bash
docker build -t agent-fastapi-vectordb .
```


## Run Everything with Docker Compose

To bring up both Qdrant and our app, use
[`docker-compose.yml`](docker-compose.yml):

```bash
export OPENAI_API_KEY="sk-..."
docker compose up --build
```

Then run the ingestion once against the container:

```bash
QDRANT_URL=http://localhost:6333 uv run python ingest.py
```

And test:

```bash
uv run python test.py
```


## Deployment

Once containerized, you can deploy this anywhere — Fly.io, Google Cloud
Run, AWS App Runner, Render, a VM.

We will use [Fly.io](https://fly.io/) because it takes about three
commands:

```bash
# install flyctl if needed
curl -L https://fly.io/install.sh | sh

fly auth signup

# the app service
fly launch --generate-name --no-deploy

# attach a Qdrant machine (Fly supports private networking between apps)
# or point QDRANT_URL at a managed Qdrant Cloud cluster

fly deploy
```

Get the URL from the logs, update `URL` in `test.py`, and verify.

When you're done:

```bash
fly apps destroy <app-name>
```

Note: check pricing before leaving anything running.


## Where to Go From Here

This service is a foundation, not a finish line. Natural next steps:

- Replace the single LLM call with an **agent** that can choose between
  `/search`, `/index`, and external tools
- Add **evaluation** on top (see
  [rag-evaluations](../rag-evaluations/))
- Add **guardrails** (see [guardrails](../guardrails/))
- Wrap it with **MCP** so other agents can call it (see
  [agents-mcp](../agents-mcp/))
- Add observability: request logging, latency, retrieval quality
- Swap the embedding model or add a re-ranker


## Summary

In this workshop we took a RAG prototype and turned it into a small
production-shaped service:

- Structured the code around FastAPI endpoints
- Used Qdrant as a persistent retrieval layer
- Validated inputs and outputs with Pydantic
- Containerized the app and prepared it for deployment
