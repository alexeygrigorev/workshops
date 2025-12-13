#!/usr/bin/env python
# coding: utf-8

import os

import yaml
import requests

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")


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


def fetch_subtitles(video_id):
    proxy = cteate_proxy_config()
    ytt_api = YouTubeTranscriptApi(proxy_config=proxy)
    transcript = ytt_api.fetch(video_id)
    subtitles = make_subtitles(transcript)
    return subtitles


def find_podcast_videos(commit_id):
    events_url = f'https://raw.githubusercontent.com/DataTalksClub/datatalksclub.github.io/{commit_id}/_data/events.yaml'

    raw_yaml = requests.get(events_url).content
    events_data = yaml.load(raw_yaml, yaml.CSafeLoader)

    # Filter for podcasts with YouTube links
    podcasts = [d for d in events_data if (d.get('type') == 'podcast') and (d.get('youtube'))]

    print(f"Found {len(podcasts)} podcasts")

    videos = []

    for podcast in podcasts:
        _, video_id = podcast['youtube'].split('watch?v=')

        # Skip problematic videos
        if video_id == 'FRi0SUtxdMw':
            continue

        videos.append({
            'title': podcast['title'],
            'video_id': video_id
        })

    print(f"Will process {len(videos)} videos")
    return videos


def workflow():
    commit_id = '187b7d056a36d5af6ac33e4c8096c52d13a078a7'
    videos = find_podcast_videos(commit_id)

    for video in videos:
        video_id = video['video_id']
        video_title = video['title']

        if es.exists(index='podcasts', id=video_id):
            print(f'already processed {video_id}')
            continue

        subtitles = fetch_subtitles(video_id)

        doc = {
            "video_id": video_id,
            "title": video_title,
            "subtitles": subtitles
        }

        es.index(index="podcasts", id=video_id, document=doc)


if __name__ == '__main__':
    workflow()