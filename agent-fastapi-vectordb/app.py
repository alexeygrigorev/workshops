import asyncio
import json
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sse_starlette.sse import EventSourceResponse

from engine import FAQAgentEngine
from faq import COURSES
from search import get_search_backend

app = FastAPI(title="faq-agent")
engine = FAQAgentEngine(search_backend=get_search_backend())


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1)
    course: Optional[str] = None


def sse(type_: str, **payload) -> dict:
    return {"data": json.dumps({"type": type_, **payload})}


async def run_agent_stream(question: str, course: Optional[str]):
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def on_event(event_type: str, payload: dict):
        await queue.put(sse(event_type, **payload))

    async def runner():
        try:
            await engine.run(question, course, on_event=on_event)
        except Exception as exc:
            await queue.put(sse("status", message=f"error: {exc}"))
            await queue.put(sse("done", answer=""))
        finally:
            await queue.put(None)

    task = asyncio.create_task(runner())

    try:
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event
    finally:
        await task


@app.post("/api/ask")
async def ask(req: AskRequest):
    return EventSourceResponse(run_agent_stream(req.question, req.course))


@app.get("/api/courses")
def courses():
    return {"courses": COURSES}


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9696)
