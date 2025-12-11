"""Temporal.io activities for indexing transcripts into Elasticsearch"""

from pathlib import Path
from typing import Optional

from elasticsearch import Elasticsearch
from temporalio import activity


# Elasticsearch configuration
STOPWORDS = [
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

INDEX_SETTINGS = {
    "settings": {
        "analysis": {
            "filter": {
                "english_stop": {
                    "type": "stop",
                    "stopwords": STOPWORDS
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


def read_doc(subtitle_file: Path) -> dict:
    """Read a subtitle file and extract document data"""
    raw_text = subtitle_file.read_text(encoding='utf8')
    lines = raw_text.split('\n')
    
    video_title = lines[0]
    subtitles = '\n'.join(lines[2:]).strip()
    video_id = subtitle_file.stem
    
    return {
        "video_id": video_id,
        "title": video_title,
        "subtitles": subtitles
    }


@activity.defn
async def create_index(es_url: str = "http://localhost:9200", recreate: bool = False) -> bool:
    """Create Elasticsearch index with custom analyzers"""
    activity.logger.info(f"Connecting to Elasticsearch at {es_url}")
    es = Elasticsearch(es_url)
    
    index_name = "podcasts"
    
    # Check if index exists
    if es.indices.exists(index=index_name):
        if recreate:
            activity.logger.info(f"Deleting existing index '{index_name}'")
            es.indices.delete(index=index_name)
        else:
            activity.logger.info(f"Index '{index_name}' already exists, skipping creation")
            return False
    
    # Create index
    activity.logger.info(f"Creating index '{index_name}' with custom analyzers")
    es.indices.create(index=index_name, body=INDEX_SETTINGS)
    activity.logger.info("Index created successfully")
    
    return True


@activity.defn
async def index_document(subtitle_file_path: str, es_url: str = "http://localhost:9200") -> Optional[str]:
    """Index a single document into Elasticsearch"""
    subtitle_file = Path(subtitle_file_path)
    
    if not subtitle_file.exists():
        activity.logger.warning(f"File not found: {subtitle_file_path}")
        return None
    
    activity.logger.info(f"Indexing document from {subtitle_file.name}")
    
    # Read document
    doc = read_doc(subtitle_file)
    
    # Connect to Elasticsearch and index
    es = Elasticsearch(es_url)
    es.index(index="podcasts", id=doc['video_id'], document=doc)
    
    activity.logger.info(f"Successfully indexed {doc['video_id']}: {doc['title']}")
    return doc['video_id']


@activity.defn
async def get_transcript_files(data_dir: str) -> list[str]:
    """Get list of all transcript files in the data directory"""
    activity.logger.info(f"Scanning for transcript files in {data_dir}")
    
    data_path = Path(data_dir)
    if not data_path.exists():
        activity.logger.error(f"Directory not found: {data_dir}")
        return []
    
    files = sorted(data_path.glob('*.txt'))
    file_paths = [str(f) for f in files]
    
    activity.logger.info(f"Found {len(file_paths)} transcript files")
    return file_paths
