import uuid

from typing import Any
from pydantic import TypeAdapter
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import FunctionToolCallEvent, ModelMessage
from pydantic_ai.durable_exec.temporal import (
    TemporalAgent,
    PydanticAIPlugin,
    PydanticAIWorkflow,
    TemporalRunContext
)

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker


with workflow.unsafe.imports_passed_through():
    from tools import SearchTools, SummarizationTools
    from elasticsearch import Elasticsearch


class NamedCallback:
    """Stream handler that prints the tool calls triggered by an agent."""

    def __init__(self, agent: Agent):
        self.agent_name = agent.name

    async def _print_function_calls(self, ctx, event) -> None:
        # Detect nested streams
        if hasattr(event, "__aiter__"):
            async for sub_event in event:
                await self._print_function_calls(ctx, sub_event)
            return

        if isinstance(event, FunctionToolCallEvent):
            tool_name = event.part.tool_name
            args = event.part.args
            print(f"TOOL CALL ({self.agent_name}): {tool_name}({args})")

    async def __call__(self, ctx, event) -> None:
        await self._print_function_calls(ctx, event)



summarization_instructions = """
Your task is to summarize the provided YouTube transcript for a specific topic.

Select the parts of the transcripts that are relevant for the topic and search queries.

Format: 
paragraph with discussion (timestamp)
""".strip()


def create_summarization_agent() -> Agent:
    return Agent(
        name='summarization',
        instructions=summarization_instructions,
        model='openai:gpt-4o-mini'
    )


research_instructions = """
You are an autonomous research agent. Your goal is to perform deep, multi-stage research on the
given topic using the available search function.

Research process:

Stage 1: Initial Exploration  
- Using your own knowledge of the topic, perform 3-5 broad search queries to understand the main topic
  and identify related areas. Only use search function.
- After the initial search exploration, summarize key concepts, definitions, and major themes.
- You MUST inspect the full transcript to be able to provide a better write up for the user.

Stage 2: Deep Investigation 
- Perform 5-6 refined queries focusing on depth.
- Inspect relevant documents for specific mechanisms, case studies, and technical details.
- Gather diverse viewpoints and data to strengthen depth and accuracy.

Rules:
1. Search queries:
   - Do not include years unless explicitly requested by the user.
   - Use timeless, concept-based queries (e.g., "AI investment trends" not "AI trends 2024").

2. The article must contain:
   - A clear, descriptive title.
   - An introduction with 2-3 paragraphs (each 4-6 sentences).
   - At least 10 sections, each focused on a distinct subtopic.
   - Each section must have at least 4 paragraphs, preferably 5-6.

3. Each paragraph must have at least one reference object containing:
   - video_id (YouTube video ID)
   - timestamp ("mm:ss" or "h:mm:ss")
   - quote (a short excerpt from that video segment)

4. Evidence quality:
   - All claims must be traceable to real YouTube sources.
   - References must correspond to valid video_id and timestamp pairs.
   - Do not fabricate data or sources.

5. Tone and style:
   - Write in a professional, neutral, analytical tone.
   - Emphasize explanation, synthesis, and comparison.

6. Output format: Markdown
""".strip()



def create_agent() -> Agent:
    es_client = Elasticsearch("http://localhost:9200")
    index_name = "podcasts"

    search_tools = SearchTools(
        es_client=es_client,
        index_name=index_name
    )

    summarization_agent = create_summarization_agent()

    summarization_tools = SummarizationTools(
        search_tools=search_tools,
        summarization_agent=summarization_agent
    )

    agent = Agent(
        name='research_agent',
        instructions=research_instructions,
        model='openai:gpt-4o-mini',
        tools=[search_tools.search_videos, summarization_tools.summarize]
    )

    class AppRunContext(TemporalRunContext):
        @classmethod
        def serialize_run_context(cls, ctx: RunContext) -> dict:
            return {
                'messages': ctx.messages,
                'retries': {}, # Placeholder for retries
            }

        @classmethod
        def deserialize_run_context(cls, serialized: dict, deps: Any) -> 'AppRunContext':
            serialized.pop('deps', None) # remove deps if present to avoid multiple values error

            if 'messages' in serialized:
                serialized_messages = TypeAdapter(list[ModelMessage]).validate_python(serialized['messages'])
                serialized['messages'] = serialized_messages
            
            return cls(**serialized, deps=deps)

    return TemporalAgent(agent, run_context_type=AppRunContext)



temporal_agent = create_agent()

@workflow.defn
class ResearchWorkflow(PydanticAIWorkflow):  

    @workflow.run
    async def run(self, prompt: str) -> str:
        result = await temporal_agent.run(prompt)  
        return result.output



async def run():
    client = await Client.connect(  
        'localhost:7233',  
        plugins=[PydanticAIPlugin()],  
    )

    prompt = "how do I get started with machine learning?"
    
    activities = temporal_agent.temporal_activities

    async with Worker(  
        client,
        task_queue='research',
        workflows=[ResearchWorkflow],
        activities=activities,
    ):
        output = await client.execute_workflow(  
            ResearchWorkflow.run,
            args=(prompt, ),
            id=f'research-{uuid.uuid4()}',
            task_queue='research',
        )

    print("FINAL OUTPUT:")
    print(output)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
