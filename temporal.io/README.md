# End-To-End Deep Research Agent

* Video: TBA

In this workshop, we will create a deep research agent based on the DataTalks.Club podcast data.

To do it, we will need:

- Download the transcript data from YouTube
- Ingest it into Elasticsearch
- Create an agent that can perform research on top of Elasticsearch


## Prerequisites

- Python 3.13
- Docker (for running Elasticsearch)
- Basic understanding of Python and APIs

## Environment Setup

For this workshop, you can use:
* GitHub Codespaces (recommended)
* Local Python environment
* Any Jupyter-compatible environment

We'll use `uv` for fast Python package management:

```bash
pip install uv
```

Create a folder "flow" and initialize an empty project there:

```bash
mkdir flow
cd flow

uv init --python=3.13
```

## Fetching YouTube Transcripts

Install the YouTube Transcript API library and Jupyter notebook:

```bash
uv add youtube-transcript-api
uv add --dev jupyter
```

Now let's start Jupyter, and create a notebook there. We can call it "notebook.ipynb".

```bash
uv run jupyter notebook
```

Inside, we'll start by fetching a transcript for a single video:

```python
from youtube_transcript_api import YouTubeTranscriptApi

def fetch_transcript(video_id):
    ytt_api = YouTubeTranscriptApi()
    transcript = ytt_api.fetch(video_id)
    return transcript

video_id = 'D2rw52SOFfM'
transcript = fetch_transcript(video_id)
```

The transcript is a list of entries, each containing:

- `start`: timestamp in seconds
- `duration`: duration of the segment
- `text`: the actual transcript text

Now let's turn this into this format:

```
0:00 Hi everyone, welcome to our event. This
0:03 event is brought to you by Data Dogs
0:04 Club which is a community of people who
0:06 love data. We have weekly events. Today
0:09 is one of such events. If you want to
0:11 found find out more about the events we
0:13 have, there's a link in the description.
0:14 Click on this link, you see all the
0:17 events we have in our pipeline. Do not
0:19 forget to subscribe to our YouTube
0:21 channel. This way you'll get notified
0:22 about all future events like the one we
0:24 have today.
```

For that, we'll need to iterate over all chunks of the transcript, and 
turn time in seconds into "mm:ss" format:


```python
def format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours == 0:
        return f"{minutes}:{secs:02}"
    return f"{hours}:{minutes:02}:{secs:02}"

def make_subtitles(transcript) -> str:
    lines = []

    for entry in transcript:
        ts = format_timestamp(entry.start)
        text = entry.text.replace('\n', ' ')
        lines.append(ts + ' ' + text)

    return '\n'.join(lines)
```

Use it:

```python
subtitles = make_subtitles(transcript)
print(subtitles[:500])
```

<details>
<summary><b>Alternative: Fetching pre-processed transcripts from GitHub</b></summary>
<br/>
If you don't want to deal with YouTube API rate limits and proxies, we've pre-processed all the transcripts and made them available on GitHub.

Install requests library:

```bash
uv add requests
```

Fetch a transcript:

```python
import requests

def fetch_transcript_cached(video_id):
    url_prefix = 'https://raw.githubusercontent.com/alexeygrigorev/workshops/refs/heads/main/temporal.io/data'
    url = f'{url_prefix}/{video_id}.txt'
    
    raw_text = requests.get(url).content.decode('utf8')
    
    lines = raw_text.split('\n')
    
    video_title = lines[0]
    subtitles = '\n'.join(lines[2:]).strip()
    
    return {
        "video_id": video_id,
        "title": video_title,
        "subtitles": subtitles
    }
```

**Note**: If you use this approach, adjust the workflow functions below to fetch from GitHub instead of YouTube API.

</details>
<br>

## Setting Up Elasticsearch

Now let's store the transcripts in Elasticsearch.

Run Elasticsearch in Docker:

```bash
docker run -it \
  --rm \
  --name elasticsearch \
  -m 4GB \
  -p 9200:9200 \
  -p 9300:9300 \
  -v elasticsearch-data:/usr/share/elasticsearch/data \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:9.2.0
```

