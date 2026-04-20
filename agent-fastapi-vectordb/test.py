import json

import requests


URL = "http://localhost:9696"
# URL = "https://agent-fastapi-vectordb.fly.dev"


def ask(question: str, course: str = None):
    response = requests.post(
        f"{URL}/api/ask",
        json={"question": question, "course": course},
        headers={"Accept": "text/event-stream"},
        stream=True,
    )

    for raw_line in response.iter_lines():
        if not raw_line:
            continue
        line = raw_line.decode("utf-8")
        if not line.startswith("data: "):
            continue

        event = json.loads(line[6:])
        t = event["type"]

        if t == "token":
            print(event["delta"], end="", flush=True)
        elif t == "tool_call":
            print(f"\n[tool_call] {event['name']}({event['arguments']})")
        elif t == "tool_result":
            count = len(event["result"]) if isinstance(event["result"], list) else "?"
            print(f"[tool_result] {event['name']} -> {count} hits")
        elif t == "iteration":
            print(f"\n--- iteration {event['n']} ---")
        elif t == "status":
            print(f"[{event['message']}]")
        elif t == "done":
            if event.get("answer"):
                print(f"\n\n[done]\n{event['answer']}")
            else:
                print("\n[done]")
            return


if __name__ == "__main__":
    ask(
        "I just discovered the course, can I still join?",
        course="llm-zoomcamp",
    )
