# Temporal.io Podcast Transcript Workflow

This is a Temporal.io workflow implementation for processing YouTube podcast transcripts from DataTalks.Club.

## Overview

The workflow fetches podcast episodes from the DataTalks.Club GitHub repository, extracts video IDs, and processes each video to download and save its transcript.

## Project Structure

- `workflow.py` - Main Temporal workflow definition
- `activities.py` - Temporal activities (individual tasks)
- `worker.py` - Temporal worker that executes workflows and activities
- `run_workflow.py` - Client script to start the workflow
- `pyproject.toml` - Project dependencies managed by uv


## Running the Workflow

### Step 1: Start the Temporal Server

If not already running:
```bash
temporal server start-dev
```

This will start the Temporal server on `localhost:7233` and the Web UI on `http://localhost:8233`

### Step 2: Start the Worker

In a new terminal, navigate to the flow directory and start the worker:
```bash
uv run python worker.py
```

The worker will connect to Temporal and wait for workflow tasks.

### Step 3: Run the Workflow

In another terminal, execute the workflow:
```bash
uv run python run_workflow.py
```

This will:

1. Connect to the Temporal server
2. Start the workflow
3. Process all podcast episodes
4. Download and save transcripts to the `data/` directory
5. Display the results

## Monitoring

You can monitor the workflow execution in the Temporal Web UI:
- Open `http://localhost:8233` in your browser
- Navigate to the "Workflows" section
- Find your workflow by ID: `podcast-transcript-workflow`

## Workflow Details

### Workflow: `PodcastTranscriptWorkflow`

The main workflow orchestrates the entire process:
1. Setup proxy configuration (if needed)
2. Fetch podcast episodes from GitHub
3. Extract video IDs
4. Process each video (fetch transcript and save)
5. Return summary of results

### Activities

- `setup_proxy()` - Configure proxy settings from environment variables
- `fetch_podcast_episodes(commit_id)` - Fetch podcast list from GitHub
- `fetch_videos(podcasts)` - Extract video IDs from podcast data
- `process_video(video_id, video_name, proxy_config)` - Download and save transcript

## Output

Transcripts are saved to the `data/` directory with filenames: `{video_id}.txt`

Each file contains:
- Video title
- Timestamped transcript

## Error Handling

- The workflow continues even if individual videos fail
- Failed videos are logged and included in the final results
- Already processed videos are skipped automatically

## Advantages of Using Temporal

1. Reliability - Workflows are durable and survive failures
2. Observability - Full visibility into workflow execution
3. Scalability - Easy to scale workers horizontally
4. Retry Logic - Built-in retry mechanisms for activities
5. State Management - Temporal manages workflow state automatically
6. Time-based Operations - Easy to add delays, timeouts, and schedules
