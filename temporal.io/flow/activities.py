import os

import yaml
import requests

from elasticsearch import Elasticsearch
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

from temporalio import activity


def cteate_proxy_config():
    proxy_user = os.environ['PROXY_USER']
    proxy_password = os.environ['PROXY_PASSWORD']
    proxy_base_url = os.environ['PROXY_BASE_URL']

    proxy_url = f'http://{proxy_user}:{proxy_password}@{proxy_base_url}'

    return GenericProxyConfig(
        http_url=proxy_url,
        https_url=proxy_url,
    )


def format_timestamp(seconds: float) -> str:
    """Convert seconds to H:MM:SS if > 1 hour, else M:SS"""
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours == 0:
        return f"{minutes}:{secs:02}"
    return f"{hours}:{minutes:02}:{secs:02}"


def make_subtitles(transcript) -> str:
    lines = []

    for entry in transcript:
        ts = format_timestamp(entry.start)
        text = entry.text.replace('\n', ' ')
        lines.append(ts + ' ' + text)

    return '\n'.join(lines)


class YouTubeActivities: 
    def __init__(self, use_proxy: bool = True):
        if use_proxy:
            self.proxy_config = cteate_proxy_config()
        else:
            self.proxy_config = None


    @activity.defn
    def fetch_subtitles(self, video_id):
        ytt_api = YouTubeTranscriptApi(proxy_config=self.proxy_config)
        transcript = ytt_api.fetch(video_id)
        subtitles = make_subtitles(transcript)
        return subtitles


class ElasticsearchActivities:

    def __init__(self, es_address: str = None):
        if es_address is None:
            es_address = os.getenv('ELASTICSEARCH_ADDRESS', 'http://localhost:9200')
        self.es = Elasticsearch(es_address)

    @activity.defn
    def video_exists(self, video_id):
        resp = self.es.exists(index="podcasts", id=video_id)
        return resp.body

    @activity.defn
    def index_video(self, video, subtitles):
        video_id = video['video_id']
        video_title = video['title']
        
        doc = {
            "video_id": video_id,
            "title": video_title,
            "subtitles": subtitles
        }

        self.es.index(index="podcasts", id=video_id, document=doc)


@activity.defn
def find_podcast_videos(commit_id):
    events_url = f'https://raw.githubusercontent.com/DataTalksClub/datatalksclub.github.io/{commit_id}/_data/events.yaml'

    raw_yaml = requests.get(events_url).content
    events_data = yaml.load(raw_yaml, yaml.CSafeLoader)

    podcasts = [d for d in events_data if (d.get('type') == 'podcast') and (d.get('youtube'))]

    print(f"Found {len(podcasts)} podcasts")

    videos = []

    for podcast in podcasts:
        _, video_id = podcast['youtube'].split('watch?v=')

        # Skip problematic videos
        if video_id in ['FRi0SUtxdMw', 's8kyzy8V5b8']:
            continue

        videos.append({
            'title': podcast['title'],
            'video_id': video_id
        })

    print(f"Will process {len(videos)} videos")
    return videos

