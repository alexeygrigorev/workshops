import json
import os
from collections.abc import Awaitable, Callable

from openai import AsyncOpenAI


MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_ITERATIONS = 5

EventCallback = Callable[[str, dict], Awaitable[None]]

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


async def noop_callback(_event_type: str, _payload: dict):
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
        course: str | None = None,
        on_event: EventCallback = noop_callback,
    ):
        await self.emit(on_event, "status", message="thinking...")
        message_history = self.build_message_history(question, course)

        for iteration in range(1, self.max_iterations + 1):
            await self.emit(on_event, "iteration", n=iteration)

            final = await self.stream_model_response(message_history, on_event)
            message_history.extend(final.output)

            tool_calls = self.extract_tool_calls(final.output)
            if not tool_calls:
                answer = self.collect_response_text(final.output)
                await self.emit(on_event, "done", answer=answer)
                return answer

            await self.handle_tool_calls(tool_calls, message_history, on_event)

        answer = "(stopped: reached max iterations)"
        await self.emit(on_event, "done", answer=answer)
        return answer

    async def emit(self, on_event: EventCallback, event_type: str, **payload):
        await on_event(event_type, payload)

    def build_message_history(self, question: str, course: str | None = None):
        if course:
            user_message = f"[course hint: {course}]\n{question}"
        else:
            user_message = question

        return [
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": user_message},
        ]

    async def stream_model_response(self, message_history, on_event: EventCallback):
        async with self.openai_client.responses.stream(
            model=self.model_name,
            input=message_history,
            tools=[search_tool],
        ) as stream:
            async for event in stream:
                if event.type == "response.output_text.delta":
                    await self.emit(on_event, "token", delta=event.delta)

            return await stream.get_final_response()

    def extract_tool_calls(self, response_output):
        return [item for item in response_output if item.type == "function_call"]

    async def handle_tool_calls(self, tool_calls, message_history, on_event: EventCallback):
        for tool_call in tool_calls:
            args = json.loads(tool_call.arguments)
            await self.emit(
                on_event,
                "tool_call",
                name=tool_call.name,
                arguments=args,
            )

            tool_output = self.make_tool_output(tool_call)
            message_history.append(tool_output)

            result = json.loads(tool_output["output"])
            await self.emit(
                on_event,
                "tool_result",
                name=tool_call.name,
                result=self.preview_result(result),
            )

    def make_tool_output(self, tool_call):
        args = json.loads(tool_call.arguments)

        if tool_call.name == "search":
            result = self.search_backend.search(**args)
        else:
            result = {"error": f"unknown tool: {tool_call.name}"}

        return {
            "type": "function_call_output",
            "call_id": tool_call.call_id,
            "output": json.dumps(result),
        }

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

    def collect_response_text(self, response_output):
        parts = []
        for item in response_output:
            if item.type != "message":
                continue

            for content in item.content:
                if getattr(content, "text", None):
                    parts.append(content.text)

        return "".join(parts)
