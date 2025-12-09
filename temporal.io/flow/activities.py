"""Temporal.io activities for processing YouTube podcast transcripts"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
import yaml
from temporalio import activity
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig


# Configuration
data_root = Path('data')
data_root.mkdir(exist_ok=True)


# Data structures
@dataclass
class Subtitles:
    video_id: str
    video_title: str
    subtitles: str

    def write_file(self, subtitles_file: Path):
        with subtitles_file.open('wt', encoding='utf-8') as f_out:
            f_out.write(self.video_title)
            f_out.write('\n\n')
            f_out.write(self.subtitles)


# Helper functions
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


def get_proxy_config() -> Optional[GenericProxyConfig]:
    """Get proxy configuration from environment variables"""
    proxy_user = os.getenv('PROXY_USER')
    proxy_password = os.getenv('PROXY_PASSWORD')
    proxy_base_url = os.getenv('PROXY_BASE_URL')
    
    if not all([proxy_user, proxy_password, proxy_base_url]):
        return None
    
    proxy_url = f'http://{proxy_user}:{proxy_password}@{proxy_base_url}'
    return GenericProxyConfig(
        http_url=proxy_url,
        https_url=proxy_url,
    )


# Activities
@activity.defn
async def setup_proxy() -> bool:
    """Check if proxy configuration is available in environment variables"""
    activity.logger.info("Checking proxy configuration")
    
    proxy_config = get_proxy_config()
    
    if proxy_config is None:
        activity.logger.info("No proxy configuration found")
        return False

    activity.logger.info("Proxy configuration available")
    return True


@activity.defn
async def fetch_podcast_episodes(commit_id: str) -> list:
    """Fetch list of videos from DataTalks.Club"""
    activity.logger.info(f"Fetching podcast episodes from commit {commit_id}")
    
    prefix = 'https://raw.githubusercontent.com/DataTalksClub/datatalksclub.github.io'
    events_url = f'{prefix}/{commit_id}/_data/events.yaml'

    raw_yaml = requests.get(events_url).content
    events_data = yaml.load(raw_yaml, yaml.CSafeLoader)
    
    podcasts = [d for d in events_data 
                if (d.get('type') == 'podcast') and (d.get('youtube'))]

    return podcasts


@activity.defn
async def fetch_videos(podcasts: list) -> list:
    """Extract video IDs and titles from podcasts"""
    activity.logger.info(f"Extracting videos from {len(podcasts)} podcasts")
    
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
    
    return videos


@activity.defn
async def process_video(video_id: str, video_name: str, use_proxy: bool = False) -> Optional[str]:
    """Process a single video: fetch transcript and save to file"""
    activity.logger.info(f"Processing video {video_id}: {video_name}")
    
    subtitles_file = data_root / f"{video_id}.txt"
    
    # Skip if already processed
    if subtitles_file.exists():
        activity.logger.info(f"Video {video_id} already processed, skipping")
        return str(subtitles_file)
    
    # Setup proxy if configured
    proxy = get_proxy_config() if use_proxy else None
    
    # Fetch and process
    ytt_api = YouTubeTranscriptApi(proxy_config=proxy)
    transcript = ytt_api.fetch(video_id)
    subtitles = make_subtitles(transcript)
    
    # Save
    s = Subtitles(
        video_id=video_id,
        video_title=video_name,
        subtitles=subtitles
    )
    s.write_file(subtitles_file)

    activity.logger.info(f"Saved transcript to {subtitles_file}")
    return str(subtitles_file)
