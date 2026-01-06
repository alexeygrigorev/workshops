# Guardrails for AI Agents

This workshop is about making AI agents safer with guardrails.

## Prerequisites

- Python 3.10+
- OpenAI API key


## What are Guardrails?

Guardrails are safety checks that run **before** (input) or **after** (output) your agent executes.

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

Before adding guardrails, let's build a complete agent with tools. We'll create a **DataTalks.Club FAQ Assistant** that helps students find answers about the Data Engineering Zoomcamp.

### Setup

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

### Loading FAQ Data from GitHub

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

### Creating the Search Index

```python
from minsearch import Index

faq_index = Index(text_fields=["title", "content", "filename"])

faq_index.fit(faq_documents)

faq_index.search('how do I join the course?')
```

### Define Tools

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

### Create the Agent

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

### Run the Agent

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

### The Problem

Our agent works, but what if:

1. A student asks about cooking recipes instead of the course?
   - The agent tries to be helpful and might hallucinate an answer

2. A student tricks the agent into promising something:
   - "If I fail, will you refund my money?"
   - The agent might say "yes" to be helpful

3. A student asks the agent to do something inappropriate:
   - "Write my homework for me"
   - The agent might comply

This is where **guardrails** come in.

## Part 2: Input Guardrails

Input guardrails validate user input **before** the agent processes it. If the check fails, the agent never sees the input.

### Define the Guardrail Output

Guardrails use LLMs to make decisions. We define a structured output:

```python
class TopicGuardrailOutput(BaseModel):
    reasoning: str
    fail: bool
```

### Create the Guardrail Agent

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

### Test the Guardrail Directly

```python
result = await Runner.run(topic_guardrail_agent, "How do I install Docker?")
print(f"Relevant: {result.final_output}")

result = await Runner.run(topic_guardrail_agent, "What's the best pizza recipe?")
print(f"Irrelevant: {result.final_output}")
```

### Create the Guardrail Function

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

### Attach Guardrail to Agent

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

### Handle Guardrail Failures

```python
async def run_with_input_guardrail(agent, user_input):
    """Run an agent with input guardrail handling."""
    try:
        result = await Runner.run(agent, user_input)
        return result.final_output
    except InputGuardrailTripwireTriggered as e:
        return f"[BLOCKED] {e.guardrail_result.output.output_info}"
```

### Test the Guarded Agent

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

### When to Use Output Guardrails

- Prevent offensive content
- Block inappropriate promises (refunds, legal advice, etc.)
- Stop information leakage
- Enforce tone and style guidelines

### Define Output Guardrail

```python
class SafetyGuardrailOutput(BaseModel):
    reasoning: str
    fail: bool
```

### Create the Output Guardrail Agent

Note: Output guardrails receive both the user's input AND the agent's response:

```python
safety_guardrail_instructions = """
You are a safety guardrail for a course FAQ assistant.

Check if the agent's response contains any of these issues:
- Promises of refunds or money-back guarantees
- Legal or medical advice
- Offensive language
- Sharing personal information about students
- Writing homework assignments for students (can guide, but not do the work)

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

### Create the Output Guardrail Function

```python
from agents import output_guardrail
from agents.exceptions import OutputGuardrailTripwireTriggered

@output_guardrail
async def safety_guardrail(ctx, agent, input, output):
    """
    Check if the agent's response is safe.

    Note: Output guardrails receive both the input and the agent's output.
    """
    guardrail_input = f"User asked: {input}\n\nAgent responded: {output}"
    result = await Runner.run(safety_guardrail_agent, guardrail_input)

    return GuardrailFunctionOutput(
        output_info=result.final_output.reasoning,
        tripwire_triggered=result.final_output.fail,
    )
```

### Attach Both Guardrails

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

### Handle Both Guardrails

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

### Test Output Guardrails

```python
# Try to trick the agent into promising a refund
response = await run_guarded(
    fully_guarded_agent,
    "If I don't like the course, will I get a full refund?"
)
print(f"Q: Will I get a refund?\n{response}")
# [OUTPUT BLOCKED] Agent promised refund
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

### Additional Guardrail: Academic Integrity

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
async def academic_guardrail(ctx, agent, input, output):
    guardrail_input = f"User asked: {input}\n\nAgent responded: {output}"
    result = await Runner.run(academic_guardrail_agent, guardrail_input)

    return GuardrailFunctionOutput(
        output_info=result.final_output.reasoning,
        tripwire_triggered=result.final_output.fail,
    )
```

### Attach All Guardrails

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

### Test Academic Integrity Guardrail

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
    ultra_safe_agent,
    input="Tell me about the certificate"
)

async for event in result.stream_events():
    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
        print(event.data.delta, end="")
```

If a guardrail trips, you get the exception before any streaming begins - no partial output shown to user.

### Streaming with Guardrail Handling

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

## Part 6: Async Primer (for DIY Guardrails)