Verify it's running:

```bash
curl http://localhost:9200
```

Install the Elasticsearch Python client:

```bash
uv add elasticsearch
```

### Creating the Index

Connect to Elasticsearch and create an index with custom analyzers for better search:

```python
from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")

stopwords = [
    "a","about","above","after","again","against","all","am","an","and","any",
    "are","aren","aren't","as","at","be","because","been","before","being",
    "below","between","both","but","by","can","can","can't","cannot","could",
    "couldn't","did","didn't","do","does","doesn't","doing","don't","down",
    "during","each","few","for","from","further","had","hadn't","has","hasn't",
    "have","haven't","having","he","he'd","he'll","he's","her","here","here's",
    "hers","herself","him","himself","his","how","how's","i","i'd","i'll",
    "i'm","i've","if","in","into","is","isn't","it","it's","its","itself",
    "let's","me","more","most","mustn't","my","myself","no","nor","not","of",
    "off","on","once","only","or","other","ought","our","ours","ourselves",
    "out","over","own","same","shan't","she","she'd","she'll","she's","should",
    "shouldn't","so","some","such","than","that","that's","the","their",
    "theirs","them","themselves","then","there","there's","these","they",
    "they'd","they'll","they're","they've","this","those","through","to",
    "too","under","until","up","very","was","wasn't","we","we'd","we'll",
    "we're","we've","were","weren't","what","what's","when","when's","where",
    "where's","which","while","who","who's","whom","why","why's","with",
    "won't","would","wouldn't","you","you'd","you'll","you're","you've",
    "your","yours","yourself","yourselves",
    "get"
]

index_settings = {
    "settings": {
        "analysis": {
            "filter": {
                "english_stop": {
                    "type": "stop",
                    "stopwords": stopwords
                },
                "english_stemmer": {
                    "type": "stemmer",
                    "language": "english"
                },
                "english_possessive_stemmer": {
                    "type": "stemmer",
                    "language": "possessive_english"
                }
            },
            "analyzer": {
                "english_with_stop_and_stem": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "english_possessive_stemmer",
                        "english_stop",
                        "english_stemmer"
                    ]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "title": {
                "type": "text",
                "analyzer": "english_with_stop_and_stem",
                "search_analyzer": "english_with_stop_and_stem"
            },
            "subtitles": {
                "type": "text",
                "analyzer": "english_with_stop_and_stem",
                "search_analyzer": "english_with_stop_and_stem"
            }
        }
    }
}

index_name = "podcasts"

if es.indices.exists(index=index_name):
    es.indices.delete(index=index_name)
    
es.indices.create(index=index_name, body=index_settings)
print(f"Index '{index_name}' created successfully")
```

## Indexing Our First Document

Now let's index the transcript we downloaded:

```python
doc = {
    "video_id": video_id,
    "title": "Reinventing a Career in Tech",
    "subtitles": subtitles
}

es.index(index="podcasts", id=video_id, document=doc)
print(f"Indexed video: {video_id}")
```


## Testing Search

Let's verify our document is searchable:

```python
def search_videos(query: str, size: int = 5):
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
    
    response = es.search(index="podcasts", body=body)
    hits = response.body['hits']['hits']
    
    results = []
    for hit in hits:
        highlight = hit['highlight']
        highlight['video_id'] = hit['_id']
        results.append(highlight)

    return results

results = search_videos("machine learning")
```

## Processing Multiple Videos

Now let's scale up to process all podcast videos from DataTalks.Club.

Install the required libraries for fetching video metadata:

```bash
uv add requests pyyaml
```

Get the list of podcast videos from DataTalks.Club:

```python
import requests
import yaml

events_url = 'https://raw.githubusercontent.com/DataTalksClub/datatalksclub.github.io/187b7d056a36d5af6ac33e4c8096c52d13a078a7/_data/events.yaml'

raw_yaml = requests.get(events_url).content
events_data = yaml.load(raw_yaml, yaml.CSafeLoader)

podcasts = [d for d in events_data if (d.get('type') == 'podcast') and (d.get('youtube'))]

print(f"Found {len(podcasts)} podcasts")
```

