"""Client to start the Elasticsearch indexing workflow"""

import asyncio
import logging

from temporalio.client import Client

from index_workflow import IndexTranscriptsWorkflow


async def main():
    """Start the indexing workflow"""
    logging.basicConfig(level=logging.INFO)
    
    # Connect to Temporal server
    client = await Client.connect("localhost:7233")
    
    # Configuration
    data_dir = "data"  # Directory containing transcript files
    es_url = "http://localhost:9200"  # Elasticsearch URL
    recreate_index = False  # Set to True to recreate the index
    
    logging.info(f"Starting indexing workflow...")
    logging.info(f"  Data directory: {data_dir}")
    logging.info(f"  Elasticsearch URL: {es_url}")
    logging.info(f"  Recreate index: {recreate_index}")
    
    result = await client.execute_workflow(
        IndexTranscriptsWorkflow.run,
        args=[data_dir, es_url, recreate_index],
        id="index-transcripts-workflow",
        task_queue="podcast-transcript-queue",
    )
    
    logging.info("Workflow completed!")
    logging.info(f"Results: {result}")
    
    print(f"\n{'='*50}")
    print(f"Indexing Results")
    print(f"{'='*50}")
    print(f"Total files: {result['total']}")
    print(f"Successfully indexed: {result['indexed']}")
    print(f"Failed: {result['failed']}")
    
    if result['failed_files']:
        print(f"\nFailed files:")
        for file_path in result['failed_files']:
            print(f"  - {file_path}")
    else:
        print(f"\n✓ All files indexed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
