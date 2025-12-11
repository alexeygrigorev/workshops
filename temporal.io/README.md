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

Initialize the project:

```bash
uv init --python=3.13
```

## Fetching YouTube Transcripts

Install the YouTube Transcript API library:

```bash
uv add youtube-transcript-api
```

First, let's fetch a transcript for a single video:

```python
from youtube_transcript_api import YouTubeTranscriptApi

def fetch_transcript(video_id):
    ytt_api = YouTubeTranscriptApi()
    transcript = ytt_api.fetch(video_id)
    return transcript

# Example usage
video_id = 'D2rw52SOFfM'
transcript = fetch_transcript(video_id)
```

The transcript is a list of entries, each containing:
- `start`: timestamp in seconds
- `duration`: duration of the segment
- `text`: the actual transcript text

Create a function to format timestamps nicely:

```python
def format_timestamp(seconds: float) -> str:
    """Convert seconds to H:MM:SS if > 1 hour, else M:SS"""
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours == 0:
        return f"{minutes}:{secs:02}"
    return f"{hours}:{minutes:02}:{secs:02}"
```

Convert the transcript to a readable subtitle format:

```python
def make_subtitles(transcript) -> str:
    lines = []

    for entry in transcript:
        ts = format_timestamp(entry.start)
        text = entry.text.replace('\n', ' ')
        lines.append(ts + ' ' + text)

    return '\n'.join(lines)
```

## Storing Transcripts

Create a structured way to handle subtitles:

```python
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Subtitles:
    video_id: str
    video_title: str
    subtitles: str

    def write_file(self, subtitles_file: Path):    
        with subtitles_file.open('wt', encoding='utf-8') as f_out:
            f_out.write(self.video_title)
            f_out.write('\n\n')
            f_out.write(self.subtitles)
```

Now let's save a transcript to file:
# Setup data directory
data_root = Path('data')
data_root.mkdir(exist_ok=True)

# Create and save subtitles
s = Subtitles(
    video_id=video_id,
    video_title="Your Video Title",
    subtitles=subtitles
)

subtitles_file = data_root / f"{s.video_id}.txt"
s.write_file(subtitles_file)
```

## Processing Multiple Videos

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

# Filter for podcasts with YouTube links
podcasts = [d for d in events_data if (d.get('type') == 'podcast') and (d.get('youtube'))]
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
```

Install tqdm for progress tracking:

```bash
uv add tqdm
```

Create a workflow that:

1. Checks if transcript already exists
2. Fetches transcript if needed
3. Formats and saves it

```python
from tqdm.auto import tqdm

def workflow(video_id, video_name):
    subtitles_file = data_root / f"{video_id}.txt"
    
    # Skip if already processed
    if subtitles_file.exists():
        return subtitles_file

    # Fetch and process
    transcript = fetch_transcript(video_id)
    subtitles = make_subtitles(transcript)

    # Save
    s = Subtitles(
        video_id=video_id,
        video_title=video_name,
        subtitles=subtitles
    )
    s.write_file(subtitles_file)
    
    return subtitles_file

# Process all videos with progress bar
for video in tqdm(videos):
    video_id = video['video_id']
    video_name = video['title']
    workflow(video_id, video_name)
```

## Using Proxies


At some point you encounter rate limiting. We fix it by using a proxy

I have a proxy that I will use. Let's configure it. 

create `.env` file:

```bash
PROXY_BASE_URL=...
PROXY_USER=...
PROXY_PASSWORD=...
```

create `.gitignore` with `.env`

use `dirdotenv` to automatically load these variables

Stop jupyter 

```bash
echo 'eval "$(uvx dirdotenv hook bash)"' >> .bashrc
source .bashrc
```

Start again and let's add proxies:


```python
import os
from youtube_transcript_api.proxies import GenericProxyConfig

# Set up proxy configuration
proxy_user = os.getenv('PROXY_USER')
proxy_password = os.getenv('PROXY_PASSWORD')
proxy_base_url = os.getenv('PROXY_BASE_URL')

proxy_url = f'http://{proxy_user}:{proxy_password}@{proxy_base_url}'

proxy = GenericProxyConfig(
    http_url=proxy_url,
    https_url=proxy_url,
)

# Update fetch function to use proxy
def fetch_transcript(video_id):
    ytt_api = YouTubeTranscriptApi(proxy_config=proxy)
    transcript = ytt_api.fetch(video_id)
    return transcript
```

But even with proxies we have problems:

- sometimes our requests are still blocked by IP
- sometimes we get SSL errors (`SSLError: [SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:2648)`)
- other problems 

So we need to have a reliable way of retrying it.

First, we put everything in a single script, and then automate this script with Temporal.io.

## Creating a workflow script 

Let's put everything in a Python script `workflow.py` (created from `youtube.py`)

Run the script:

```bash
uv run python workflow.py
```


The script will:
1. Fetch the list of podcast videos from DataTalks.Club
2. For each video, check if transcript already exists
3. Download and process transcripts
4. Save them to the `data/` directory
5. Show progress with a progress bar
6. Handle errors gracefully and continue with other videos


## Temporal.io

Now let's do it with Temporal

When processing multiple YouTube transcripts, we face several challenges:

1. Reliability: Network requests can fail due to rate limiting, timeouts, or SSL errors
2. Retries: We need smart retry logic with exponential backoff
3. Progress Tracking: If the script crashes, we need to resume from where we left off
4. Observability: We want to monitor which videos succeeded or failed
5. Scalability: Process multiple videos concurrently while respecting API limits

Temporal.io solves these problems by providing:

- Durable execution: Workflows survive crashes and restarts
- Built-in retries: Automatic retry policies with backoff
- State management: No need to manually track progress
- Visibility: Web UI to monitor workflow execution
- Concurrency control: Easy to manage parallel execution

### Installing Temporal

**For Linux:**

```bash
# Create a dir for executables
echo 'PATH="${PATH}:~/bin"' >> ~/.bashrc
source ~/.bashrc


# Download the Temporal CLI
wget 'https://temporal.download/cli/archive/latest?platform=linux&arch=amd64' -O temporal.tar.gz

# Extract
tar -xzf temporal.tar.gz

# Move to ~/bin
mv temporal ~/bin/
rm temporal.tar.gz LICENSE

# Make it executable
chmod +x ~/bin/temporal
```

**Verify installation:**

```bash
temporal -v
```

You should see output like:

```
temporal version 1.5.1 (Server 1.29.1, UI 2.42.1)
```


## Dowloading YouTube Transcripts with Temporal.io 

The `flow/` directory contains the complete Temporal.io implementation:

- **`workflow.py`**: Defines the `PodcastTranscriptWorkflow` class that orchestrates the entire process
  - Fetches podcast episodes from DataTalks.Club GitHub repo
  - Extracts video IDs and metadata
  - Processes each video transcript with retry logic
  - Returns summary of successful and failed operations

- **`activities.py`**: Contains all the activity functions:
  - `setup_proxy()`: Checks if proxy configuration is available
  - `fetch_podcast_episodes()`: Fetches podcast list from GitHub
  - `fetch_videos()`: Extracts video IDs from podcast data
  - `process_video()`: Downloads and saves individual transcripts

- **`worker.py`**: Starts the Temporal worker that executes workflows and activities

- **`run_workflow.py`**: Client script to start and execute the workflow

The workflow includes built-in retry policies with exponential backoff (3 attempts, 1-30 second intervals) for all activities.

## Workflow Implementation

First version:

```python
use_proxy = await workflow.execute_activity(
    setup_proxy,
    start_to_close_timeout=timedelta(seconds=10),
)

# Fetch podcast episodes
workflow.logger.info("Fetching podcast episodes...")
podcasts = await workflow.execute_activity(
    fetch_podcast_episodes,
    commit_id,
    start_to_close_timeout=timedelta(seconds=30),
)
workflow.logger.info(f"Found {len(podcasts)} podcast episodes")

# Fetch videos
workflow.logger.info("Fetching video list...")
videos = await workflow.execute_activity(
    fetch_videos,
    podcasts,
    start_to_close_timeout=timedelta(seconds=10),
)
workflow.logger.info(f"Found {len(videos)} videos")

# Process all videos
successful = 0
failed = 0
failed_videos = []

for video in videos:
    video_id = video['video_id']
    video_name = video['title']
    
    try:
        result = await workflow.execute_activity(
            process_video,
            args=[video_id, video_name, use_proxy],
            start_to_close_timeout=timedelta(seconds=60),
        )
        
        if result:
            successful += 1
            workflow.logger.info(f"Processed {video_id}: {video_name}")
    except Exception as e:
        failed += 1
        failed_videos.append({
            'video_id': video_id,
            'title': video_name,
            'error': str(e)
        })
        workflow.logger.error(f"Failed to process {video_id}: {e}")

return {
    'total': len(videos),
    'successful': successful,
    'failed': failed,
    'failed_videos': failed_videos
}
```

## Running the Workflow

To run the complete workflow, you need **three terminals**:

**Terminal 1 - Start Temporal Server:**

```bash
temporal server start-dev
```

This starts the Temporal server in development mode with an in-memory database. The server runs on:
- gRPC: `localhost:7233` (for workflow/activity execution)
- Web UI: `http://localhost:8233` (for monitoring)

For persistence across restarts, use:
```bash
temporal server start-dev --db-filename temporal.db
```

**Terminal 2 - Start the Worker:**

```bash
cd flow
uv run python worker.py
```

The worker connects to the Temporal server and registers workflows/activities. Keep this running.

**Terminal 3 - Execute the Workflow:**

```bash
cd flow
uv run python run_workflow.py
```

This triggers the workflow execution. Watch the progress in:
- Terminal 2: Worker logs showing activity executions
- Terminal 3: Final results summary
- Browser: `http://localhost:8233` for detailed workflow visualization


## Retrials

We can add retrials explicitly:

```python
retry_policy = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)

...

result = await workflow.execute_activity(
    ...
    retry_policy=retry_policy,
)
```