Extract video IDs from the podcast data:

```python
videos = []

for podcast in podcasts:
    _, video_id = podcast['youtube'].split('watch?v=')

    # Skip problematic videos
    if video_id == 'FRi0SUtxdMw':
        continue

    videos.append({
        'title': podcast['title'],
        'video_id': video_id
    })

print(f"Will process {len(videos)} videos")
```

Install tqdm for progress tracking:

```bash
uv add tqdm
```

Now we can download and index all the videos:

```bash
from tqdm.auto import tqdm

for video in tqdm(videos):
    video_id = video['video_id']
    video_title = video['title']

    if es.exists(index='podcasts', id=video_id):
        print(f'already processed {video_id}')
        continue

    transcript = fetch_transcript(video_id)
    subtitles = make_subtitles(transcript)

    doc = {
        "video_id": video_id,
        "title": video_title,
        "subtitles": subtitles
    }
    
    es.index(index="podcasts", id=video_id, document=doc)
```


## Using Proxies

At some point we will encounter rate limiting from YouTube.

We fix this by using a proxy.

Create a `.env` file with your proxy credentials:

```bash
PROXY_BASE_URL=...
PROXY_USER=...
PROXY_PASSWORD=...
```

Create `.gitignore` to exclude `.env`:

```bash
echo '.env' >> .gitignore
```

Stop Jupyter.

To load these variables, we'll use `dirdotenv` to load the variables from the `.env` file:

```bash
echo 'alias dirdotenv="uvx dirdotenv"' >> ~/.bashrc
echo 'eval "$(dirdotenv hook bash)"' >> ~/.bashrc
source ~/.bashrc
```

Update your fetch function to use proxy:

```python
import os
from youtube_transcript_api.proxies import GenericProxyConfig

proxy_user = os.environ['PROXY_USER']
proxy_password = os.environ['PROXY_PASSWORD']
proxy_base_url = os.environ['PROXY_BASE_URL']

proxy_url = f'http://{proxy_user}:{proxy_password}@{proxy_base_url}'

proxy = GenericProxyConfig(
    http_url=proxy_url,
    https_url=proxy_url,
)

def fetch_transcript(video_id):
    ytt_api = YouTubeTranscriptApi(proxy_config=proxy)
    transcript = ytt_api.fetch(video_id)
    return transcript
```

Now continue processing.


## Temporal.io

But even with proxies, we can still face challenges:

- Requests can be blocked by IP
- SSL errors (`SSLError: [SSL: WRONG_VERSION_NUMBER] wrong version number`)
- Network timeouts
- Rate limiting

So we need a reliable way of making retrials. We can implement it ourselves, but
it will be a lot of code that we will need to maintain. 

Let's use a special tool for that: Temporal.io. It provides a reliable way to orchestrate workflows with retry logic and durable execution.

Temporal.io solves these problems by providing:

- Durable execution: Workflows survive crashes and restarts
- Built-in retries: Automatic retry policies with backoff
- State management: No need to manually track progress
- Visibility: Web UI to monitor workflow execution
- Concurrency control: Easy to manage parallel execution

Let's install it. For Linux: 

```bash
# Create a dir for executables
mkdir ~/bin
echo 'PATH="${PATH}:~/bin"' >> ~/.bashrc
source ~/.bashrc

# Download the Temporal CLI
wget 'https://temporal.download/cli/archive/latest?platform=linux&arch=amd64' -O temporal.tar.gz

# Extract
tar -xzf temporal.tar.gz

# Move to ~/bin
mv temporal ~/bin/
rm temporal.tar.gz LICENSE
```

Verify that it works:

```bash
temporal -v
```

You should see output like:

```
temporal version 1.5.1 (Server 1.29.1, UI 2.42.1)
```

You can see how to install it for other platforms [here](temporal-install.md).

Start the server: 

```bash
temporal server start-dev
```


Add temporal to our project with uv:

```bash
uv add temporalio
```


## Creating a Workflow

