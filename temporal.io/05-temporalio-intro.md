
Install 

uv init 
uv add temporalio


Activity is non-deterministic code or operation that may fail (API requests, database calls). decorate a function with @activity.defn.

Workflow executes the activities. It's a class annotated with @workflow.defn that has an async run method annotated with @workflow.run


Task Queue
The Task Queue is where Temporal Workflows look for Workflows and Activities to execute. You define Task Queues by assigning a name as a string. You'll use this Task Queue name when you start a Workflow Execution, and you'll use it again when you define your Workers.

You can see the inputs and results of the Workflow Execution by clicking the Input and Results section:


A Worker is responsible for executing 


Running code:


```
import asyncio
from temporalio.client import Client


async def main():
    client = await Client.connect("localhost:7233")

    # Execute a workflow
    result = await client.execute_workflow(
        WorkflowClass.run,
        "Temporal",
        id="hello-workflow", task_queue="hello-task-queue"
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
```



uv run python main.py

go to http://localhost:8233/namespaces/default/workflows to see it running (and saying you need a queue)

you typically invoke it when something happens - en event triggered, or you want process a new piece of data, etc

to actually process it you need a worker


intead of waiing, you can exit immediately (or continue doing some other things). use start_workflow for that

execute_workflow() - Starts the workflow and waits for it to complete (blocking)
start_workflow() - Starts the workflow and returns immediately with a handle


run it: 

uv run python run_worker.py