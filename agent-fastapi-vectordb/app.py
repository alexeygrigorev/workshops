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


class SseRenderer:
    def __init__(self):
        self.queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def handle_event(self, event_type: str, payload: dict):
        handler = getattr(self, f"handle_{event_type}", self.handle_unknown)
        await handler(payload)

    async def handle_status(self, payload: dict):
        await self.enqueue("status", payload)

    async def handle_iteration(self, payload: dict):
        await self.enqueue("iteration", payload)

    async def handle_tool_call(self, payload: dict):
        await self.enqueue("tool_call", payload)

    async def handle_tool_result(self, payload: dict):
        await self.enqueue("tool_result", payload)

    async def handle_token(self, payload: dict):
        await self.enqueue("token", payload)

    async def handle_done(self, payload: dict):
        await self.enqueue("done", payload)

    async def handle_unknown(self, payload: dict):
        await self.enqueue("status", {"message": str(payload)})

    async def enqueue(self, event_type: str, payload: dict):
        await self.queue.put(sse(event_type, **payload))

    async def finish(self):
        await self.queue.put(None)


async def run_agent_stream(question: str, course: Optional[str]):
    renderer = SseRenderer()

    async def runner():
        try:
            await engine.run(question, renderer, course=course)
        except Exception as exc:
            await renderer.handle_event("status", {"message": f"error: {exc}"})
            await renderer.handle_event("done", {"answer": ""})
        finally:
            await renderer.finish()

    task = asyncio.create_task(runner())

    try:
        while True:
            event = await renderer.queue.get()
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
