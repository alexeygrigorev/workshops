"""Temporal.io workflow for processing YouTube podcast transcripts"""

import asyncio
from datetime import timedelta
from typing import List, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import (
        fetch_podcast_episodes,
        fetch_videos,
        process_video,
        setup_elasticsearch,
        setup_proxy,
    )


@workflow.defn
class PodcastTranscriptWorkflow:
    """Workflow to process podcast transcripts from YouTube"""

    @workflow.run
    async def run(self, commit_id: str, max_concurrent: int = 10, recreate_index: bool = False) -> dict:
        """
        Main workflow execution
        
        Args:
            commit_id: GitHub commit ID to fetch podcast episodes from
            max_concurrent: Maximum number of videos to process concurrently (default: 10)
            recreate_index: Whether to recreate the Elasticsearch index (default: False)
            
        Returns:
            Dictionary with processing results
        """
        # Define retry policy for activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
            backoff_coefficient=2.0,
        )
        
        # Setup Elasticsearch index
        workflow.logger.info("Setting up Elasticsearch index...")
        await workflow.execute_activity(
            setup_elasticsearch,
            recreate_index,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        use_proxy = await workflow.execute_activity(
            setup_proxy,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=retry_policy,
        )

        # Fetch podcast episodes
        workflow.logger.info("Fetching podcast episodes...")
        podcasts = await workflow.execute_activity(
            fetch_podcast_episodes,
            commit_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        workflow.logger.info(f"Found {len(podcasts)} podcast episodes")

        # Fetch videos
        workflow.logger.info("Fetching video list...")
        videos = await workflow.execute_activity(
            fetch_videos,
            podcasts,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=retry_policy,
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
                    retry_policy=retry_policy,
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
