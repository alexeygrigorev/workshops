import asyncio
from concurrent.futures import ThreadPoolExecutor

from temporalio.worker import Worker
from temporalio.client import Client

from workflow import PodcastTranscriptWorkflow

from activities import (
    fetch_subtitles,
    find_podcast_videos,
    video_exists,
    index_video,
)


async def run_worker():
    client = await Client.connect("localhost:7233")

    executor = ThreadPoolExecutor(max_workers=10)

    worker = Worker(
        client,
        task_queue="podcast_transcript_task_queue",
        workflows=[PodcastTranscriptWorkflow],
        activities=[
            fetch_subtitles,
            find_podcast_videos,
            video_exists,
            index_video,
        ],
        activity_executor=executor,
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())