"""Client to start the podcast transcript workflow"""

import asyncio
import logging

from temporalio.client import Client

from workflow import PodcastTranscriptWorkflow


async def main():
    """Start the workflow"""
    logging.basicConfig(level=logging.INFO)
    
    # Connect to Temporal server
    client = await Client.connect("localhost:7233")
    
    # Start the workflow
    commit_id = '187b7d056a36d5af6ac33e4c8096c52d13a078a7'
    max_concurrent = 10  # Process up to 10 videos concurrently
    
    logging.info(f"Starting workflow with commit_id: {commit_id}, max_concurrent: {max_concurrent}")
    
    result = await client.execute_workflow(
        PodcastTranscriptWorkflow.run,
        args=[commit_id, max_concurrent],
        id="podcast-transcript-workflow",
        task_queue="podcast-transcript-queue",
    )
    
    logging.info("Workflow completed!")
    logging.info(f"Results: {result}")
    
    print(f"\nTotal videos: {result['total']}")
    print(f"Successful: {result['successful']}")
    print(f"Failed: {result['failed']}")
    
    if result['failed_videos']:
        print("\nFailed videos:")
        for video in result['failed_videos']:
            print(f"  - {video['video_id']}: {video['title']}")
            print(f"    Error: {video['error']}")


if __name__ == "__main__":
    asyncio.run(main())
