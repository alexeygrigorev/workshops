# AI Research Agent with Temporal

This project implements a durable AI research agent using Pydantic AI and Temporal. The agent performs deep, multi-stage research on topics by searching video content, analyzing transcripts, and generating comprehensive reports.

## Features

- **Durable Execution**: Survives API failures, system crashes, and deployments
- **Multi-Stage Research**: Performs initial exploration followed by deep investigation
- **Video Search**: Searches video titles and subtitles using Elasticsearch
- **Smart Summarization**: Summarizes video content to avoid context length issues
- **Comprehensive Reports**: Generates detailed markdown reports with citations
- **Type Safety**: Full type safety with Pydantic models throughout

## Architecture

The system uses a multi-agent architecture:

1. **Research Agent**: Orchestrates the research process, performs searches, and generates reports
2. **Summarization Agent**: Summarizes video transcripts while preserving key information

The workflow is coordinated by Temporal, with:
- **Activities**: Elasticsearch searches and data retrieval (non-deterministic operations)
- **Workflow**: Agent coordination and research orchestration (deterministic execution)

## Prerequisites

1. **Temporal Server**: Install and start the Temporal dev server
   ```bash
   # Install Temporal CLI (if not already installed)
   # On macOS:
   brew install temporal
   
   # On Windows/Linux, download from:
   # https://github.com/temporalio/cli/releases
   
   # Start Temporal dev server
   temporal server start-dev
   ```

2. **Elasticsearch**: Running instance with podcasts index
   ```bash
   # Make sure Elasticsearch is running on http://localhost:9200
   # with the 'podcasts' index containing video data
   ```

3. **OpenAI API Key**: Set in environment variable
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

## Installation

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Create a `.env` file (optional):
   ```
   OPENAI_API_KEY=your-api-key-here
   ELASTICSEARCH_HOST=http://localhost:9200
   TEMPORAL_ADDRESS=localhost:7233
   ```

## Usage

### 1. Start the Worker

In one terminal, start the Temporal worker:

```bash
uv run python worker.py
```

You should see:
```
Worker started, listening on task queue: research-task-queue
Press Ctrl+C to stop...
```

### 2. Run a Research Workflow

In another terminal, start a research workflow:

```bash
# With a specific query
uv run python start_workflow.py "how do I get rich with AI?"

# Or with default query
uv run python start_workflow.py
```

The workflow will:
1. Perform 3-5 initial broad searches
2. Conduct 5-6 deep investigation searches
3. Summarize relevant video content
4. Generate a comprehensive research report

The report will be:
- Printed to the console
- Saved as a markdown file (e.g., `research_report_research-workflow-Task-1.md`)

## How It Works

### Temporal Workflow

The `ResearchWorkflow` orchestrates the entire research process:

```python
@workflow.defn
class ResearchWorkflow:
    @workflow.run
    async def run(self, query: str) -> str:
        # 1. Set up tools that use Temporal activities
        # 2. Create research agent with tools
        # 3. Wrap agent with TemporalAgent
        # 4. Execute research
        # 5. Return formatted report
```

### Durable Execution Benefits

1. **API Failure Recovery**: If OpenAI API times out, Temporal automatically retries
2. **State Preservation**: Conversation history and search results are preserved
3. **Resumable Execution**: Can pause for hours/days without losing progress
4. **No Manual Checkpointing**: Temporal handles all state management

### Activities

Activities wrap non-deterministic operations:

- `search_videos_activity`: Searches Elasticsearch for relevant videos
- `get_subtitles_activity`: Retrieves video subtitles

These can fail and retry independently without re-running the entire workflow.

### Agent Tools

The research agent has access to two tools:

1. **search_videos**: Searches for videos (calls Temporal activity)
2. **summarize_video**: Summarizes video content (uses summarization agent)

## Research Process

The agent follows a structured research process:

### Stage 1: Initial Exploration
- Performs 3-5 broad search queries
- Identifies main topics and related areas
- Summarizes key concepts and themes

### Stage 2: Deep Investigation
- Performs 5-6 refined, focused queries
- Analyzes specific mechanisms and case studies
- Gathers diverse viewpoints

### Report Generation
- Creates comprehensive markdown report with:
  - Title and introduction (2-3 paragraphs)
  - 10-12 detailed sections
  - 4-6 paragraphs per section
  - Citations with video IDs and timestamps
  - Conclusion (2-3 paragraphs)

## Monitoring

Access the Temporal Web UI to monitor workflows:

```
http://localhost:8233
```

You can:
- View workflow execution history
- See activity retries
- Inspect workflow state
- Debug failures

## Example Output

```markdown
# Deep Research Report

**Research Query:** how do I get rich with AI?

**Total Searches Conducted:** 8
**Unique Videos Analyzed:** 15

---

# Getting Rich with AI: A Comprehensive Guide

## Introduction

Artificial Intelligence has emerged as one of the most transformative technologies
of the 21st century, creating unprecedented opportunities for wealth creation...

[10+ detailed sections with citations]

## Conclusion

The path to wealth through AI is multifaceted, requiring a combination of
technical expertise, business acumen, and strategic thinking...

---

## Research Metadata

**Search Queries Executed:**
- investment opportunities in AI
- starting AI-focused businesses
- AI applications in wealth generation
...
```

## Troubleshooting

### Import Errors

If you see import errors for `temporalio` or `elasticsearch`, run:
```bash
uv sync
```

### Temporal Server Not Running

Make sure the Temporal dev server is running:
```bash
temporal server start-dev
```

### Elasticsearch Connection Issues

Verify Elasticsearch is accessible:
```bash
curl http://localhost:9200
```

### OpenAI API Errors

Ensure your API key is set:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Project Structure

```
agent/
├── activities.py          # Temporal activities (Elasticsearch operations)
├── models.py             # Pydantic data models
├── workflow.py           # Main research workflow
├── worker.py             # Temporal worker
├── start_workflow.py     # Workflow starter script
├── agent.py              # Original notebook code (reference)
├── pyproject.toml        # Project dependencies
└── README.md             # This file
```

## Learn More

- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [Pydantic AI + Temporal Integration](https://ai.pydantic.dev/durable-exec/temporal/)
- [Temporal Python SDK](https://docs.temporal.io/dev-guide/python)
- [Temporal Deep Research Example](https://docs.temporal.io/deep-research)

## Next Steps

1. **Add More Tools**: Extend the agent with additional research capabilities
2. **Improve Summarization**: Fine-tune the summarization strategy
3. **Add Human-in-the-Loop**: Use Temporal signals for approval workflows
4. **Scale Up**: Deploy to production with Temporal Cloud
5. **Add Observability**: Integrate with Pydantic Logfire for detailed traces
