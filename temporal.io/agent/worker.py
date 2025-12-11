"""Temporal worker for the research workflow."""

import asyncio
import os
from temporalio.client import Client
from temporalio.worker import Worker
from dotenv import load_dotenv

from workflow import ResearchWorkflow
from activities import search_videos_activity, get_subtitles_activity


async def main():
    """Run the Temporal worker."""
    # Load environment variables
    load_dotenv()
    
    # Get Temporal server address
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    
    # Connect to Temporal
    client = await Client.connect(temporal_address)
    
    # Create worker
    worker = Worker(
        client,
        task_queue="research-task-queue",
        workflows=[ResearchWorkflow],
        activities=[search_videos_activity, get_subtitles_activity],
    )
    
    print("Worker started, listening on task queue: research-task-queue")
    print("Press Ctrl+C to stop...")
    
    # Run the worker
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
