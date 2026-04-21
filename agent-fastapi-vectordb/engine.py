import json
import os
from typing import Protocol

from openai import AsyncOpenAI


MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_ITERATIONS = 5


class Renderer(Protocol):
    async def handle_event(self, event_type: str, payload: dict): ...

search_tool = {
    "type": "function",
    "name": "search",
    "description": "Search the DataTalks.Club FAQ knowledge base.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for.",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
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


class NullRenderer:
    async def handle_event(self, _event_type: str, _payload: dict):
        return None


class FAQAgentEngine:
    def __init__(
        self,
        search_backend,
        openai_client: AsyncOpenAI | None = None,
        model_name: str = MODEL_NAME,
        max_iterations: int = MAX_ITERATIONS,
    ):
        self.search_backend = search_backend
        self.openai_client = openai_client or AsyncOpenAI()
        self.model_name = model_name
        self.max_iterations = max_iterations

    async def run(
        self,
        question: str,
        renderer: Renderer | None = None,
        course: str | None = None,
    ):
        renderer = renderer or NullRenderer()
        await renderer.handle_event("status", {"message": "thinking..."})
        message_history = self.build_message_history(question)

        for iteration in range(1, self.max_iterations + 1):
            await renderer.handle_event("iteration", {"n": iteration})

            response = await self.request_response(message_history, renderer)

            has_tool_calls = await self.handle_tool_calls(
                response,
                message_history,
                renderer,
                course,
            )
            if not has_tool_calls:
                answer = self.collect_answer(response)
                await renderer.handle_event("done", {"answer": answer})
                return answer

        answer = "(stopped: reached max iterations)"
        await renderer.handle_event("done", {"answer": answer})
        return answer

    def build_message_history(self, question: str):
        return [
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": question},
        ]

    async def request_response(self, message_history, renderer: Renderer):
        async with self.openai_client.responses.stream(
            model=self.model_name,
            input=message_history,
            tools=[search_tool],
        ) as stream:
            async for event in stream:
                if event.type == "response.output_text.delta":
                    await renderer.handle_event("token", {"delta": event.delta})

            return await stream.get_final_response()

    def append_tool_messages(self, message_history, tool_call, result):
        message_history.append(
            {
                "type": "function_call",
                "call_id": tool_call.call_id,
                "name": tool_call.name,
                "arguments": tool_call.arguments,
            }
        )
        message_history.append(
            {
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": json.dumps(result),
            }
        )

    async def handle_tool_calls(
        self,
        response,
        message_history,
        renderer: Renderer,
        course: str | None = None,
    ):
        has_tool_calls = False

        for item in response.output:
            if item.type != "function_call":
                continue

            has_tool_calls = True

            args = json.loads(item.arguments)
            await renderer.handle_event(
                "tool_call",
                {"name": item.name, "arguments": args},
            )

            result = self.call_tool(item, course=course)
            await renderer.handle_event(
                "tool_result",
                {"name": item.name, "result": self.preview_result(result)},
            )

            self.append_tool_messages(message_history, item, result)

        return has_tool_calls

    def call_tool(self, tool_call, course: str | None = None):
        args = json.loads(tool_call.arguments)

        if tool_call.name != "search":
            return {"error": f"unknown tool: {tool_call.name}"}

        return self.search_backend.search(query=args["query"], course=course)

    def preview_result(self, result):
        if not isinstance(result, list):
            return result

        preview = []
        for hit in result:
            preview.append(
                {
                    "id": hit.get("id"),
                    "course": hit.get("course"),
                    "question": hit.get("question"),
                    "score": round(hit.get("score", 0.0), 3),
                }
            )
        return preview

    def collect_answer(self, response):
        parts = []
        for item in response.output:
            if item.type != "message":
                continue

            for content in item.content:
                if getattr(content, "text", None):
                    parts.append(content.text)

        return "".join(parts)
