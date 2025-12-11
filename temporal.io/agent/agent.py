#!/usr/bin/env python
# coding: utf-8

# In[1]:


from elasticsearch import Elasticsearch


# In[2]:


es = Elasticsearch("http://localhost:9200")


# In[20]:


def search_videos(query: str, size: int = 5) -> list[dict]:
    """
    Search for videos whose titles or subtitles match a given query.

    This function queries a video index and returns the most relevant matches,
    giving higher importance to title matches. It also provides highlighted
    text snippets that show where the query matched within each result.

    Args:
        query (str): The text to search for in video titles and subtitles.
        size (int, optional): Maximum number of results to return. Defaults to 5.

    Returns:
        list[dict]: A list of highlighted match information for each video,
        including the video ID and highlighted snippets from the title and/or subtitles.
    """
    body = {
        "size": size,
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title^3", "subtitles"],
                "type": "best_fields",
                "analyzer": "english_with_stop_and_stem"
            }
        },
        "highlight": {
            "pre_tags": ["*"],      # highlight start
            "post_tags": ["*"],     # highlight end
            "fields": {
                "title": {
                    "fragment_size": 150,
                    "number_of_fragments": 1
                },
                "subtitles": {
                    "fragment_size": 150,
                    "number_of_fragments": 1
                }
            }
        }
    }

    response = es.search(index="podcasts", body=body)

    hits = response.body['hits']['hits']

    results = []

    for hit in hits:
        highlight = hit['highlight']
        highlight['video_id'] = hit['_id']
        results.append(highlight)

    return results


def get_subtitles_by_id(video_id: str) -> dict:
    """
    Retrieve the stored subtitle data for a specific video.

    Args:
        video_id (str): The unique identifier of the video.

    Returns:
        dict: The video's subtitle metadata and transcript content.
    """
    result = es.get(index="podcasts", id='1aMuynlLM3o')
    return result['_source']


# In[21]:


search_videos('how do I get rich with AI?')


# In[ ]:





# In[22]:


from pydantic_ai import Agent


# In[28]:


from pydantic_ai.messages import FunctionToolCallEvent

class NamedCallback:
    """Stream handler that prints the tool calls triggered by an agent."""

    def __init__(self, agent: Agent):
        self.agent_name = agent.name

    async def _print_function_calls(self, ctx, event) -> None:
        # Detect nested streams
        if hasattr(event, "__aiter__"):
            async for sub_event in event:  # type: ignore[attr-defined]
                await self._print_function_calls(ctx, sub_event)
            return

        if isinstance(event, FunctionToolCallEvent):
            tool_name = event.part.tool_name
            args = event.part.args
            print(f"TOOL CALL ({self.agent_name}): {tool_name}({args})")

    async def __call__(self, ctx, event) -> None:
        await self._print_function_calls(ctx, event)


# In[ ]:


research_instructions = """
You're a helpful researcher agent
""".strip()

research_agent = Agent(
    name='research_agent',
    instructions=research_instructions,
    model='openai:gpt-4o-mini',
    tools=[search_videos, get_subtitles_by_id]
)

research_agent_callback = NamedCallback(research_agent)

result = await research_agent.run(
    user_prompt='how do I get rich with AI?',
    event_stream_handler=research_agent_callback
)


# In[35]:


print(result.output)


# In[42]:


messages = result.new_messages()

for m in messages:
    for p in m.parts:
        kind = p.part_kind
        if kind == 'user-prompt':
            print('USER:', p.content)
            print()
        if kind == 'text':
            print('ASSISTANT:', p.content)
            print()
        if kind == 'tool-call':
            print('TOOL CALL:', p.tool_name, p.args)


# No tool calls

# In[47]:


research_instructions = """
You're a researcher and your task is to use the available tools to conduct a research on the topic 
that the user provided.

cite the sources
""".strip()


# In[ ]:


research_agent = Agent(
    name='research_agent',
    instructions=research_instructions,
    model='openai:gpt-4o-mini',
    tools=[search_videos, get_subtitles_by_id]
)

research_agent_callback = NamedCallback(research_agent)

result = await research_agent.run(
    user_prompt='how do I get rich with AI?',
    event_stream_handler=research_agent_callback
)


# In[51]:


print(result.output)


# In[83]:


messages = result.new_messages()

for m in messages:
    for p in m.parts:
        kind = p.part_kind
        if kind == 'user-prompt':
            print('USER:', p.content)
            print()
        if kind == 'text':
            print('ASSISTANT:', p.content)
            print()
        if kind == 'tool-call':
            print('TOOL CALL:', p.tool_name, p.args)


# In[90]:


research_instructions = """
You are an autonomous research agent. Your goal is to perform deep, multi-stage research on the
given topic using the available search function. You must iteratively refine your understanding
of the topic and its subtopics through structured exploration.

Research process:

stage 1: initial exploration  
- Using your own knowledge of the topic, perform 3-5 broad search queries to understand the main topic
  in results and identify related areas. Only use search function, don't use anything else.
- After the initial search exploration is done, summarize key concepts, definitions, and major themes.  

stage 2: deep investigation 
- Perform 5–6 refined queries focusing on depth before doing any analysis.  
- Ispect relevant documents. Check specific mechanisms, case studies, technical details, or research gaps.  
- Gather diverse viewpoints and data to strengthen depth and accuracy.  

Rules:

1. Search queries:
   - Do not include years (e.g., “2023,” “2024”) unless explicitly part of the user’s request.
   - Always use timeless, general, or concept-based queries (e.g., “AI investment trends”
     instead of “AI investment trends 2023”).
   - Prefer queries that help build depth, context, and connections across subtopics.

2. The article must contain:
   - A clear, descriptive title.
   - An introduction with 2–3 paragraphs (each 4–6 sentences).
   - At least 10 sections, ideally 10–12, each focused on a distinct subtopic.
   - Each section must have at least 4 paragraphs, preferably 5–6.
   - Each paragraph must contain 4–6 sentences of original synthesis.

3. Each paragraph must have at least one reference object containing:
   - video_id (YouTube video ID)
   - timestamp ("mm:ss" or "h:mm:ss")
   - quote (a short excerpt or paraphrase from that video segment)
   - Do not embed citations inline in the text.

4. The conclusion must have 2–3 paragraphs summarizing the key findings and implications.

5. Structure and coherence:
   - Each section must have a unique title describing its focus.
   - Paragraphs within a section must explore different but related ideas.
   - The narrative should flow logically across sections.

6. Evidence quality:
   - All claims must be traceable to real YouTube sources.
   - References must correspond to valid video_id and timestamp pairs.
   - Quotes should reflect the video’s spoken content accurately.
   - Do not fabricate data or sources.

7. Depth and length requirements:
   - If the output has fewer than 10 sections or any section has fewer than 4 paragraphs, it is invalid.
   - If any paragraph has no references, it is invalid.
   - The report should read like an in-depth, long-form synthesis, not a short article.

8. Tone and style:
   - Write in a professional, neutral, analytical tone.
   - Emphasize explanation, synthesis, and comparison.
   - Avoid repetition and filler text.

9. Output format:
   - Markdown format
   - Populate all required fields: stages, article, sections, paragraphs, references.

10. Self-check before completion:
   - Confirm you have 10–12 sections.
   - Confirm each section has 4–6 paragraphs.
   - Confirm each paragraph has 4–6 sentences.
   - Confirm each paragraph has at least one valid reference object.
   - Confirm introduction and conclusion both contain 2–3 paragraphs.

Only output once all checks are satisfied.


Final deliverable:

The article must be long, detailed, and divided into multiple sections and paragraphs — not short summaries.

""".strip()


# Get this:
# 
# ```
# raise ModelHTTPError(status_code=status_code, model_name=self.model_name, body=e.body) from e
# pydantic_ai.exceptions.ModelHTTPError: status_code: 400, model_name: gpt-4o-mini, body: {'message': "This model's maximum context length is 128000 tokens. However, your messages resulted in 165609 tokens (165383 in the messages, 226 in the functions). Please reduce the length of the messages or functions.", 'type': 'invalid_request_error', 'param': 'messages', 'code': 'context_length_exceeded'}
# ```
# 
# Let's summarize our subtitles

# In[72]:


sumarization_instructions = """
Your task is to summarize the provided youtube transcript for a specific topic

select the parts of the transcripts that are relevant for the topic and search qieries

Format: 

paragraph with discussion (timestamp)
""".strip()


# In[73]:


sumarization_agent = Agent(
    name='summarization',
    instructions=sumarization_instructions,
    model='openai:gpt-4o-mini'
)


# In[74]:


user_query = 'how do I get rich with AI?'
search_queries = [
    "investment opportunities in AI",
    "starting AI-focused businesses",
    "AI applications in wealth generation",
    "AI for entrepreneurship",
    "AI impact on job sectors"
]

subtitles = get_subtitles_by_id('1aMuynlLM3o')['subtitles']

prompt = f"""
user query:

{user_query}

search engine queries: 

{'\n'.join(search_queries)}

subtitles:

{subtitles}
""".strip()


# In[75]:


print(prompt[:500])


# In[76]:


summary_result = await sumarization_agent.run(prompt)


# In[77]:


print(summary_result.output)


# In[86]:


from pydantic_ai import RunContext
import textwrap
import json

async def summarize(ctx: RunContext, video_id: str) -> str:
    """
    Generate a summary for a video based on the conversation history, search queries,
    and the video's subtitles.

    This function inspects prior model interaction parts to extract:
      - what the user has asked,
      - what search queries were triggered during the conversation.

    It then retrieves the subtitles of the referenced video and constructs a
    consolidated prompt containing all of this context. That prompt is sent to
    a summarization agent, and the agent's summary is returned.

    Args:
        video_id (str): The identifier of the video to summarize.

    Returns:
        str: A generated summary reflecting user intent, search behavior, and the
        video's subtitle content.
    """
    user_queries = []
    search_queries = []

    for p in m.parts:
        kind = p.part_kind
        if kind == 'user-prompt':
            user_queries.append(p.content)
        if kind == 'tool-call':
            if p.tool_name == 'search_videos':
                args = json.loads(p.args)
                query = args['query']
                search_queries.append(query)

    subtitles = get_subtitles_by_id('1aMuynlLM3o')['subtitles']

    prompt = textwrap.dedent(f"""
        user query:

        {'\n'.join(user_queries)}

        search engine queries: 

        {'\n'.join(search_queries)}

        subtitles:

        {subtitles}
    """).strip()

    summary_result = await sumarization_agent.run(prompt) 
    return summary_result.output


# In[91]:


research_agent = Agent(
    name='research_agent',
    instructions=research_instructions,
    model='openai:gpt-4o-mini',
    tools=[search_videos, summarize]
)


# In[ ]:


research_agent_callback = NamedCallback(research_agent)

result = await research_agent.run(
    user_prompt='how do I get rich with AI?',
    event_stream_handler=research_agent_callback
)


# In[ ]:


print(result.output)


# In[ ]:




