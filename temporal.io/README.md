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

If you need to use a proxy, set the environment variables first:

```bash
export PROXY_USER="your_user"
export PROXY_PASSWORD="your_password"
export PROXY_BASE_URL="proxy.example.com:8080"
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
# Download the Temporal CLI
wget 'https://temporal.download/cli/archive/latest?platform=linux&arch=amd64' -O temporal.tar.gz

# Extract
tar -xzf temporal.tar.gz

# Move to a directory in your PATH (e.g., ~/bin or /usr/local/bin)
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

### Setup

First, make sure Elasticsearch is running (see the Docker command at the bottom of this document).

Install the Elasticsearch Python client:

```bash
uv add elasticsearch
```

### Create Elasticsearch Activities

Add these activities to handle Elasticsearch operations:

```python
from elasticsearch import Elasticsearch

@activity.defn
async def create_index():
    """Create Elasticsearch index with proper mappings"""
    es = Elasticsearch("http://localhost:9200")
    
    index_settings = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "video_id": {"type": "keyword"},
                "title": {"type": "text"},
                "text": {"type": "text"},
                "timestamp": {"type": "keyword"}
            }
        }
    }
    
    if not es.indices.exists(index="podcasts"):
        es.indices.create(index="podcasts", body=index_settings)
    
    return True

@activity.defn
async def index_transcript(video_id: str, video_title: str, subtitles_file: str):
    """Index a transcript file into Elasticsearch"""
    es = Elasticsearch("http://localhost:9200")
    
    # Read and parse the transcript file
    with open(subtitles_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()[2:]  # Skip title and blank line
    
    # Index each subtitle entry
    for line in lines:
        if not line.strip():
            continue
            
        parts = line.split(' ', 1)
        if len(parts) == 2:
            timestamp, text = parts
            
            doc = {
                "video_id": video_id,
                "title": video_title,
                "timestamp": timestamp.strip(),
                "text": text.strip()
            }
            
            es.index(index="podcasts", document=doc)
    
    return True
```

### Create Indexing Workflow

Create a new workflow in `flow/index_workflow.py`:

```python
@workflow.defn
class IndexTranscriptsWorkflow:
    """Workflow to index transcripts into Elasticsearch"""
    
    @workflow.run
    async def run(self) -> dict:
        # Create index
        await workflow.execute_activity(
            create_index,
            start_to_close_timeout=timedelta(seconds=30),
        )
        
        # Get all transcript files
        transcript_files = list(data_root.glob("*.txt"))
        
        # Index each file
        indexed = 0
        for file_path in transcript_files:
            video_id = file_path.stem
            
            with open(file_path, 'r', encoding='utf-8') as f:
                video_title = f.readline().strip()
            
            await workflow.execute_activity(
                index_transcript,
                args=[video_id, video_title, str(file_path)],
                start_to_close_timeout=timedelta(seconds=60),
            )
            indexed += 1
        
        return {"indexed": indexed, "total": len(transcript_files)}
```

Run the indexing workflow similarly to the transcript workflow - start the worker with the new workflow and activities, then execute it with a client script.


## Additional Resources

- [YouTube Transcript API Documentation](https://github.com/jdepoix/youtube-transcript-api)
- [Elasticsearch Python Client](https://elasticsearch-py.readthedocs.io/)
- [DataTalks.Club Podcasts](https://datatalks.club/podcast.html)





## Start Elasticsearch

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
  -v es-data:/usr/share/elasticsearch/data \
  docker.elastic.co/elasticsearch/elasticsearch:8.4.3
```

Verify it's running:

```bash
curl http://localhost:9200
```
