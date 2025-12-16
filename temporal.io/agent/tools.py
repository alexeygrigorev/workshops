import json
import textwrap

from pydantic_ai import Agent, RunContext
from elasticsearch import Elasticsearch


class SearchTools:

    def __init__(self, es_client: Elasticsearch, index_name: str):
        self.es_client = es_client
        self.index_name = index_name

    def search_videos(self, query: str, size: int = 5) -> list[dict]:
        """
        Search for videos whose titles or subtitles match a given query.

        Returns highlighted match information including video IDs and snippets.

        Args:
            query (str): The search query string to match against video titles and subtitles. Must be a non-empty string.
            size (int, optional): Maximum number of results to return. Must be a positive integer. Defaults to 5.
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
                "pre_tags": ["*"],
                "post_tags": ["*"],
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

        response = self.es_client.search(index=self.index_name, body=body)
        hits = response.body['hits']['hits']

        results = []
        for hit in hits:
            highlight = hit['highlight']
            highlight['video_id'] = hit['_id']
            results.append(highlight)

        return results

    def get_subtitles_by_id(self, video_id: str) -> dict:
        """
        Retrieve the full subtitle content for a specific video.

        Args:
            video_id (str): the YouTube video id for which we want to get the subtitles
        """
        result = self.es_client.get(index=self.index_name, id=video_id)
        return result['_source']


class SummarizationTools:

    def __init__(self,
        search_tools: SearchTools,
        summarization_agent: Agent
    ):
        self.search_tools = search_tools
        self.summarization_agent = summarization_agent

    async def summarize(self, ctx: RunContext, video_id: str) -> str:
        """
        Generate a summary for a video based on the conversation history,
        search queries, and the video's subtitles.
        """
        user_queries = []
        search_queries = []

        for m in ctx.messages:
            for p in m.parts:
                kind = p.part_kind
                if kind == 'user-prompt':
                    user_queries.append(p.content)
                if kind == 'tool-call':
                    if p.tool_name == 'search_videos':
                        args = json.loads(p.args)
                        query = args['query']
                        search_queries.append(query)

        subtitles = self.search_tools.get_subtitles_by_id(video_id)['subtitles']

        prompt = textwrap.dedent(f"""
            user query:
            {'\n'.join(user_queries)}

            search engine queries: 
            {'\n'.join(search_queries)}

            subtitles:
            {subtitles}
        """).strip()

        summary_result = await self.summarization_agent.run(prompt) 
        return summary_result.output

