"""Start the research workflow."""

import asyncio
import sys
import os
from temporalio.client import Client
from dotenv import load_dotenv

from workflow import ResearchWorkflow


async def main():
    """Start a new research workflow execution."""
    # Load environment variables
    load_dotenv()
    
    # Get query from command line or use default
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "how do I get rich with AI?"
    
    # Get Temporal server address
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    
    # Connect to Temporal
    client = await Client.connect(temporal_address)
    
    # Start workflow
    print(f"Starting research workflow with query: {query}")
    print("This may take several minutes...")
    print()
    
    handle = await client.start_workflow(
        ResearchWorkflow.run,
        query,
        id=f"research-workflow-{asyncio.current_task().get_name()}",
        task_queue="research-task-queue",
    )
    
    print(f"Workflow started with ID: {handle.id}")
    print(f"Workflow run ID: {handle.result_run_id}")
    print()
    print("Waiting for result...")
    print()
    
    # Wait for result
    result = await handle.result()
    
    print("=" * 80)
    print("RESEARCH REPORT")
    print("=" * 80)
    print()
    print(result)
    print()
    print("=" * 80)
    
    # Save to file
    output_file = f"research_report_{handle.id}.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)
    
    print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