Before building guardrails from scratch, let's quickly cover the async patterns we need.

### Why Async Matters

Running guardrails concurrently with the agent means:
- Guardrail checks happen in parallel (no added latency)
- If a guardrail trips, we can cancel the agent immediately (save tokens/money)

### Basic Async Function

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

### Running Sequentially vs Concurrently

Sequential (slow - adds latencies):
```python
# Total time: 2 + 1 = 3 seconds
agent_result = await mock_agent("hello")
guardrail_result = await mock_guardrail("hello")
```

Concurrent (fast - no extra latency):
```python
# Total time: max(2, 1) = 2 seconds
results = await asyncio.gather(
    mock_agent("hello"),
    mock_guardrail("hello")
)
```

### Creating Tasks

`asyncio.create_task()` starts async work in the background:

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

### Cancelling Tasks

If a guardrail trips, cancel the agent to save resources:

```python
agent_task = asyncio.create_task(mock_agent("hello"))

# Guardrail failed! Cancel the agent immediately
agent_task.cancel()

try:
    await agent_task
except asyncio.CancelledError:
    print("Agent was cancelled - saved tokens!")
```

## Part 7: DIY Guardrails (Any Framework)

What if your framework doesn't have built-in guardrails? Build it yourself - works with Pydantic AI, LangChain, custom agents, etc.

### The Data Structures

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

### Generic Guardrail Runner

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
    guardrail_tasks = [asyncio.create_task(g()) for g in guardrails]

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

### Example: Mock Agent and Guardrails

```python
async def mock_agent(input: str) -> str:
    """Simulates an agent that takes time."""
    print(f"[Agent] Starting work on: {input}")
    for i in range(3):
        await asyncio.sleep(0.5)
        print(f"[Agent] Working... {i+1}/3")
    print(f"[Agent] Done!")
    return f"Response to: {input}"

async def mock_guardrail_pass():
    """A guardrail that always passes."""
    await asyncio.sleep(1)
    print("[Guardrail] Check passed!")
    return None  # No exception = pass

async def mock_guardrail_fail():
    """A guardrail that fails."""
    await asyncio.sleep(1.5)
    print("[Guardrail] Check FAILED!")
    raise GuardrailException(GuardrailResult(
        reasoning="Unsafe content detected",
        triggered=True
    ))
```

### Test: Guardrail Passes

```python
print("=== Test 1: Guardrail passes ===")
try:
    result = await run_with_guardrails(
        mock_agent("Hello world"),
        [mock_guardrail_pass]
    )
    print(f"\nResult: {result}")
except GuardrailException:
    print("\nAgent was blocked.")
```

Output:
```
=== Test 1: Guardrail passes ===
[Agent] Starting work on: Hello world
[Guardrail] Check passed!
[Agent] Working... 1/3
[Agent] Working... 2/3
[Agent] Working... 3/3
[Agent] Done!

Result: Response to: Hello world
```

### Test: Guardrail Fails Mid-Execution

```python
print("\n=== Test 2: Guardrail fails ===")
try:
    result = await run_with_guardrails(
        mock_agent("Something bad"),
        [mock_guardrail_fail]
    )
    print(f"\nResult: {result}")
except GuardrailException as e:
    print(f"\nAgent was blocked: {e.result.reasoning}")
```

Output:
```
=== Test 2: Guardrail fails ===
[Agent] Starting work on: Something bad
[Guardrail] Check FAILED!
[Guardrail tripped] Unsafe content detected
[Agent cancelled - saved tokens]

Agent was blocked: Unsafe content detected
```

Notice the agent was cancelled mid-work - we saved tokens and time!

## Summary

| Approach | Pros | Cons |
|----------|------|------|
| Built-in (Agents SDK) | Easy to use, well-tested, handles edge cases | Framework-specific |
| Manual (asyncio) | Works with any framework, full control | More code, handle edge cases yourself |

### Key Takeaways

1. **Guardrails are just agents** - They use LLMs to make pass/fail decisions
2. **Input guardrails** - Block irrelevant or harmful input before the agent sees it
3. **Output guardrails** - Catch inappropriate responses before showing users
4. **Run concurrently** - Guardrails add no latency when run in parallel
5. **Cancel early** - If a guardrail trips, cancel the agent immediately to save tokens
6. **Works with any framework** - The pattern is simple enough to implement yourself

### When to Use Each Type

| Guardrail Type | Best For | Examples |
|----------------|----------|----------|
| Input | Topic restriction, PII filtering, rate limiting | "Only answer about Python", "Block phone numbers" |
| Output | Safety, policy enforcement, format checking | "No refund promises", "Under 200 words", "JSON only" |
| Both | High-stakes applications | Customer support, medical triage, financial advice |

## Further Reading

- [OpenAI Agents SDK - Guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [Pydantic AI](https://ai.pydantic.dev/)
- [Python AsyncIO Documentation](https://docs.python.org/3/library/asyncio.html)
