import os
from typing import Optional

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field, ConfigDict
from qdrant_client import QdrantClient, models
from openai import OpenAI


COLLECTION_NAME = "faq"
EMBEDDING_MODEL = "jinaai/jina-embeddings-v2-small-en"

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

qdrant = QdrantClient(QDRANT_URL)
openai_client = OpenAI()

app = FastAPI(title="faq-agent")


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


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1)
    course: Optional[str] = None
    limit: int = Field(5, ge=1, le=20)


class AskResponse(BaseModel):
    answer: str
    sources: list[SearchHit]


class IndexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    question: str
    text: str
    section: str
    course: str


def search_qdrant(query: str, course: Optional[str], limit: int):
    query_filter = None
    if course:
        query_filter = models.Filter(
            must=[models.FieldCondition(key="course", match=models.MatchValue(value=course))]
        )

    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=models.Document(text=query, model=EMBEDDING_MODEL),
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    )

    hits = []
    for point in results.points:
        payload = point.payload or {}
        hits.append(
            SearchHit(
                id=int(point.id),
                score=float(point.score),
                question=payload.get("question", ""),
                text=payload.get("text", ""),
                section=payload.get("section", ""),
                course=payload.get("course", ""),
            )
        )
    return hits


INSTRUCTIONS = (
    "You're a course teaching assistant. Answer the QUESTION using only "
    "facts from the CONTEXT. If the context is not sufficient, say so."
)


def build_prompt(question: str, hits: list[SearchHit]) -> str:
    context = "\n\n".join(
        f"section: {h.section}\nquestion: {h.question}\nanswer: {h.text}" for h in hits
    )
    return f"<QUESTION>\n{question}\n</QUESTION>\n\n<CONTEXT>\n{context}\n</CONTEXT>"


def llm(question: str, hits: list[SearchHit]) -> str:
    response = openai_client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": build_prompt(question, hits)},
        ],
    )
    return response.output_text


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/search")
def search(req: SearchRequest) -> SearchResponse:
    hits = search_qdrant(req.query, req.course, req.limit)
    return SearchResponse(hits=hits)


@app.post("/ask")
def ask(req: AskRequest) -> AskResponse:
    hits = search_qdrant(req.question, req.course, req.limit)
    answer = llm(req.question, hits)
    return AskResponse(answer=answer, sources=hits)


@app.post("/index")
def index(doc: IndexRequest):
    point = models.PointStruct(
        id=doc.id,
        vector=models.Document(
            text=f"{doc.question}\n\n{doc.text}", model=EMBEDDING_MODEL
        ),
        payload=doc.model_dump(),
    )
    qdrant.upsert(collection_name=COLLECTION_NAME, points=[point])
    return {"status": "indexed", "id": doc.id}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9696)