Before we create a Temporal workflow, let's first organize everything in a proper Python project, not a Jupyter notebook.

Let's start with converting our notebook into a Python script:


```bash
uv run jupyter nbconvert --to=script notebook.ipynb
```

Next, move index creation logic to `create_index.py`.

For the rest of the logic, let's create a file `workflow.py` (see [workflow.py](workflow.py)).

Let's take a look at the main flow and identify places where the code can break:


```python
def workflow():
    commit_id = '187b7d056a36d5af6ac33e4c8096c52d13a078a7'
    # here: network
    videos = find_podcast_videos(commit_id)

    for video in videos:
        video_id = video['video_id']
        video_title = video['title']

        # here: network
        if es.exists(index='podcasts', id=video_id):
            print(f'already processed {video_id}')
            continue

        # here: many reasons
        subtitles = fetch_subtitles(video_id)

        doc = {
            "video_id": video_id,
            "title": video_title,
            "subtitles": subtitles
        }

        # here: network
        es.index(index="podcasts", id=video_id, document=doc)
```

## Temporal Activities

These pieces of code become our **activities** -  individual units of work that a Temporal Workflow performs. Usually they are tasks that we need to do: 

- interacting with external systems (e.g., making API calls)
- writing data to a database
- sending emails or notifications
- sprocessing files, images, or other business logic

We annotate them with `@activity.defn`. 

Let's move them to a separate file `activities.py` (see the result [here](flow/activities.py)).


## Temporal Workflow

These activities are executed in a **workflow**. 

This is the code we have so far: 

```python
from elasticsearch import Elasticsearch

def workflow():
    commit_id = '187b7d056a36d5af6ac33e4c8096c52d13a078a7'
    videos = find_podcast_videos(commit_id)

    es_address = "http://localhost:9200"

    for video in videos:
        video_id = video['video_id']

        if video_exists(es_address, video_id):
            print(f'already processed {video_id}')
            continue

        subtitles = fetch_subtitles(video_id)
        index_video(es_address, video, subtitles)
```

Let's turn it into a Temporal workflow. It's a class annotaged with `@workflow.defn` which must have an async method for running the workflow annotated with `@workflow.run`

```python
from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import (
        fetch_subtitles,
        find_podcast_videos,
        video_exists,
        index_video,
    )


@workflow.defn
class PodcastTranscriptWorkflow:

    @workflow.run
    async def run(self, commit_id: str, es_address: str) -> dict:
        workflow.logger.info(f"Finding podcast videos from commit {commit_id}...")
        
        videos = await workflow.execute_activity(
            activity=find_podcast_videos,
            args=(commit_id,),
            start_to_close_timeout=timedelta(minutes=1),
        )

        workflow.logger.info(f"Connecting to Elasticsearch at {es_address}...")

        for video in videos:
            video_id = video['video_id']

            if await workflow.execute_activity(
                activity=video_exists,
                args=(es_address, video_id),
                start_to_close_timeout=timedelta(seconds=10),
            ):
                workflow.logger.info(f'already processed {video_id}')
                continue

            subtitles = await workflow.execute_activity(
                activity=fetch_subtitles,
                args=(video_id,),
                start_to_close_timeout=timedelta(minutes=1),
            )

            await workflow.execute_activity(
                activity=index_video,
                args=(es_address, video, subtitles),
                start_to_close_timeout=timedelta(seconds=30),
            )
        
        return {
            "status": "completed",
            "processed_videos": len(videos),
        }
```

This is how we run it:

```python
import asyncio
from temporalio.client import Client


async def run_workflow():
    client = await Client.connect("localhost:7233")

    commit_id = '187b7d056a36d5af6ac33e4c8096c52d13a078a7'
    es_address = 'http://localhost:9200'

    result = await client.execute_workflow(
        PodcastTranscriptWorkflow.run,
        args=(commit_id, es_address),
        id="podcast_transcript_workflow",
        task_queue="podcast_transcript_task_queue",
    )

    print("Workflow completed! Result:", result)


if __name__ == "__main__":
    asyncio.run(run_workflow())
```

Let's run it:

```python
uv run python workflow.py
```

We can see this workflow in the UI, but nothing is happening. We need a **worker** - a process that actually executes the workflow and the activities.

Let's create `worker.py`:

```python
import asyncio

from temporalio.worker import Worker
from temporalio.client import Client

from workflow import PodcastTranscriptWorkflow
import activities


async def run_worker():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="podcast-transcript-task-queue",
        workflows=[PodcastTranscriptWorkflow],
        activities=[
            activities.fetch_subtitles,
            activities.find_podcast_videos,
            activities.video_exists,
            activities.index_video,
        ],
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
```

When I run it, I get an error:

Fix: add `ThreadPoolExecutor` for executing sync activities. 

```python
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=10)

worker = Worker(
    ...
    activity_executor=executor,
)
```

Run it:

```bash
uv run python worker.py
```

Now we can go to UI and see the flow being executed. It should take aroud 10 minutes to complete.


## Building an AI Research Agent

Now that we have transcripts indexed in Elasticsearch, we can build an AI agent that uses them to conduct research and answer questions.

### Setup

Create a new directory for the agent:

```bash
mkdir agent
cd agent
```

Initialize the project with required dependencies:

```bash
uv init
uv add pydantic-ai openai elasticsearch
uv add --dev jupyter
```

Create a `.env` file with your OpenAI API key:

```bash
OPENAI_API_KEY='your-key'
```

Start Jupyter to work interactively:

```bash
uv run jupyter notebook
```

Create a new notebook `agent.ipynb` to follow along.

### Creating Search Tools

First, connect to Elasticsearch and create search functions that will serve as tools for the agent:

```python
from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")

def search_videos(query: str, size: int = 5) -> list[dict]:
    """
    Search for videos whose titles or subtitles match a given query.
    
    Returns highlighted match information including video IDs and snippets.
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
    Retrieve the full subtitle content for a specific video.
    """
    result = es.get(index="podcasts", id=video_id)
    return result['_source']
```

Test the search function:

```python
search_videos('how do I get rich with AI?')
```

### Creating a Basic Research Agent

Create a simple agent with search capabilities using Pydantic AI:

```python
from pydantic_ai import Agent

research_instructions = """
You're a helpful researcher agent.
""".strip()

research_agent = Agent(
    name='research_agent',
    instructions=research_instructions,
    model='openai:gpt-4o-mini',
    tools=[search_videos, get_subtitles_by_id]
)

result = await research_agent.run(
    user_prompt='how do I get rich with AI?'
)

print(result.output)
```

**Tracking tool calls:**

To see which tools the agent is calling, create a callback handler:

```python
from pydantic_ai.messages import FunctionToolCallEvent

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

# Use the callback
research_agent_callback = NamedCallback(research_agent)

result = await research_agent.run(
    user_prompt='how do I get rich with AI?',
    event_stream_handler=research_agent_callback
)
```

You can also inspect the conversation messages:

```python
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
```

**Improving instructions for better tool usage:**

To get the agent to actually use the tools and conduct thorough research, provide detailed instructions:

```python
research_instructions = """
You're a researcher and your task is to use the available tools to conduct research on the topic 
that the user provided.

Cite the sources with video IDs and timestamps.
""".strip()

research_agent = Agent(
    name='research_agent',
    instructions=research_instructions,
    model='openai:gpt-4o-mini',
    tools=[search_videos, get_subtitles_by_id]
)

result = await research_agent.run(
    user_prompt='how do I get rich with AI?',
    event_stream_handler=research_agent_callback
)

print(result.output)
```

This still doens't create great results. let's use something more comprehensive 

For comprehensive research with structured exploration, use more detailed instructions:

```python
research_instructions = """
You are an autonomous research agent. Your goal is to perform deep, multi-stage research on the
given topic using the available search function.

Research process:

Stage 1: Initial Exploration  
- Using your own knowledge of the topic, perform 3-5 broad search queries to understand the main topic
  and identify related areas. Only use search function.
- After the initial search exploration, summarize key concepts, definitions, and major themes.

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
```

### Managing Context with Summarization

