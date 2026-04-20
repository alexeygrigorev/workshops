import json
import os
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sse_starlette.sse import EventSourceResponse

from openai import AsyncOpenAI
from qdrant_client import QdrantClient, models


COLLECTION_NAME = "faq"
EMBEDDING_MODEL = "jinaai/jina-embeddings-v2-small-en"
MODEL_NAME = "gpt-4o-mini"
MAX_ITERATIONS = 5

qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL", "http://localhost:6333"),
    api_key=os.getenv("QDRANT_API_KEY"),
)
openai_client = AsyncOpenAI()

app = FastAPI(title="faq-agent")


search_tool = {
    "type": "function",
    "name": "search",
    "description": "Search the DataTalks.Club FAQ knowledge base using semantic search.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for.",
            },
            "course": {
                "type": "string",
                "description": (
                    "Filter to a specific course. "
                    "One of: llm-zoomcamp, ml-zoomcamp, mlops-zoomcamp, "
                    "data-engineering-zoomcamp. Omit to search all courses."
                ),
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}


def search(query: str, course: Optional[str] = None, limit: int = 5):
    query_filter = None
    if course:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="course",
                    match=models.MatchValue(value=course),
                )
            ]
        )

    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=models.Document(text=query, model=EMBEDDING_MODEL),
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    )

    hits = []
    for p in results.points:
        payload = p.payload or {}
        hits.append(
            {
                "id": payload.get("id"),
                "course": payload.get("course"),
                "section": payload.get("section"),
                "question": payload.get("question"),
                "answer": payload.get("answer"),
                "score": float(p.score),
            }
        )
    return hits


def make_call(tool_call):
    args = json.loads(tool_call.arguments)
    if tool_call.name == "search":
        result = search(**args)
    else:
        result = {"error": f"unknown tool: {tool_call.name}"}

    return {
        "type": "function_call_output",
        "call_id": tool_call.call_id,
        "output": json.dumps(result),
    }


INSTRUCTIONS = """
You're a teaching assistant for DataTalks.Club zoomcamps.

Answer the user's question using the FAQ knowledge base. Use the `search`
tool to look things up. You can call search multiple times with different
queries to explore the topic well.

Rules:
- Use only facts from the search results.
- If the answer isn't in the results, say so clearly.
- At the end, list the FAQ entries you used under a "Sources" section,
  one per line in the form: `- [id] section > question`.
""".strip()


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1)
    course: Optional[str] = None


def sse(type_: str, **payload) -> dict:
    return {"data": json.dumps({"type": type_, **payload})}


async def run_agent(question: str, course: Optional[str]):
    yield sse("status", message="thinking...")

    if course:
        user_message = f"[course hint: {course}]\n{question}"
    else:
        user_message = question

    message_history = [
        {"role": "system", "content": INSTRUCTIONS},
        {"role": "user", "content": user_message},
    ]

    for iteration in range(1, MAX_ITERATIONS + 1):
        yield sse("iteration", n=iteration)

        async with openai_client.responses.stream(
            model=MODEL_NAME,
            input=message_history,
            tools=[search_tool],
        ) as stream:
            async for event in stream:
                if event.type == "response.output_text.delta":
                    yield sse("token", delta=event.delta)

            final = await stream.get_final_response()

        message_history.extend(final.output)

        tool_calls = [m for m in final.output if m.type == "function_call"]

        for tc in tool_calls:
            args = json.loads(tc.arguments)
            yield sse("tool_call", name=tc.name, arguments=args)

            tool_output = make_call(tc)
            message_history.append(tool_output)

            result = json.loads(tool_output["output"])
            if isinstance(result, list):
                preview = [
                    {
                        "id": h.get("id"),
                        "course": h.get("course"),
                        "question": h.get("question"),
                        "score": round(h.get("score", 0.0), 3),
                    }
                    for h in result
                ]
            else:
                preview = result
            yield sse("tool_result", name=tc.name, result=preview)

        if not tool_calls:
            final_text = ""
            for m in final.output:
                if m.type == "message":
                    for c in m.content:
                        if getattr(c, "text", None):
                            final_text += c.text
            yield sse("done", answer=final_text)
            return

    yield sse("done", answer="(stopped: reached max iterations)")


@app.post("/api/ask")
async def ask(req: AskRequest):
    return EventSourceResponse(run_agent(req.question, req.course))


@app.get("/api/courses")
def courses():
    return {
        "courses": [
            {"id": "llm-zoomcamp", "name": "LLM Zoomcamp"},
            {"id": "ml-zoomcamp", "name": "ML Zoomcamp"},
            {"id": "mlops-zoomcamp", "name": "MLOps Zoomcamp"},
            {"id": "data-engineering-zoomcamp", "name": "Data Engineering Zoomcamp"},
        ]
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9696)