## Ingesting Data to Elasticsearch

After downloading the transcripts, you can create another Temporal workflow to index them in Elasticsearch for full-text search.


Run Elasticsearch in Docker:

```bash
docker run -it \
  --rm \
  --name elasticsearch \
  -m 4GB \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -v es-data9:/usr/share/elasticsearch/data \
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

### Setting Up the Index

Connect to Elasticsearch:

```python
from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")
```

Create an index with custom analyzers for better search. We'll use English stemming and stopword removal:

```python
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
```

Create the index:

```python
es.indices.create(index="podcasts", body=index_settings)
```

### Indexing Documents

Read all transcript files and index them:

```python
from pathlib import Path
from tqdm.auto import tqdm

data = Path('data/')
files = sorted(data.glob('*.txt'))

def read_doc(subtitle_file):
    raw_text = subtitle_file.read_text(encoding='utf8')
    lines = raw_text.split('\n')
    
    video_title = lines[0]
    subtitles = '\n'.join(lines[2:]).strip()
    video_id = subtitle_file.stem
    
    return {
        "video_id": video_id,
        "title": video_title,
        "subtitles": subtitles
    }

# Index all files
for subtitle_file in tqdm(files):
    doc = read_doc(subtitle_file)
    es.index(index="podcasts", id=doc['video_id'], document=doc)
```

### Searching

Create a search function with highlighting:

```python
def search_videos(query: str, size: int=5):
    """
    Search over both `title` and `subtitles`,
    boosting `title` 3x for higher relevance.
    Uses stemming + stopword removal.
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

# Example search
result = search_videos('how do I get rich with ai')
```

Get full subtitles by video ID:

```python
def get_subtitles_by_id(video_id):
    result = es.get(index="podcasts", id=video_id)
    return result['_source']
```

## Turning Indexing into Temporal.io Flow

Now let's implement the indexing process as a Temporal workflow for better reliability, error handling, and observability.

### Implementation Files

We've created three new files in the `flow/` directory:

**1. `index_activities.py`** - Contains Elasticsearch activities:

- `create_index()`: Creates the Elasticsearch index with custom analyzers
  - Supports recreating the index if it already exists
  - Uses the same index settings with stemming and stopwords
  
- `index_document()`: Indexes a single transcript file
  - Reads and parses the transcript file
  - Indexes it into Elasticsearch with the video ID as the document ID
  
- `get_transcript_files()`: Scans the data directory for transcript files
  - Returns a list of file paths to index

**2. `index_workflow.py`** - Defines the `IndexTranscriptsWorkflow`:

```python
@workflow.defn
class IndexTranscriptsWorkflow:
    @workflow.run
    async def run(
        self, 
        data_dir: str = "data",
        es_url: str = "http://localhost:9200",
        recreate_index: bool = False,
        max_concurrent: int = 5
    ) -> dict:
```

The workflow:
1. Creates the Elasticsearch index (or uses existing one)
2. Gets the list of all transcript files
3. Indexes each file sequentially with retry logic
4. Returns summary of successful and failed indexing operations

All activities use retry policies with exponential backoff (3 attempts, 1-10 second intervals).

**3. `run_index_workflow.py`** - Client script to execute the workflow

**4. `worker.py`** - Updated to include the new indexing workflow and activities

### Running the Indexing Workflow

Make sure Elasticsearch is running (see Docker command earlier in this document).

**Terminal 1 - Temporal Server** (if not already running):
```bash
temporal server start-dev
```

**Terminal 2 - Start the Worker:**

The worker has been updated to include both transcript downloading and indexing workflows:

```bash
cd flow
uv run python worker.py
```

**Terminal 3 - Execute the Indexing Workflow:**

```bash
cd flow
uv run python run_index_workflow.py
```

The indexing workflow will:
1. Connect to Elasticsearch at `http://localhost:9200`
2. Create the `podcasts` index with custom analyzers
3. Scan the `data/` directory for transcript files
4. Index each transcript with retry logic
5. Display results showing total files, successful, and failed indexing

You can monitor the workflow execution in the Temporal Web UI at `http://localhost:8233`.

### Configuration Options

You can modify the configuration in `run_index_workflow.py`:

```python
data_dir = "data"              # Directory containing transcript files
es_url = "http://localhost:9200"  # Elasticsearch URL
recreate_index = False         # Set to True to recreate the index
```

Set `recreate_index = True` if you want to delete and recreate the index with fresh data.

## Agent

mkdir agent
cd agent

uv init
uv add pydantic-ai openai elasticsearch python-dotenv
uv add --dev jupyter

add `OPENAI_API_KEY` to `.env`

```
OPENAI_API_KEY='your-key'
```

start jupoyter 

uv run jupyter notebook

creae a new notebook agent.ipynb





## Additional Resources

- [YouTube Transcript API Documentation](https://github.com/jdepoix/youtube-transcript-api)
- [Elasticsearch Python Client](https://elasticsearch-py.readthedocs.io/)
- [DataTalks.Club Podcasts](https://datatalks.club/podcast.html)





