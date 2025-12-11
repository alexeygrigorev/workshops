"""Research workflow using Temporal and Pydantic AI."""

from temporalio import workflow
from temporalio.exceptions import ApplicationError
from datetime import timedelta
from typing import List

from pydantic_ai import Agent, RunContext
from pydantic_ai.durable_exec.temporal import TemporalAgent
from activities import search_videos_activity, get_subtitles_activity
import textwrap
import json


# Agent for summarizing video content
summarization_instructions = """
Your task is to summarize the provided YouTube transcript for a specific topic.

Select the parts of the transcripts that are relevant for the topic and search queries.

Format: 
paragraph with discussion (timestamp)
""".strip()

summarization_agent = Agent(
    name='summarization',
    instructions=summarization_instructions,
    model='openai:gpt-4o-mini'
)

# Agent for deep research
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
- Inspect relevant documents. Check specific mechanisms, case studies, technical details, or research gaps.  
- Gather diverse viewpoints and data to strengthen depth and accuracy.  

Rules:

1. Search queries:
   - Do not include years (e.g., "2023," "2024") unless explicitly part of the user's request.
   - Always use timeless, general, or concept-based queries (e.g., "AI investment trends"
     instead of "AI investment trends 2023").
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
   - Quotes should reflect the video's spoken content accurately.
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


@workflow.defn
class ResearchWorkflow:
    """
    Deep research workflow that orchestrates multi-stage research using AI agents.
    
    This workflow:
    1. Uses a research agent with video search capabilities
    2. Performs initial exploration (3-5 broad queries)
    3. Conducts deep investigation (5-6 refined queries)
    4. Summarizes video content to avoid context length issues
    5. Generates a comprehensive research report
    """
    
    def __init__(self):
        self.search_queries_log: List[str] = []
        self.videos_analyzed: List[str] = []
        
    @workflow.run
    async def run(self, query: str) -> str:
        """
        Execute the deep research workflow.
        
        Args:
            query: The research question/topic to investigate
            
        Returns:
            A formatted research report in markdown
        """
        workflow.logger.info(f"Starting research workflow for query: {query}")
        
        # Wrap summarization agent for Temporal execution (define early for use in closure)
        temporal_summarization_agent = TemporalAgent(summarization_agent)
        
        # Define the summarization tool that the research agent will use
        async def summarize_video(ctx: RunContext, video_id: str) -> str:
            """
            Generate a summary for a video based on the conversation history,
            search queries, and the video's subtitles.
            """
            # Extract user queries and search queries from message history
            user_queries = []
            search_queries = []
            
            # Get messages from the agent's context
            messages = ctx.messages
            for m in messages:
                for p in m.parts:
                    kind = p.part_kind
                    if kind == 'user-prompt':
                        user_queries.append(p.content)
                    if kind == 'tool-call':
                        if p.tool_name == 'search_videos':
                            args = json.loads(p.args)
                            search_query = args['query']
                            search_queries.append(search_query)
            
            # Get subtitles via Temporal activity
            subtitles_data = await workflow.execute_activity(
                get_subtitles_activity,
                video_id,
                start_to_close_timeout=timedelta(seconds=30),
            )
            
            subtitles = subtitles_data.get('subtitles', '')
            
            # Create summarization prompt
            prompt = textwrap.dedent(f"""
                user query:
                
                {chr(10).join(user_queries)}
                
                search engine queries: 
                
                {chr(10).join(search_queries)}
                
                subtitles:
                
                {subtitles}
            """).strip()
            
            # Use the summarization agent (this will be wrapped by TemporalAgent)
            summary_result = await temporal_summarization_agent.run(prompt)
            return summary_result.output
        
        # Define the search tool that the research agent will use
        async def search_videos(ctx: RunContext, query: str, size: int = 5) -> list[dict]:
            """
            Search for videos via Temporal activity.
            """
            # Track the query
            self.search_queries_log.append(query)
            
            # Execute search via Temporal activity
            results = await workflow.execute_activity(
                search_videos_activity,
                args=[query, size],
                start_to_close_timeout=timedelta(seconds=30),
            )
            
            # Convert SearchResult objects to dicts for the agent
            results_dict = []
            for r in results:
                self.videos_analyzed.append(r.video_id)
                result_dict = {
                    'video_id': r.video_id,
                }
                if r.title_highlight:
                    result_dict['title'] = r.title_highlight
                if r.subtitles_highlight:
                    result_dict['subtitles'] = r.subtitles_highlight
                results_dict.append(result_dict)
            
            return results_dict
        
        # Create the research agent with tools
        research_agent = Agent(
            name='research_agent',
            instructions=research_instructions,
            model='openai:gpt-4o-mini',
            tools=[search_videos, summarize_video]
        )
        
        # Wrap agent for Temporal execution
        temporal_research_agent = TemporalAgent(research_agent)
        
        # Execute the research
        workflow.logger.info("Running research agent...")
        try:
            result = await temporal_research_agent.run(
                user_prompt=query,
            )
            
            report = result.output
            
            # Format the final output with metadata
            formatted_report = f"""
# Deep Research Report

**Research Query:** {query}

**Total Searches Conducted:** {len(self.search_queries_log)}
**Unique Videos Analyzed:** {len(set(self.videos_analyzed))}

---

{report}

---

## Research Metadata

**Search Queries Executed:**
{chr(10).join([f"- {q}" for q in self.search_queries_log])}

**Videos Referenced:**
{chr(10).join([f"- {v}" for v in set(self.videos_analyzed)])}
"""
            
            workflow.logger.info("Research workflow completed successfully")
            return formatted_report
            
        except Exception as e:
            workflow.logger.error(f"Research workflow failed: {e}")
            raise ApplicationError(
                f"Research workflow failed: {str(e)}",
                "RESEARCH_FAILED",
                non_retryable=True,
            )