When dealing with long transcripts, we exceed context window. But we can summarize the transcripts. 

Let's create a summarizing agent:

```python
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
```

You can use it directly to test:

```python
user_query = 'how do I get rich with AI?'
search_queries = [
    "investment opportunities in AI",
    "starting AI-focused businesses",
    "AI applications in wealth generation"
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

summary_result = await summarization_agent.run(prompt)
print(summary_result.output)
```

### Making it a tool

To make summarization available as a tool for the research agent, create a dynamic function that uses conversation context:

```python
from pydantic_ai import RunContext
import textwrap
import json

async def summarize(ctx: RunContext, video_id: str) -> str:
    """
    Generate a summary for a video based on the conversation history,
    search queries, and the video's subtitles.
    """
    user_queries = []
    search_queries = []
    
    # Extract context from conversation history
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
    
    # Get full subtitles
    subtitles = get_subtitles_by_id(video_id)['subtitles']
    
    # Build contextual prompt
    prompt = textwrap.dedent(f"""
        user query:
        {'\n'.join(user_queries)}
        
        search engine queries: 
        {'\n'.join(search_queries)}
        
        subtitles:
        {subtitles}
    """).strip()
    
    summary_result = await summarization_agent.run(prompt) 
    return summary_result.output

# Update research agent with summarization tool
research_agent = Agent(
    name='research_agent',
    instructions=research_instructions,
    model='openai:gpt-4o-mini',
    tools=[search_videos, summarize]  # Replace get_subtitles_by_id with summarize
)

result = await research_agent.run(
    user_prompt='how do I get rich with AI?',
    event_stream_handler=research_agent_callback
)

print(result.output)
```

This approach allows the agent to:
1. Search for relevant videos
2. Summarize only the relevant parts of long transcripts
3. Stay within context limits while accessing detailed information
4. Conduct multi-stage research with proper citations

## Making the Agent Durable with Temporal

The agent we've built works well, but it has limitations in production:
- If the OpenAI API times out, we lose all progress
- System crashes mean starting over from scratch
- No automatic retry handling for failures
- State is not preserved across restarts

Temporal solves these problems with **durable execution**. The workflow looks like it's running continuously, but it can survive crashes, API failures, and even days-long pauses without losing state.

### Why Temporal for AI Agents?

Temporal's durable execution model is perfect for AI agents because:

1. **Automatic State Preservation**: Conversation history and search results are saved automatically
2. **Resilient to Failures**: API timeouts and crashes trigger automatic retries, not restarts
3. **Long-Running Workflows**: Can pause for hours/days (e.g., waiting for approval) without consuming resources
4. **Observable**: Full execution history in Temporal Web UI for debugging
5. **Scalable**: Workers can be distributed across multiple machines

### Installing Dependencies

Make sure you have Temporal support:

```bash
cd agent
uv add pydantic-ai[temporal] temporalio
```

### Creating the Workflow

Now we'll convert our research agent to use Temporal. The approach is similar to what we did before, but we wrap the agents and activities for durability.

Create `agent_workflow.py`:

```python
"""Research workflow using Temporal and Pydantic AI."""
from temporalio import workflow, activity
from temporalio.exceptions import ApplicationError
from datetime import timedelta
from typing import List
from elasticsearch import Elasticsearch
import os
import textwrap
import json

from pydantic_ai import Agent, RunContext
from pydantic_ai.durable_exec.temporal import TemporalAgent


# Elasticsearch activities
@activity.defn
async def search_videos_activity(query: str, size: int = 5) -> list[dict]:
    """Search for videos - runs as a Temporal activity."""
    es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    es = Elasticsearch(es_url)
    
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
                "title": {"fragment_size": 150, "number_of_fragments": 1},
                "subtitles": {"fragment_size": 150, "number_of_fragments": 1}
            }
        }
    }
    
    response = es.search(index="podcasts", body=body)
    hits = response.body['hits']['hits']
    
    results = []
    for hit in hits:
        highlight = hit.get('highlight', {})
        result = {'video_id': hit['_id']}
        if 'title' in highlight:
            result['title'] = highlight['title'][0]
        if 'subtitles' in highlight:
            result['subtitles'] = highlight['subtitles'][0]
        results.append(result)
    
    es.close()
    return results


@activity.defn
async def get_subtitles_activity(video_id: str) -> dict:
    """Retrieve subtitles for a video - runs as a Temporal activity."""
    es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    es = Elasticsearch(es_url)
    
    result = es.get(index="podcasts", id=video_id)
    source = result['_source']
    
    es.close()
    return source


# Agents
summarization_agent = Agent(
    name='summarization',
    instructions="""Your task is to summarize the provided YouTube transcript 
    for a specific topic. Select relevant parts and include timestamps.""",
    model='openai:gpt-4o-mini'
)

research_instructions = """
You are an autonomous research agent performing deep research.

Stage 1: Initial exploration (3-5 broad queries)
Stage 2: Deep investigation (5-6 refined queries)

Generate a comprehensive report with:
- Clear title and introduction
- 10-12 detailed sections
- Citations with video_id and timestamps
- Professional, analytical tone
"""


@workflow.defn
class ResearchWorkflow:
    """Durable research workflow orchestrating AI agents."""
    
    def __init__(self):
        self.search_queries_log: List[str] = []
        self.videos_analyzed: List[str] = []
        
    @workflow.run
    async def run(self, query: str) -> str:
        """Execute durable research workflow."""
        workflow.logger.info(f"Starting research for: {query}")
        
        # Wrap summarization agent for Temporal
        temporal_summarization_agent = TemporalAgent(summarization_agent)
        
        # Tool: Summarize video (uses activity + agent)
        async def summarize_video(ctx: RunContext, video_id: str) -> str:
            # Extract context from conversation
            user_queries = []
            search_queries = []
            
            for m in ctx.messages:
                for p in m.parts:
                    if p.part_kind == 'user-prompt':
                        user_queries.append(p.content)
                    if p.part_kind == 'tool-call' and p.tool_name == 'search_videos':
                        args = json.loads(p.args)
                        search_queries.append(args['query'])
            
            # Get subtitles via activity
            subtitles_data = await workflow.execute_activity(
                get_subtitles_activity,
                video_id,
                start_to_close_timeout=timedelta(seconds=30),
            )
            
            # Create contextual prompt
            prompt = textwrap.dedent(f"""
                user query: {chr(10).join(user_queries)}
                search queries: {chr(10).join(search_queries)}
                subtitles: {subtitles_data.get('subtitles', '')}
            """).strip()
            
            # Summarize with agent
            summary_result = await temporal_summarization_agent.run(prompt)
            return summary_result.output
        
        # Tool: Search videos (uses activity)
        async def search_videos(ctx: RunContext, query: str, size: int = 5) -> list[dict]:
            self.search_queries_log.append(query)
            
            results = await workflow.execute_activity(
                search_videos_activity,
                args=[query, size],
                start_to_close_timeout=timedelta(seconds=30),
            )
            
            for r in results:
                self.videos_analyzed.append(r['video_id'])
            
            return results
        
        # Create research agent with tools
        research_agent = Agent(
            name='research_agent',
            instructions=research_instructions,
            model='openai:gpt-4o-mini',
            tools=[search_videos, summarize_video]
        )
        
        # Wrap for Temporal execution
        temporal_research_agent = TemporalAgent(research_agent)
        
        # Execute research (durable!)
        try:
            result = await temporal_research_agent.run(user_prompt=query)
            
            # Format report with metadata
            formatted_report = f"""
# Deep Research Report

**Query:** {query}
**Searches:** {len(self.search_queries_log)}
**Videos:** {len(set(self.videos_analyzed))}

{result.output}

## Research Metadata
**Queries:** {', '.join(self.search_queries_log)}
**Videos:** {', '.join(set(self.videos_analyzed))}
"""
            workflow.logger.info("Research completed successfully")
            return formatted_report
            
        except Exception as e:
            workflow.logger.error(f"Research failed: {e}")
            raise ApplicationError(
                f"Research workflow failed: {str(e)}",
                "RESEARCH_FAILED",
                non_retryable=True,
            )
```

