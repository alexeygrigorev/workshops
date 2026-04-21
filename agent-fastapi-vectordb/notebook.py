import asyncio

from engine import FAQAgentEngine
from search import get_search_backend


class NotebookRenderer:
    async def handle_event(self, event_type: str, payload: dict):
        handler = getattr(self, f"handle_{event_type}", self.handle_unknown)
        await handler(payload)

    async def handle_status(self, payload: dict):
        print(f"[{payload['message']}]")

    async def handle_iteration(self, payload: dict):
        print(f"\n--- iteration {payload['n']} ---")

    async def handle_tool_call(self, payload: dict):
        print(f"\n[tool_call] {payload['name']}({payload['arguments']})")

    async def handle_tool_result(self, payload: dict):
        count = len(payload["result"]) if isinstance(payload["result"], list) else "?"
        print(f"[tool_result] {payload['name']} -> {count} hits")

    async def handle_token(self, payload: dict):
        print(payload["delta"], end="", flush=True)

    async def handle_done(self, payload: dict):
        print(f"\n\n[done]\n{payload['answer']}")

    async def handle_unknown(self, payload: dict):
        print(payload)


async def main():
    engine = FAQAgentEngine(search_backend=get_search_backend())
    renderer = NotebookRenderer()
    await engine.run(
        "I just discovered the course, can I still join?",
        renderer,
        course="data-engineering-zoomcamp",
    )


if __name__ == "__main__":
    asyncio.run(main())
