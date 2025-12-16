import asyncio
from concurrent.futures import ThreadPoolExecutor

from temporalio.worker import Worker
from temporalio.client import Client

from workflow import PodcastTranscriptWorkflow

from activities import (
    YouTubeActivities,
    ElasticsearchActivities,
    find_podcast_videos,
)


async def run_worker():
    client = await Client.connect("localhost:7233")

    executor = ThreadPoolExecutor(max_workers=10)

    yt_activities = YouTubeActivities()
    es_activities = ElasticsearchActivities()

    worker = Worker(
        client,
        task_queue="podcast_transcript_task_queue",
        workflows=[PodcastTranscriptWorkflow],
        activities=[
            find_podcast_videos,
            yt_activities.fetch_subtitles,
            es_activities.video_exists,
            es_activities.index_video,
        ],
        activity_executor=executor,
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())