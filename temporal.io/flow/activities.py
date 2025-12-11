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
from elasticsearch import Elasticsearch


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


def get_es_connection() -> Elasticsearch:
    """Get Elasticsearch connection"""
    es_url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
    return Elasticsearch(es_url)


# Activities
@activity.defn
async def setup_elasticsearch(recreate: bool = False) -> str:
    """Setup Elasticsearch index with custom analyzers"""
    activity.logger.info("Setting up Elasticsearch index")
    
    es = get_es_connection()
    index_name = "podcasts"
    
    # Stopwords for English
    stopwords = [
        "a","about","above","after","again","against","all","am","an","and","any",
        "are","aren","aren't","as","at","be","because","been","before","being",
        "below","between","both","but","by","can","can","can't","cannot","could",
        "couldn't","did","didn't","do","does","doesn't","doing","don't","down",
        "during","each","few","for","from","further","had","hadn't","has","hasn't",
        "have","haven't","having","he","he'd","he'll","he's","her","here","here's",
        "hers","herself","him","himself","his","how","how's","i","i'd","i'll",
        "i'm","i've","if","in","into","is","isn't","it","it's","its","itself",
        "let's","me","more","most","mustn't","my","myself","no","nor","not","of",
        "off","on","once","only","or","other","ought","our","ours","ourselves",
        "out","over","own","same","shan't","she","she'd","she'll","she's","should",
        "shouldn't","so","some","such","than","that","that's","the","their",
        "theirs","them","themselves","then","there","there's","these","they",
        "they'd","they'll","they're","they've","this","those","through","to",
        "too","under","until","up","very","was","wasn't","we","we'd","we'll",
        "we're","we've","were","weren't","what","what's","when","when's","where",
        "where's","which","while","who","who's","whom","why","why's","with",
        "won't","would","wouldn't","you","you'd","you'll","you're","you've",
        "your","yours","yourself","yourselves",
        "get"
    ]
    
    index_settings = {
        "settings": {
            "analysis": {
                "filter": {
                    "english_stop": {
                        "type": "stop",
                        "stopwords": stopwords
                    },
                    "english_stemmer": {
                        "type": "stemmer",
                        "language": "english"
                    },
                    "english_possessive_stemmer": {
                        "type": "stemmer",
                        "language": "possessive_english"
                    }
                },
                "analyzer": {
                    "english_with_stop_and_stem": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "english_possessive_stemmer",
                            "english_stop",
                            "english_stemmer"
                        ]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "title": {
                    "type": "text",
                    "analyzer": "english_with_stop_and_stem",
                    "search_analyzer": "english_with_stop_and_stem"
                },
                "subtitles": {
                    "type": "text",
                    "analyzer": "english_with_stop_and_stem",
                    "search_analyzer": "english_with_stop_and_stem"
                }
            }
        }
    }
    
    # Create or recreate index
    if es.indices.exists(index=index_name):
        if recreate:
            activity.logger.info(f"Deleting existing index: {index_name}")
            es.indices.delete(index=index_name)
            es.indices.create(index=index_name, body=index_settings)
            activity.logger.info(f"Recreated index: {index_name}")
        else:
            activity.logger.info(f"Index {index_name} already exists")
    else:
        es.indices.create(index=index_name, body=index_settings)
        activity.logger.info(f"Created index: {index_name}")
    
    es.close()
    return index_name


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
async def process_video(video_id: str, video_name: str, use_proxy: bool = False) -> bool:
    """Process a single video: fetch transcript and index to Elasticsearch"""
    activity.logger.info(f"Processing video {video_id}: {video_name}")
    
    es = get_es_connection()
    index_name = "podcasts"
    
    # Skip if already indexed
    if es.exists(index=index_name, id=video_id):
        activity.logger.info(f"Video {video_id} already indexed, skipping")
        es.close()
        return False
    
    # Setup proxy if configured
    proxy = get_proxy_config() if use_proxy else None
    
    # Fetch and process transcript
    ytt_api = YouTubeTranscriptApi(proxy_config=proxy)
    transcript = ytt_api.fetch(video_id)
    subtitles = make_subtitles(transcript)
    
    # Index to Elasticsearch
    doc = {
        "video_id": video_id,
        "title": video_name,
        "subtitles": subtitles
    }
    
    es.index(index=index_name, id=video_id, document=doc)
    activity.logger.info(f"Indexed video {video_id} to Elasticsearch")
    
    es.close()
    return True
