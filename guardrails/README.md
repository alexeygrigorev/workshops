# Guardrails for AI Agents

This workshop is about making AI agents safer with guardrails. It is a part of the
[AI Bootcamp: From RAG to Agents](https://maven.com/alexey-grigorev/from-rag-to-agents) course.

* [Video](https://www.youtube.com/watch?v=Sk1aqwNJWT4) 
* [Code](notebook.ipynb)

This work


## Prerequisites

- Python 3.10+
- OpenAI API key


## What are Guardrails?

Guardrails are safety checks that run before (input) or after (output) your agent executes.

```
Input Guardrail:  User -> [CHECK] -> Agent (only if check passes)
Output Guardrail: Agent -> [CHECK] -> User (only if check passes)
```

Why do we need them?

- Agents can be tricked into harmful behavior
- Agents may drift off-topic
- Agents might make inappropriate promises (e.g., refunds, legal advice)
- You want to restrict what your agent can talk about


## Part 1: Building an Agent (Starting Point)

Before adding guardrails, let's build a complete agent with tools. We'll create a DataTalks.Club FAQ Assistant that helps students find answers about the Data Engineering Zoomcamp.

setup:

First, install the required dependencies:

```bash
pip install uv
uv init
uv add jupyter openai openai-agents minsearch requests python-frontmatter
```

Add your OpenAI key in `.env`:

```
OPENAI_API_KEY='your-key'
```

Make sure `.env` is in `.gitignore`:

```bash
echo .env >> .gitignore
```

I use `dirdotenv` to get access to the env variables from `.env` and `.envrc` to my terminal:

```bash
pip install dirdotenv
echo 'eval "$(dirdotenv hook bash)"' >> ~/.bashrc
```

Start the notebook:

```bash
uv run jupyter notebook
```

Loading FAQ data from GitHub:

For this workshop, we will create an agent that uses [FAQ data from DataTalks.Club courses](https://datatalks.club/faq/).

The data for the FAQ is in [a GitHub repo](https://datatalks.club/faq/), so we will use it. We can download all the data as a ZIP archive,  

This logic is implemented inside `docs.py` file with a `GithubRepositoryDataReader` class that downloads markdown files from any GitHub repository. 

> **Want to learn more?** Check out this free email course to learn how `docs.py` works and how to build your first AI agent: https://alexeygrigorev.com/aihero/

Download `docs.py`:

```bash
wget https://raw.githubusercontent.com/alexeygrigorev/workshops/refs/heads/main/guardrails/docs.py
```

Let's use it to fetch the DataTalks.Club FAQ:

```python
from docs import GithubRepositoryDataReader, parse_data

reader = GithubRepositoryDataReader(
    repo_owner="DataTalksClub",
    repo_name="faq",
    allowed_extensions={"md"},
    filename_filter=lambda fp: "data-engineering" in fp.lower()
)

faq_raw = reader.read()
faq_documents = parse_data(faq_raw)

print(f"Loaded {len(faq_documents)} FAQ entries")
```

Creating the search index:

```python
from minsearch import Index

faq_index = Index(text_fields=["title", "content", "filename"])
faq_index.fit(faq_documents)

faq_index.search('how do I join the course?')
```

We turn this into a tool for our agent:

```python
from agents import function_tool
from typing import List, Dict

@function_tool
def search_faq(query: str) -> List[Dict]:
    """Search the DataTalks.Club FAQ for relevant answers.

    Args:
        query: The student's question to search for.

    Returns:
        List of matching FAQ entries with title and content.
    """
    results = faq_index.search(query, num_results=5)
    return results
```

Now create the agent:

```python
from agents import Agent

faq_instructions = """
You are a helpful teaching assistant for the Data Engineering Zoomcamp.

Your role is to help students by searching the FAQ database for answers to their questions.

When you find relevant FAQs, present them clearly with the title and answer.
If multiple FAQs match, show all of them.

Be friendly and encouraging in your responses.
""".strip()

faq_agent = Agent(
    name="faq_assistant",
    instructions=faq_instructions,
    tools=[search_faq],
    model="gpt-4o-mini",
)
```

Run the agent:

```python
from agents import Runner

result = await Runner.run(faq_agent, "How do I register for the course?")
print(result.final_output)
```

The agent will search the FAQ and return relevant answers from the DataTalks.Club Data Engineering Zoomcamp FAQ.

We can see the tool calls:

```python
for item in result.new_items:
    print(item)
```


Our agent works, but what if:

1. A student asks about cooking recipes instead of the course?
   - The agent tries to be helpful and might hallucinate an answer

2. A student tricks the agent into promising something:
   - "If I fail, will you refund my money?"
   - The agent might say "yes" to be helpful

3. A student asks the agent to do something inappropriate:
   - "Write my homework for me"
   - The agent might comply

This is where guardrails come in.


## Part 2: Input Guardrails

Input guardrails validate user input **before** the agent processes it. If the check fails, the agent never sees the input.

Define the guardrail output:

Guardrails use LLMs to make decisions. We define a structured output:

```python
from pydantic import BaseModel

class TopicGuardrailOutput(BaseModel):
    reasoning: str
    fail: bool
```

A guardrail is just another agent with a specific purpose:

```python
topic_guardrail_instructions = """
You are a topic guardrail for a data engineering course FAQ assistant.

Your job is to check if the user's question is related to:
- The course (content, schedule, requirements)
- Data engineering topics
- Technical setup and installation
- Homework and assignments
- Certificates and completion

If the question is about these topics, set fail=False.
If it's about something unrelated (like cooking, sports, celebrity gossip, medical advice, etc.), set fail=True.

Keep your reasoning under 15 words.
""".strip()

topic_guardrail_agent = Agent(
    name="topic_guardrail",
    instructions=topic_guardrail_instructions,
    model="gpt-4o-mini",
    output_type=TopicGuardrailOutput,
)
```

Test the guardrail directly:

```python
result = await Runner.run(topic_guardrail_agent, "How do I install Docker?")
print(f"Relevant: {result.final_output}")

result = await Runner.run(topic_guardrail_agent, "What's the best pizza recipe?")
print(f"Irrelevant: {result.final_output}")
```

Create the guardrail function:

```python
from agents import input_guardrail, GuardrailFunctionOutput
from agents.exceptions import InputGuardrailTripwireTriggered

@input_guardrail
async def topic_guardrail(ctx, agent, input):
    """Check if the user's question is about the course."""
    result = await Runner.run(topic_guardrail_agent, input)
    output = result.final_output

    return GuardrailFunctionOutput(
        output_info=output.reasoning,
        tripwire_triggered=output.fail,
    )
```

Attach guardrail to agent:

```python
guarded_faq_agent = Agent(
    name="guarded_faq_assistant",
    instructions=faq_instructions,
    tools=[search_faq],
    model="gpt-4o-mini",
    input_guardrails=[topic_guardrail],
)
```

Run it:

```python
prompt = "how do I eat salami?"
result = await Runner.run(guarded_faq_agent, prompt)
result.final_output
```

Handle guardrail failures:

```python
async def run_with_input_guardrail(agent, user_input):
    """Run an agent with input guardrail handling."""
    try:
        result = await Runner.run(agent, user_input)
        return result.final_output
    except InputGuardrailTripwireTriggered as e:
        return f"[BLOCKED] {e.guardrail_result.output.output_info}"
```

Test the guarded agent:

```python
# Relevant question - works fine
response = await run_with_input_guardrail(
    guarded_faq_agent,
    "How do I submit homework?"
)
print(f"Q: How do I submit homework?\n{response}\n")

# Irrelevant question - blocked
response = await run_with_input_guardrail(
    guarded_faq_agent,
    "What's the best pizza recipe?"
)
print(f"Q: What's the best pizza recipe?\n{response}")
# [BLOCKED] About cooking, not course
```

## Part 3: Output Guardrails

Output guardrails validate the agent's response **before** it reaches the user. They catch things the agent might "hallucinate" or be tricked into saying.

When to use output guardrails:

- Prevent offensive content
- Block inappropriate promises (refunds, legal advice, etc.)
- Stop information leakage
- Enforce tone and style guidelines

Define output guardrail:

```python
class SafetyGuardrailOutput(BaseModel):
    reasoning: str
    fail: bool
```

Create the output guardrail agent:

Note: Output guardrails receive both the user's input AND the agent's response:

```python
safety_guardrail_instructions = """
You are a safety guardrail for a course FAQ assistant.

Check if the agent's response contains any of these issues:
- Promises about deadline extensions
- Legal or medical advice
- Offensive language
- Sharing personal information about students
- Writing homework assignments for students (can guide, but not do the work)
- Sharing exam answers or solutions

If the response is safe, set fail=False.
If it contains any of the issues above, set fail=True.

Keep your reasoning under 15 words.
""".strip()

safety_guardrail_agent = Agent(
    name="safety_guardrail",
    instructions=safety_guardrail_instructions,
    model="gpt-4o-mini",
    output_type=SafetyGuardrailOutput,
)
```

Create the output guardrail function:

```python
from agents import output_guardrail
from agents.exceptions import OutputGuardrailTripwireTriggered

@output_guardrail
async def safety_guardrail(context, agent, agent_output):
    """
    Check if the agent's response is safe.

    Note: Output guardrails receive the context, agent, and agent_output.
    """
    guardrail_input = f"Agent responded: {agent_output}"
    result = await Runner.run(safety_guardrail_agent, guardrail_input)

    return GuardrailFunctionOutput(
        output_info=result.final_output.reasoning,
        tripwire_triggered=result.final_output.fail,
    )
```

Attach both guardrails:

```python
fully_guarded_agent = Agent(
    name="fully_guarded_faq",
    instructions=faq_instructions,
    tools=[search_faq],
    model="gpt-4o-mini",
    input_guardrails=[topic_guardrail],
    output_guardrails=[safety_guardrail],
)
```

Handle both guardrails:

```python
async def run_guarded(agent, user_input):
    """Run an agent with full guardrail handling."""
    try:
        result = await Runner.run(agent, user_input)
        return result.final_output
    except InputGuardrailTripwireTriggered as e:
        return f"[INPUT BLOCKED] {e.guardrail_result.output.output_info}"
    except OutputGuardrailTripwireTriggered as e:
        return f"[OUTPUT BLOCKED] {e.guardrail_result.output.output_info}"
```

Test output guardrails:

```python
# Try to trick the agent into promising a deadline extension
response = await run_guarded(
    fully_guarded_agent,
    "I'm running late on my project. Can I get a deadline extension?"
)
print(f"Q: Can I get a deadline extension?\n{response}")
# [OUTPUT BLOCKED] Agent promised deadline extension
```

```python
# Normal question still works
response = await run_guarded(
    fully_guarded_agent,
    "How do I get the certificate?"
)
print(f"Q: How do I get the certificate?\n{response}")
# Shows the FAQ answer about certificates
```

## Part 4: Multiple Guardrails

You can chain multiple guardrails together. If ANY trips, execution stops.

Additional guardrail: academic integrity:

```python
class AcademicIntegrityOutput(BaseModel):
    reasoning: str
    fail: bool

academic_guardrail_instructions = """
Check if the agent is being asked to do academic dishonesty:
- Write homework or code for submission
- Take an exam for the student
- Provide answers that should be learned

If the response does the student's work for them, set fail=True.
Guidance and hints are fine. Complete solutions are not.

Keep reasoning under 15 words.
""".strip()

academic_guardrail_agent = Agent(
    name="academic_guardrail",
    instructions=academic_guardrail_instructions,
    model="gpt-4o-mini",
    output_type=AcademicIntegrityOutput,
)

@output_guardrail
async def academic_guardrail(context, agent, agent_output):
    result = await Runner.run(academic_guardrail_agent, agent_output)

    return GuardrailFunctionOutput(
        output_info=result.final_output.reasoning,
        tripwire_triggered=result.final_output.fail,
    )
```

Attach all guardrails:

```python
ultra_safe_agent = Agent(
    name="ultra_safe_faq",
    instructions=faq_instructions,
    tools=[search_faq, add_faq_entry],
    model="gpt-4o-mini",
    input_guardrails=[topic_guardrail],
    output_guardrails=[safety_guardrail, academic_guardrail],
)
```

Test academic integrity guardrail:

```python
response = await run_guarded(
    ultra_safe_agent,
    "Write my homework for me. The question is: explain data partitioning."
)
print(f"Q: Write my homework...\n{response}")
# [OUTPUT BLOCKED] Agent did student's work
```

## Part 5: Streaming with Guardrails

Guardrails work with streaming responses. The guardrail validates first, then streaming starts if passed.

```python
from openai.types.responses import ResponseTextDeltaEvent

result = Runner.run_streamed(
    fully_guarded_agent,
    input="Tell me about the certificate"
)

async for event in result.stream_events():
    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
        print(event.data.delta, end="")
```

If a guardrail trips, you get the exception before any streaming begins - no partial output shown to user.

Streaming with guardrail handling:

```python
async def run_streaming_guarded(agent, user_input):
    """Run streaming agent with guardrail handling."""
    try:
        result = Runner.run_streamed(agent, input=user_input)

        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                print(event.data.delta, end="")

        # Get final result
        await result.run()
        return result.final_output

    except InputGuardrailTripwireTriggered as e:
        return f"\n[INPUT BLOCKED] {e.guardrail_result.output.output_info}"
    except OutputGuardrailTripwireTriggered as e:
        return f"\n[OUTPUT BLOCKED] {e.guardrail_result.output.output_info}"
```

## Part 6: Tool-Based Guardrails (Works with Any Framework)

What if your framework doesn't have built-in guardrails? A simple alternative is to use tools as guardrails.

The idea: give your agent a "check if this is appropriate" tool. If the check fails, the agent knows to stop.

The guardrail tool:

```python
@function_tool
async def check_topic(query: str) -> TopicGuardrailOutput:
    """Check if the query is appropriate for this course.

    Args:
        query: The user's question to check.

    Returns:
        TopicGuardrailOutput with fail flag and reasoning.
    """
    # Use the existing guardrail agent to check
    result = topic_guardrail_agent.sync_run(query)
    return result.final_output
```

The agent with guardrail tool:

```python
quarded_faq_instructions = faq_instructions + """

IMPORTANT: Before answering any question, use the check_topic tool first.
- If check_topic returns fail=True, respond with the reasoning and stop.
- If check_topic returns fail=False, proceed to search the FAQ and answer.
"""

faq_agent_with_guardrail = Agent(
    name="faq_assistant",
    instructions=guarded_faq_instructions,
    tools=[check_topic, search_faq],
    model="gpt-4o-mini",
)
```

Test it:

```python
result = await Runner.run(faq_agent_with_guardrail, "How do I submit homework?")
print(result.final_output)

result = await Runner.run(faq_agent_with_guardrail, "How do I bake a cake?")
print(result.final_output)
```

Why this works:

- Every framework supports tools
- The agent self-regulates by checking first
- Simple to understand and debug

Limitations:

- Sequential execution, the user has to wait
- The agent might forget to use the tool
- Less reliable than framework-enforced guardrails
- Agent could be tricked into skipping the check

When to use: Quick prototypes, frameworks without guardrail support, simple use cases.


## Part 7: Async Primer (for DIY Guardrails)

In the case of tools, we first run the check and then proceed to output. Sometimes it takes too much time and we can't let the user wait for too long.

In this case, we need to run checks alongside the agent. This is how it's implemented in the Agents SDK.

Why async matters:

Running guardrails concurrently with the agent means:
- Guardrail checks happen in parallel (no added latency)
- If a guardrail trips, we can cancel the agent immediately (save tokens/money)

Basic async function:

```python
import asyncio

async def mock_agent(input: str) -> str:
    """Simulates an agent that takes time to process."""
    print(f"[Agent] Starting work on: {input}")
    await asyncio.sleep(2)  # Simulate API call
    print(f"[Agent] Done!")
    return f"Response to: {input}"

# Run it
result = await mock_agent("hello")
print(result)
```

Running sequentially vs concurrently:

Sequential (slow - adds latencies):
```python
async def mock_guardrail(input: str) -> str:
    """Simulates an guardrail that takes time to process."""
    print(f"[Guardrail] Starting work on: {input}")
    await asyncio.sleep(1)  # Simulate API call
    print(f"[Guardrail] Good!")
    return f"Response to: {input}"

# Total time: 2 + 1 = 3 seconds
guardrail_result = await mock_guardrail("hello")
agent_result = await mock_agent("hello")
```

Concurrent (fast - no extra latency):
```python
# Total time: max(2, 1) = 2 seconds
results = await asyncio.gather(
    mock_agent("hello"),
    mock_guardrail("hello")
)
```

To be able to cancel a coroutine, we need to turn it into a task. We do it usign `asyncio.create_task()` - it starts async work in the background:

```python
# Start both in background
agent_task = asyncio.create_task(mock_agent("hello"))
guard_task = asyncio.create_task(mock_guardrail("hello"))

# Do other things while they run...

# Wait for both to complete
await asyncio.gather(agent_task, guard_task)

# Get results
print(agent_task.result())
```

Cancelling tasks:

If a guardrail trips, cancel the agent to save resources.

Let's create a failing guardrail:

```python
from dataclasses import dataclass

@dataclass
class GuardrailResult:
    """Result from a guardrail check."""
    reasoning: str
    triggered: bool

class GuardrailException(Exception):
    """Raised when a guardrail trips."""
    def __init__(self, result: GuardrailResult):
        self.result = result
        super().__init__(result.reasoning)
```

And the code:

```python
async def failing_guardrail(input):
    """A guardrail that fails after a short delay."""
    await asyncio.sleep(1.5)
    raise GuardrailException(GuardrailResult(
        reasoning="Content is not appropriate",
        triggered=True
    ))

guard_task = asyncio.create_task(failing_guardrail("hello"))
agent_task = asyncio.create_task(mock_agent("hello"))

try:
    await asyncio.gather(agent_task, guard_task)
except GuardrailException:
    # Guardrail tripped - cancel the agent
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        print("Agent was cancelled - saved tokens!")
```

## Part 8: DIY Guardrails (Any Framework)

What if your framework doesn't have built-in guardrails? Build it yourself - works with Pydantic AI, LangChain, custom agents, etc.


Generic guardrail runner:

```python
async def run_with_guardrails(agent_coro, guardrails):
    """
    Run an agent with guardrails.

    Args:
        agent_coro: The agent coroutine to run
        guardrails: List of async guardrail functions

    Returns:
        The agent's result if all guardrails pass

    Raises:
        GuardrailException: If any guardrail trips
    """
    # Create tasks
    agent_task = asyncio.create_task(agent_coro)
    guardrail_tasks = [asyncio.create_task(g) for g in guardrails]

    try:
        # Wait for agent OR any guardrail to trip
        await asyncio.gather(agent_task, *guardrail_tasks)
        return agent_task.result()

    except GuardrailException as e:
        print(f"[Guardrail tripped] {e.result.reasoning}")

        # Cancel the agent immediately
        agent_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            print("[Agent cancelled - saved tokens]")

        # Cancel remaining guardrails
        for t in guardrail_tasks:
            t.cancel()
        await asyncio.gather(*guardrail_tasks, return_exceptions=True)

        raise
```

how it works:

This function runs an agent concurrently with guardrails and cancels the agent if any guardrail trips.

Inputs:
- `agent_coro`: A coroutine (async function) that runs the agent
- `guardrails`: A list of async guardrail functions that check if execution should stop

Execution flow diagram:

```
                ┌─────────────────────────────────────┐
                │   Create all tasks in parallel      │
                └─────────────────────────────────────┘
                              │
           ┌──────────────────┴──────────────────┐
           ▼                                     ▼
    ┌─────────────┐                     ┌─────────────────┐
    │ agent_task  │                     │ guardrail_tasks │
    │ (running)   │                     │ (all running)   │
    └─────────────┘                     └─────────────────┘
           │                                     │
           └──────────────────┬──────────────────┘
                              ▼
                ┌─────────────────────────────────────┐
                │   asyncio.gather() - wait for any  │
                │   to complete or raise exception    │
                └─────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    ┌─────────────────────┐       ┌──────────────────────┐
    │ GuardrailException  │       │ All complete         │
    │ (guardrail tripped) │       │ (no exceptions)      │
    └─────────────────────┘       └──────────────────────┘
              │                               │
              ▼                               ▼
    Cancel agent &                Return agent result
    remaining guardrails
```

Step-by-step:

1. Create tasks: `asyncio.create_task()` starts all tasks in the background - agent AND guardrails run at the same time

2. Gather: `asyncio.gather()` waits for all tasks; if any raises `GuardrailException`, we jump to the `except` block

3. Success path: If no exception, return `agent_task.result()` - the agent's answer

4. Failure path: If a guardrail trips:
   - Cancel the agent with `agent_task.cancel()` - saves money/tokens
   - Wait for cancellation to complete
   - Cancel remaining guardrails (no point continuing checks)
   - Re-raise the exception

Why this matters:
- No added latency: Guardrails run in parallel with the agent, not before/after
- Early cancellation: As soon as a guardrail trips, the agent stops - no wasted API calls
- Framework agnostic: Works with Pydantic AI, LangChain, custom code, anything async

Example: using the guardrail agent with our FAQ agent:

```python

prompt = 'I just discovered the course, can I still join?' #How can I cook pizza?'
result = await run_with_guardrails(
    Runner.run(faq_agent, prompt),
    [topic_guardrail(prompt),]
)
result.final_output
```

Notice the agent is cancelled immediately when the guardrail trips!

## Summary

Key Takeaways:

1. Guardrails are just agents - They use LLMs to make pass/fail decisions
2. Input guardrails - Block irrelevant or harmful input before the agent sees it
3. Output guardrails - Catch inappropriate responses before showing users
4. Run concurrently - Guardrails add no latency when run in parallel
5. Cancel early - If a guardrail trips, cancel the agent immediately to save tokens
6. Works with any framework - The pattern is simple enough to implement yourself

When to Use Each Type:

| Guardrail Type | Best For | Examples |
|----------------|----------|----------|
| Input | Topic restriction, PII filtering, rate limiting | "Only answer about Python", "Block phone numbers" |
| Output | Safety, policy enforcement, format checking | "No deadline extensions", "Under 200 words", "JSON only" |
| Both | High-stakes applications | Customer support, medical triage, financial advice |

## Further Reading

- [OpenAI Agents SDK - Guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [Python AsyncIO Documentation](https://docs.python.org/3/library/asyncio.html)


## Final words 

That's it! 

If you're interested in learning more about it, check out my course about building AI Agents:

https://maven.com/alexey-grigorev/from-rag-to-agents