**Key Features:**
- Activities (`search_videos_activity`, `get_subtitles_activity`) wrap Elasticsearch operations
- `TemporalAgent` wraps Pydantic AI agents for durable execution
- Tools (search_videos, summarize_video) use activities internally
- Workflow state (`search_queries_log`, `videos_analyzed`) is preserved
- Full conversation history survives failures

### Creating the Worker

Create `agent_worker.py`:

```python
"""Temporal worker for research workflows."""
import asyncio
import os
from temporalio.client import Client
from temporalio.worker import Worker
from dotenv import load_dotenv

from agent_workflow import (
    ResearchWorkflow,
    search_videos_activity,
    get_subtitles_activity
)

async def main():
    load_dotenv()
    
    # Connect to Temporal
    client = await Client.connect(
        os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    )
    
    # Create worker
    worker = Worker(
        client,
        task_queue="research-task-queue",
        workflows=[ResearchWorkflow],
        activities=[search_videos_activity, get_subtitles_activity],
    )
    
    print("Worker started on task queue: research-task-queue")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Starting Workflows

Create `start_research.py`:

```python
"""Start a research workflow."""
import asyncio
import sys
import os
from temporalio.client import Client
from dotenv import load_dotenv
from agent_workflow import ResearchWorkflow

async def main():
    load_dotenv()
    
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "how do I get rich with AI?"
    
    client = await Client.connect(
        os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    )
    
    print(f"Starting research: {query}")
    
    handle = await client.start_workflow(
        ResearchWorkflow.run,
        query,
        id=f"research-{query[:30].replace(' ', '-')}",
        task_queue="research-task-queue",
    )
    
    print(f"Workflow ID: {handle.id}")
    print("Waiting for result...")
    
    result = await handle.result()
    
    print("\n" + "="*80)
    print("RESEARCH REPORT")
    print("="*80 + "\n")
    print(result)
    
    # Save to file
    output_file = f"research_report_{handle.id}.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"\nSaved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Running the System

Make sure Temporal server is running (see installation instructions in the Temporal.io section above).

**Terminal 1 - Temporal Server:**

```bash
temporal server start-dev
```

**Terminal 2 - Run the Worker:**

```bash
cd agent
uv run python agent_worker.py
```

**Terminal 3 - Start a Research Workflow:**

```bash
uv run python start_research.py "how do I get rich with AI?"
```

### What Happens Under the Hood

1. **Workflow Starts**: Research query sent to Temporal
2. **Agent Execution**: Research agent begins Stage 1 (exploration)
3. **Tool Calls**: 
   - Agent calls `search_videos` → Temporal activity executes
   - Results cached in workflow history
   - If OpenAI times out, only that agent call retries (searches not re-executed)
4. **Summarization**: 
   - Agent calls `summarize_video` → Activity gets subtitles
   - Summarization agent runs (also durable)
   - Results preserved even if it fails
5. **Stage 2**: Deep investigation continues from where Stage 1 left off
6. **Report Generated**: Final markdown report returned
7. **State Preserved**: Everything stored in Temporal's event history

### Monitoring and Debugging

**Temporal Web UI (http://localhost:8233):**
- View all running/completed workflows
- Inspect execution history (every activity, every decision)
- See retry attempts and failures
- Replay workflows for debugging

The key advantage: if anything fails (network, API timeout, crash), Temporal automatically retries from the last successful point without losing conversation history or re-executing completed searches.

## Additional Resources

- [Temporal Deep Research Documentation](https://docs.temporal.io/deep-research)
- [Pydantic AI + Temporal Integration](https://ai.pydantic.dev/durable-exec/temporal/)
- [Temporal Python SDK](https://docs.temporal.io/dev-guide/python)

- [YouTube Transcript API Documentation](https://github.com/jdepoix/youtube-transcript-api)
- [Elasticsearch Python Client](https://elasticsearch-py.readthedocs.io/)
- [DataTalks.Club Podcasts](https://datatalks.club/podcast.html)





