"""Temporal.io worker for podcast transcript processing"""

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from activities import (
    fetch_podcast_episodes,
    fetch_videos,
    process_video,
    setup_elasticsearch,
    setup_proxy,
)
from index_activities import (
    create_index,
    get_transcript_files,
    index_document,
)
from workflow import PodcastTranscriptWorkflow
from index_workflow import IndexTranscriptsWorkflow


async def main():
    """Main entry point for the worker"""
    logging.basicConfig(level=logging.INFO)
    
    # Connect to Temporal server
    # Default is localhost:7233
    client = await Client.connect("localhost:7233")
    
    # Create a worker
    worker = Worker(
        client,
        task_queue="podcast-transcript-queue",
        workflows=[PodcastTranscriptWorkflow, IndexTranscriptsWorkflow],
        activities=[
            setup_elasticsearch,
            setup_proxy,
            fetch_podcast_episodes,
            fetch_videos,
            process_video,
            create_index,
            get_transcript_files,
            index_document,
        ],
    )
    
    logging.info("Worker starting...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
