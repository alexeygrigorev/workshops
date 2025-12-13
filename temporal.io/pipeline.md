
## Creating a processing pipeline

Now let's turn this into 

Create a workflow function that:

1. Checks if the video is already indexed in Elasticsearch
2. If not, fetches the transcript from YouTube
3. Formats it and indexes it to Elasticsearch

```python
from tqdm.auto import tqdm

def workflow(video_id, video_title) -> bool:
    """Process a single video: fetch transcript and index to Elasticsearch."""
    
    # Check if already indexed
    # TODO: don't use document_exists, use es.exists 
    if document_exists(es, "podcasts", video_id):
        return False

    # Fetch and process transcript from YouTube
    transcript = fetch_transcript(video_id)
    subtitles = make_subtitles(transcript)

    # Prepare document
    doc = {
        "video_id": video_id,
        "title": video_title,
        "subtitles": subtitles
    }
    
    # Index to Elasticsearch
    es.index(index="podcasts", id=video_id, document=doc)
    
    return True
```

Let's now process all the videos:

```python
indexed = 0
skipped = 0
errors = 0

for video in tqdm(videos):
    video_id = video['video_id']
    video_title = video['title']
    
    try:
        result = workflow(video_id, video_title)
        if result == "indexed":
            indexed += 1
        else:
            skipped += 1
    except Exception as e:
        errors += 1
        print(f"Error processing {video_id}: {e}")

print(f"\nProcessing complete:")
print(f"  Indexed: {indexed}")
print(f"  Skipped: {skipped}")
print(f"  Errors: {errors}")
```