from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import (
        YouTubeActivities,
        ElasticsearchActivities,
        find_podcast_videos,
    )


@workflow.defn
class PodcastTranscriptWorkflow:

    @workflow.run
    async def run(self, commit_id: str) -> dict:
        workflow.logger.info(f"Finding podcast videos from commit {commit_id}...")
        
        videos = await workflow.execute_activity(
            activity=find_podcast_videos,
            args=(commit_id,),
            start_to_close_timeout=timedelta(minutes=1),
        )

        workflow.logger.info("Connecting to Elasticsearch...")

        for video in videos:
            video_id = video['video_id']

            if await workflow.execute_activity(
                activity=ElasticsearchActivities.video_exists,
                args=(video_id, ),
                start_to_close_timeout=timedelta(seconds=10),
            ):
                workflow.logger.info(f'already processed {video_id}')
                continue

            subtitles = await workflow.execute_activity(
                activity=YouTubeActivities.fetch_subtitles,
                args=(video_id,),
                start_to_close_timeout=timedelta(minutes=1),
            )

            await workflow.execute_activity(
                activity=ElasticsearchActivities.index_video,
                args=(video, subtitles, ),
                start_to_close_timeout=timedelta(seconds=30),
            )
        
        return {
            "status": "completed",
            "processed_videos": len(videos),
        }    


# putting imports here to make it easier for the tutorial structure
import asyncio

from temporalio.client import Client



async def run_workflow():
    client = await Client.connect("localhost:7233")

    commit_id = '187b7d056a36d5af6ac33e4c8096c52d13a078a7'

    result = await client.execute_workflow(
        PodcastTranscriptWorkflow.run,
        args=(commit_id, ),
        id="podcast_transcript_workflow",
        task_queue="podcast_transcript_task_queue",
    )

    print("Workflow completed! Result:", result)


if __name__ == "__main__":
    asyncio.run(run_workflow())