"""Temporal.io workflow for indexing transcripts into Elasticsearch"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from index_activities import (
        create_index,
        get_transcript_files,
        index_document,
    )


@workflow.defn
class IndexTranscriptsWorkflow:
    """Workflow to index podcast transcripts into Elasticsearch"""

    @workflow.run
    async def run(
        self, 
        data_dir: str = "data",
        es_url: str = "http://localhost:9200",
        recreate_index: bool = False,
        max_concurrent: int = 5
    ) -> dict:
        """
        Main workflow execution for indexing transcripts
        
        Args:
            data_dir: Directory containing transcript files (default: "data")
            es_url: Elasticsearch URL (default: "http://localhost:9200")
            recreate_index: Whether to recreate the index if it exists (default: False)
            max_concurrent: Maximum number of documents to index concurrently (default: 5)
            
        Returns:
            Dictionary with indexing results
        """
        # Define retry policy for activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3,
            backoff_coefficient=2.0,
        )
        
        # Step 1: Create index
        workflow.logger.info("Creating Elasticsearch index...")
        index_created = await workflow.execute_activity(
            create_index,
            args=[es_url, recreate_index],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        if index_created:
            workflow.logger.info("Index created successfully")
        else:
            workflow.logger.info("Using existing index")
        
        # Step 2: Get list of transcript files
        workflow.logger.info("Getting list of transcript files...")
        file_paths = await workflow.execute_activity(
            get_transcript_files,
            data_dir,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        workflow.logger.info(f"Found {len(file_paths)} files to index")
        
        if not file_paths:
            workflow.logger.warning("No transcript files found")
            return {
                'total': 0,
                'indexed': 0,
                'failed': 0,
                'failed_files': []
            }
        
        # Step 3: Index documents
        indexed = 0
        failed = 0
        failed_files = []
        
        for file_path in file_paths:
            try:
                result = await workflow.execute_activity(
                    index_document,
                    args=[file_path, es_url],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=retry_policy,
                )
                
                if result:
                    indexed += 1
                    workflow.logger.info(f"Indexed: {result} ({indexed}/{len(file_paths)})")
                else:
                    failed += 1
                    failed_files.append(file_path)
            except Exception as e:
                failed += 1
                failed_files.append(file_path)
                workflow.logger.error(f"Failed to index {file_path}: {e}")
        
        workflow.logger.info(f"Indexing complete: {indexed} successful, {failed} failed")
        
        return {
            'total': len(file_paths),
            'indexed': indexed,
            'failed': failed,
            'failed_files': failed_files
        }
