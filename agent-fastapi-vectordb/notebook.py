import asyncio

from engine import FAQAgentEngine
from search import get_search_backend


async def print_event(event_type: str, payload: dict):
    if event_type == "token":
        print(payload["delta"], end="", flush=True)
        return

    if event_type == "status":
        print(f"[{payload['message']}]")
        return

    if event_type == "iteration":
        print(f"\n--- iteration {payload['n']} ---")
        return

    if event_type == "tool_call":
        print(f"\n[tool_call] {payload['name']}({payload['arguments']})")
        return

    if event_type == "tool_result":
        count = len(payload["result"]) if isinstance(payload["result"], list) else "?"
        print(f"[tool_result] {payload['name']} -> {count} hits")
        return

    if event_type == "done":
        print(f"\n\n[done]\n{payload['answer']}")


async def main():
    engine = FAQAgentEngine(search_backend=get_search_backend())
    await engine.run(
        "I just discovered the course, can I still join?",
        course="llm-zoomcamp",
        on_event=print_event,
    )


if __name__ == "__main__":
    asyncio.run(main())
