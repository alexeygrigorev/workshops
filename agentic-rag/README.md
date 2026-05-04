# From RAG to Agents: Implementing Agentic Search

This workshop is a stripped-down version of two modules from the
[AI Engineering Buildcamp: From RAG to Agents](https://maven.com/alexey-grigorev/from-rag-to-agents)
course. I took the RAG and the Agents modules and distilled it into a single hands-on session.

If you want the full version (multiple use
cases, evaluation, monitoring, guardrails, capstone project), check
the course.

To see my other tutorials, check [AI Shipping Labs](https://aishippinglabs.com/) - a community of AI Builders.

Places where you can find me:

- Alexey On Data substack: https://alexeyondata.substack.com/
- LinkedIn: https://www.linkedin.com/in/agrigorev/
- X: https://x.com/Al_Grigor


## Introduction

Retrieval Augmented Generation (RAG) put LLMs in contact with your
data. Agents put them in the driver's seat.

In this workshop, we will:

- Build a classic RAG system over the [Evidently AI docs](https://github.com/evidentlyai/docs)
- Create an agent that can use search from RAG as a tool
- Turn it into an agentic search agent that explores the knowledge base 

Step by step, you'll:

- Build a classic RAG system over a real documentation dataset
- See the limits of "chunk + retrieve" RAG
- Implement custom tools and wire them into an orchestrated agent
- Build an agentic search flow with two tools:
  - `search` - returns highlighted snippets
  - `get_file` - fetches the full document on demand
- Use an agentic framework to make it manageable

If you know Python and have an OpenAI-compatible API key, you're
ready to go.


## Environment

* For this workshop, all you need is Python with Jupyter.
* I use GitHub Codespaces to run it, but you can use whatever
  environment you like.
* You also need an [OpenAI account](https://openai.com/) (or an
  alternative OpenAI-compatible provider).

### Setting up Github Codespaces

GitHub Codespaces is the recommended environment for this workshop.

But you can use any other environment with Jupyter Notebook.
If you want to do it on your laptop, that's perfectly fine.

* Open this repository in GitHub Codespaces, or copy the
  `agentic-rag` folder into your own repository
* Add the OpenAI key:
    * Go to Settings -> Secrets and Variables (under Security) -> Codespaces
    * Click "New repository secret"
    * Name: `OPENAI_API_KEY`, Secret: your key
    * Click "Add secret"
* Create a codespace
    * Click "Code"
    * Select the "Codespaces" tab
    * "Create codespace on main"

In case you use it on your laptop, set the API key before you start
Jupyter:

```bash
export OPENAI_API_KEY='YOUR_KEY'
```

### Workshop files

This folder contains the code we'll write during the workshop:

- `notebook.py` - the follow-along version, split into notebook
  cells with `# %%`. Copy each cell into Jupyter as we go, or open
  it directly in VS Code/Jupyter.
- `search_tools.py` - the same search-tool logic extracted into a
  small module for reference after the workshop.
- `test_search_tools.py` - lightweight tests for the `SearchTools`
  class.

During the live workshop, we'll write the code ourselves. The files
are here so the workshop is still useful stand-alone after the
session.

### Installing required libraries

Install the dependencies:

```bash
cd agentic-rag
uv sync
```

Start Jupyter:

```bash
uv run jupyter notebook
```

Open Jupyter, create a notebook, and copy the cells from
`notebook.py` as we go. Check that the OpenAI client works:

```python
from openai import OpenAI
openai_client = OpenAI()
```

For Groq or other OpenAI-compatible proviers:

```python
from openai import OpenAI
import os

openai_client = OpenAI(
    api_key=os.getenv('GROQ_API_KEY'),
    base_url='https://api.groq.com/openai/v1'
)
```

If you see an error, make sure you set the key correctly.


## The use case: Evidently documentation

Throughout the workshop, our knowledge base is the
[Evidently AI documentation](https://github.com/evidentlyai/docs) -
a real, evolving set of Markdown files. 

LLMs have a knowledge cutoff, but library
documentation keeps changing. Plugging fresh docs into an LLM is
one of the most common and useful applications of RAG.


## Part 1: Building a Classic RAG System

Let's first build a "classic" RAG system. Once we have it working,
we'll see exactly where its limitations are - and that will motivate
the move to an agent.

### What is RAG?

RAG (Retrieval-Augmented Generation) connects an LLM to your data
so it can answer questions grounded in your documents instead of
relying purely on what it memorized during training.

A RAG system has three components:

1. Search - Retrieve documents relevant to the user's question
2. Prompt building - Stitch the retrieved documents into a prompt
3. LLM - Generate an answer based on the prompt

In code:

```python
def rag(question):
    search_results = search(question)
    user_prompt = build_prompt(question, search_results)
    return llm(user_prompt)
```

That's it. The "magic" of RAG is that the LLM only sees the
documents we hand it - so its answers are grounded in our data.

### Loading the documentation

We use `gitsource` to fetch and parse Markdown files from a GitHub
repo:

```python
from gitsource import GithubRepositoryDataReader

reader = GithubRepositoryDataReader(
    repo_owner="evidentlyai",
    repo_name="docs",
    allowed_extensions={"md", "mdx"},
)
files = reader.read()

parsed_docs = [doc.parse() for doc in files]
```

Each parsed doc has a few useful fields: `title`, `description`,
`content`, and `filename`.

### Chunking

The documents are too long to put into a prompt as-is. So we split
them into smaller chunks.

```python
from gitsource import chunk_documents

chunked_docs = chunk_documents(parsed_docs, size=3000, step=1500)
```

Here `chunk_documents(size=3000, step=1500)`
makes 3000-character chunks with 1500-character overlap, so we
don't lose information at chunk boundaries.

### Indexing and searching

We'll use [`minsearch`](https://github.com/alexeygrigorev/minsearch),
a small in-memory search library:

```python
from minsearch import Index

index = Index(
    text_fields=["title", "description", "content"],
    keyword_fields=["filename"]
)

index.fit(chunked_docs)
```

`text_fields` are tokenized and ranked with TF-IDF. `keyword_fields`
are used as exact-match filters.

Wrap it in a `search` function:

```python
def search(query):
    return index.search(query=query, num_results=5)
```

### Building the prompt and calling the LLM

The LLM doesn't see the docs unless we pass them in. So we build a
prompt (instructions + template). 

The instructions describe how our system should behave and the template will contain the user's question and the retrieved chunks:

```python
RAG_INSTRUCTIONS = """
You're a documentation assistant. Answer the QUESTION based on the CONTEXT from our documentation.

Use only facts from the CONTEXT when answering.
If the answer isn't in the CONTEXT, say so.
""".strip()

RAG_PROMPT_TEMPLATE = """
<QUESTION>
{question}
</QUESTION>

<CONTEXT>
{context}
</CONTEXT>
""".strip()
```

Let's use it:

```python
import json

def build_prompt(question, search_results):
    context = json.dumps(search_results, indent=2)
    return RAG_PROMPT_TEMPLATE.format(question=question, context=context)
```

Now let's create the `llm` funciton - the last line in our `rag` function:

```python
def llm(instructions, user_prompt, model="gpt-4o-mini"):
    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": user_prompt}
    ]
    response = openai_client.responses.create(model=model, input=messages)
    return response.output_text
```

Now it actually works:

```python
def rag(question):
    search_results = search(question)
    user_prompt = build_prompt(question, search_results)
    return llm(RAG_INSTRUCTIONS, user_prompt)
```

Try it:

```python
rag('How do I create a dashboard in Evidently?')
```

You should get an answer grounded to our knowledge base.

### Where classic RAG breaks down

This works for clean, simple questions. But notice what's happening:

- Chunking loses context. If the answer is split across chunks
  1, 3, and 5 - and we retrieve only chunks 2 and 4 - we're stuck.
- One search per question. If the first query fails, we're done.
- The LLM has no say in retrieval. It only sees what came back.
- No way to "open" a document. A snippet isn't always enough.

Now try the same question with a typo and see how it goes:

```python
rag('How do I create a dahsbord in Evidently?')
```

The answer gets noticeably worse - or the system says it can't
find anything. The literal token `dahsbord` doesn't match anything
in the index, and our pipeline has no way to fix that.

To do better, we need to put the LLM in the driver's seat and let it decide
what to query. That's what an agent does.


## Part 2: From RAG to an Agent

### The agentic flow

In an agent, the LLM decides what to do next. We give it tools - in
our case, search functions - and it chooses when and how to use
them.

The flow:

1. The user asks a question.
2. We send the question to the LLM along with the list of available tools.
3. The LLM either:
   - replies directly (if we want - we configure it via instructions), OR
   - asks us to call one of the tools with specific arguments.
4. If the LLM asks for a tool call, we execute it and return the result.
5. The LLM looks at the result and either calls another tool or replies.
6. We repeat until the LLM produces a final answer.

What makes this agentic is step 3 - the LLM, not us, decides when
and how to search.

Under the hood this is a small request-response loop, often called
the agentic loop: send messages to the LLM, run any tool calls it
asks for, append the results, and ask again until it stops asking
for tools.

### Using a framework: `toyaikit`

We won't implement the agentic loop ourselves. I show it in the course
and you can find a lot of information about it online too.

I recommend implementing it yourself, but for the sake of time we will skip it 
and delegate this part to a framework. 

First, we'll use [`toyaikit`](https://github.com/alexeygrigorev/toyaikit) - a library that I implemented for teaching and workshops.
You can see how the agentic loop is implemented there.

> `toyaikit` is great for learning. For production you'll want a
> "real" framework. We'll switch to PydanticAI at the end of the
> workshop.

Install it:

```bash
uv add toyaikit
```

Like any other framework, `toyaikit` requires our tools to have 
type hints and docstring. This information is then passed 
to an LLM, so it knows when to use these functions.

Let's annotate `search` properly:

```python
from typing import Any, Dict, List

def search(query: str) -> List[Dict[str, Any]]:
    """
    Search the documentation database.

    Args:
        query (str): The search query to look up in the index.

    Returns:
        List of matching documents.
    """
    return index.search(query=query, num_results=5)
```

Wrap the function in a `Tools` collection:

```python
from toyaikit.tools import Tools

agent_tools = Tools()
agent_tools.add_tool(search)

# Inspect the schema toyaikit generated:
agent_tools.get_tools()
```

Let's start with imports for the agent:

```python
from toyaikit.llm import OpenAIClient
from toyaikit.chat.interface import IPythonChatInterface
from toyaikit.chat.runners import OpenAIResponsesRunner, DisplayingRunnerCallback
```

Now initialize the helpers:

```python
llm_client = OpenAIClient(
    model="gpt-4o-mini",
    client=openai_client,
)

chat_interface = IPythonChatInterface()
runner_callback = DisplayingRunnerCallback(chat_interface=chat_interface)
```

And create the agent:


```python
instructions = """
You're a documentation assistant.
Answer the user question using the documentation knowledge base.

Use only facts from the knowledge base when answering.
If you cannot find the answer, inform the user.
""".strip()

agent = OpenAIResponsesRunner(
    tools=agent_tools,
    developer_prompt=instructions,
    chat_interface=chat_interface,
    llm_client=llm_client,
)
```

Run the agent on a single question. Notice the typo - we'll see
that the agent quietly fixes it before searching:

```python
result = agent.loop(
    'How do I create a dahsbord in Evidently?',
    callback=runner_callback
)

print(result.last_message)
```

We can also run it as an interactive chat (type `stop` to exit):

```python
result = agent.run()
```

We've solved the typo problem - the LLM rewrote `dahsbord` into
`dashboard` before searching.

But we still have the chunking
problem from Part 1: if the right answer spans several chunks,
we're guessing. Let's fix that next.


## Part 3: Agentic Search - Going Beyond RAG

We have an agent now - an agent with one tool. But we can give it access to more tools, so it can choose between them.

### The chunking problem

Traditional RAG has a fundamental limitation. We take a big
document, chunk it, and hope the retrieved chunks contain what we
need. If we retrieve chunks 2 and 4 out of 5, we're missing
information from 1, 3, and 5.

Now think about how you read documentation. You don't get
pre-chunked fragments.

You:

1. Search for something
2. Look at the snippets and titles
3. Open the most relevant document
4. Read through it to find what you need

With agents, we can replicate that. Instead of chunking upfront,
we'll replace the single `search` tool with two tools:

1. `search` - returns short, highlighted snippets so the agent
   can decide which document is worth opening
2. `get_file` - returns the full document when the agent wants
   to read it end-to-end

The agent stays in charge: it searches, looks at the snippets,
picks the most promising filename, opens the file, and synthesizes
the answer.

### Re-indexing without chunking

We rebuild `index` over full documents this time, not chunks. This
replaces the chunked index from Part 1:

```python
from gitsource import GithubRepositoryDataReader
from minsearch import Index

reader = GithubRepositoryDataReader(
    repo_owner="evidentlyai",
    repo_name="docs",
    allowed_extensions={"md", "mdx"},
)
files = reader.read()

parsed_docs = [doc.parse() for doc in files]

index = Index(
    text_fields=["title", "description", "content"],
    keyword_fields=["filename"]
)
index.fit(parsed_docs)
```

### Highlighter: showing snippets, not full documents

When we search, returning the full document is too much context.
We want concise snippets that help the agent decide which documents
to open.

`minsearch` has a highlighter (the same idea as Lucene/Elasticsearch
highlighting):

```python
from minsearch import Highlighter, Tokenizer
from minsearch.tokenizer import DEFAULT_ENGLISH_STOP_WORDS

stopwords = DEFAULT_ENGLISH_STOP_WORDS | {"evidently"}
tokenizer = Tokenizer(stemmer="snowball", stop_words=stopwords)

highlighter = Highlighter(
    highlight_fields=["content"],
    max_matches=3,
    snippet_size=50,
    tokenizer=tokenizer,
)
```

Let's try it. Run a search, then pass the results through the
highlighter:

```python
query = "how to create a dashboard"
search_results = index.search(query=query, num_results=5)

snippets = highlighter.highlight(query, search_results)
snippets[0]
```

Each result keeps the same fields, but `content` is replaced with a
short list of snippets around the matched terms - exactly what we
want to feed back to the agent.

What the highlighter parameters do:

- `highlight_fields` - which fields to extract snippets from
- `max_matches=3` - up to 3 snippets per document (concise)
- `snippet_size=50` - ~50 tokens per snippet (enough context to
  decide relevance, not enough to drown the prompt)
- `stop_words` - skip noise words; `"evidently"` appears everywhere
  in this corpus so we treat it as a stop word
- `stemmer="snowball"` - matches word variations (`use`/`using`)

### File index: opening full documents on demand

We also need a way to look up the full content of a document by
filename. We need it for the second function. 

A simple dict is enough:

```python
file_index = {doc["filename"]: doc["content"] for doc in parsed_docs}
```

Look up a file by name to see what we get:

```python
filename = next(iter(file_index))
print(filename)
print(file_index[filename][:500])
```

### The two-tool class

Why a class instead of two plain functions? Both `search` and
`get_file` need access to the same shared state - the `index`, the
`highlighter`, the `file_index`. A class lets us hold that state in
one place instead of relying on globals, and adding more tools
later (a re-ranker, a "list files" helper) is a one-line change.

I also like to keep tools in a separate Python file (e.g.
`search_tools.py`) and import them from the notebook. Two reasons:

- It separates *tool logic* from *agent logic*. The notebook stays
  focused on wiring up the agent.
- The tools become testable on their own - you can write
  unit tests for `search` and `get_file` without spinning up an LLM.

For the workshop we'll keep everything in the notebook for speed,
but in a real project I'd put this in its own module.

```python
from typing import Any, Dict, List

class SearchTools:
    """
    Provides search and file retrieval utilities over an indexed data store.
    """
    def __init__(self, index, highlighter, file_index: Dict[str, str]):
        self.index = index
        self.highlighter = highlighter
        self.file_index = file_index

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search the index and return highlighted snippets.

        Args:
            query (str): The search query to look up in the index.

        Returns:
            List of search results with highlighted snippets.
        """
        search_results = self.index.search(query=query, num_results=5)
        return self.highlighter.highlight(query, search_results)

    def get_file(self, filename: str) -> str:
        """
        Retrieve a file's full contents by filename.

        Args:
            filename (str): The filename of the file to retrieve.

        Returns:
            The full file contents, or an error message if not found.
        """
        if filename in self.file_index:
            return self.file_index[filename]
        return f"file {filename} does not exist"
```

The `search` method returns highlighted snippets. The `get_file`
method returns the full document.

Let's initialize it:

```python
search_tools = SearchTools(index, highlighter, file_index)
```

Smoke-test both methods:

```python
snippets = search_tools.search("create a dashboard")
snippets[0]
```

```python
filename = snippets[0]["filename"]
search_tools.get_file(filename)[:500]
```

The first call returns a list of search results with highlighted
snippets (decision-time data). The second call returns the full
contents of the file we picked.

### Wiring up the agent

We already have `toyaikit` set up. Swap the single `search`
function for our `SearchTools` instance:

```python
from toyaikit.tools import Tools
from toyaikit.chat.runners import OpenAIResponsesRunner

agent_tools = Tools()
agent_tools.add_tools(search_tools)
```

Note `add_tools` (plural) - it discovers all public methods on the
`search_tools` instance and registers them as tools, schemas and
all.

Now create the agent. We'll start with the same minimal instructions
we used in Part 2:

```python
instructions = """
You're a documentation assistant.
Answer the user question using only the documentation knowledge base.
""".strip()

agent = OpenAIResponsesRunner(
    tools=agent_tools,
    developer_prompt=instructions,
    chat_interface=chat_interface,
    llm_client=llm_client,
)
```

### Running it: simple prompt

Run it on a single question with step-by-step output:

```python
result = agent.loop(
    'how can I create evidently dahsbord? show me the code',
    callback=runner_callback
)
```

Watch what happens. With a minimal prompt, the agent often does the
bare minimum: one `search`, then it answers from the snippets and
calls it a day. Sometimes that's enough. Often it isn't - the
snippets don't contain the code, or they miss the part of the doc
that actually answers the question.

### Tightening the prompt

We can push the agent toward more thorough behavior by being
explicit about the stages we want:

```python
instructions = """
You're a documentation assistant.

Answer the user question using only the documentation knowledge base.

Make 3 iterations:

1) First iteration:
   - Perform one search using the search tool to identify potentially relevant documents.
   - Explain (in 2-3 sentences) why this search query is appropriate for the user question.

2) Second iteration:
   - Analyze the results from the previous search.
   - Based on the filenames or documents returned, perform:
       - Up to 2 additional search queries to refine or expand coverage, and
       - One or more get_file calls to retrieve the full content of the most relevant documents.
   - For each search or get_file call, explain (in 2-3 sentences) why this action is necessary and how it helps answer the question.

3) Third iteration:
   - Analyze the retrieved document contents from get_file.
   - Synthesize the information into a final answer to the user.

IMPORTANT:
- At every step, explicitly explain your reasoning for each search query or file retrieval.
- Use only facts found in the documentation knowledge base.
- Do not introduce outside knowledge or assumptions.
- If the answer cannot be found in the retrieved documents, clearly inform the user.

Additional notes:
- The knowledge base is entirely about Evidently, so you do not need to include the word "evidently" in search queries.
- Prefer retrieving and analyzing full documents (via get_file) before producing the final answer.
""".strip()
```

Why split it into three explicit stages? Without staging, the agent
tends to stop early - one search, one answer. Naming the stages
forces it to:

- Start broad with a single search to see what exists.
- Use the snippets to decide what to read in full and what to
  search again for - this is the part where we actually use both
  tools.
- Only then commit to an answer, grounded in the full documents
  it pulled.

Asking for a 2-3 sentence explanation at each step is also useful
in practice - it makes the agent's reasoning visible, so when
something goes wrong you can see *why*.

Recreate the agent with the new instructions and run the same
question:

```python
agent = OpenAIResponsesRunner(
    tools=agent_tools,
    developer_prompt=instructions,
    chat_interface=chat_interface,
    llm_client=llm_client,
)

result = agent.loop(
    'how can I create evidently dahsbord? show me the code',
    callback=runner_callback
)
```

This time you should see:

1. The agent searches with a fixed-up query.
2. It looks at the snippets, picks the most promising filename(s),
   and calls `get_file` to read them in full.
3. It synthesizes the answer from the full content - including code
   examples it pulled out of the actual document.

This is agentic search. Retrieval isn't fixed at index time - the
agent decides what to open based on what it sees in the snippets,
and reads only the documents it actually needs.

You can also run it as an interactive chat (type `stop` to exit).
Capture the result so the notebook doesn't dump the whole
conversation:

```python
result = agent.run()
```


## Part 4: From `toyaikit` to PydanticAI

`toyaikit` is great for learning - it's interactive, plus it's small enough that you can read its source in a few hours. 

But for production, you'll want a
framework that supports more providers, has better tracing, and is
maintained as a library.

My favorite agentic framework is [PydanticAI](https://ai.pydantic.dev/). I'll use it. Install it:

```bash
uv add pydantic-ai
```

### Collecting the tools

Instead of the `Tools` class, we need to prepare a list with functions. These functions, of course, need to have doc strings and type hints.

Since our project is small, we can simply list them:

```python
tools = [search_tools.search, search_tools.get_file]
```

### Creating the agent

Now we're ready to create an agent:

```python
from pydantic_ai import Agent

search_agent = Agent(
    name='search',
    model='openai:gpt-4o-mini',
    instructions=instructions,
    tools=tools,
)
```

The pieces map one-to-one to what we had with `toyaikit`:

- `model` - the LLM (`'openai:gpt-4o-mini'`, but PydanticAI also
  speaks Anthropic, Gemini, Groq, ...).
- `instructions` - the same three-iteration prompt we already wrote.
- `tools` - the same two methods.

### Running the agent

PydanticAI is async, so we need to use `await`.

Let's run it: 
```python
query = 'how do I use evidently to monitor my machine learning models?'

result = await search_agent.run(query)
print(result.output)
```

I assume you're running it in a Jupyter notebook. If
you're running from a `.py` file, wrap the calls in
`asyncio.run(...)`.


The agent runs the same agentic search pattern: search → snippets →
`get_file` → synthesize.

### Inspecting the conversation

PydanticAI exposes structured messages. This is how we can see what's inside:

```python
def print_messages(messages):
    for m in messages:
        print(m.kind)
        for p in m.parts:
            part_kind = p.part_kind
            if part_kind == 'user-prompt':
                print('USER:', p.content)
            if part_kind == 'tool-call':
                print('TOOL CALL:', p.tool_name, p.args)
            if part_kind == 'tool-return':
                print('TOOL RETURN:', p.tool_name)
            if part_kind == 'text':
                print(p.content)
        print()

print_messages(result.all_messages())
```

Each message has a `kind` (request or response) and `parts`. Parts
can be `user-prompt`, `tool-call`, `tool-return`, or `text`.

You can also look at usage to see how much it cost us:

```python
result.usage()
```

### Multi-turn conversations

If we want to have a conversation with the agent, we need to be able to send a follow-up question.

For that, pass the previous messages as `message_history`:

```python
messages = result.all_messages()

result2 = await search_agent.run(
    'show me the code',
    message_history=messages
)

print(result2.output)
print_messages(result2.new_messages())
```

### A simple Q&A loop

Putting it together:

```python
from pydantic_ai.usage import RunUsage

messages = []
usage = RunUsage()

while True:
    user_prompt = input('You: ')
    if user_prompt.lower().strip() == 'stop':
        break

    result = await search_agent.run(user_prompt, message_history=messages)
    usage = usage + result.usage()

    print_messages(result.new_messages())
    messages.extend(result.new_messages())

print(usage)
```

Same agent, same tools, same behavior - now on a framework you can
ship.


## Summary

In this workshop, we:

- Built a classic RAG pipeline over real documentation
- Saw exactly where classic RAG runs out of road - chunking loses
  context, typos break retrieval, and the LLM can't follow up
- Turned `search` into a tool and ran the agentic loop with
  `toyaikit`
- Went beyond RAG with the two-tool agentic search pattern:
  - `search` returns highlighted snippets to decide what to read
  - `get_file` returns the full document to actually read it
- Migrated the same agent to PydanticAI for production use

You now have a working agentic search system and a clear mental
model for where LLM applications are heading: from "retrieve once,
generate once" toward LLMs that reason, choose tools, and iterate
until they get the answer right.


## Next Steps

- Add more tools: a re-ranker, a "list files in folder" tool, a
  "fetch GitHub issue" tool.
- Try a different search backend (Elasticsearch, Qdrant) behind
  the same `search` interface.
- Evaluate the agent (Hit Rate, MRR, LLM-as-judge) and iterate on
  the instructions.
- Put guardrails around the agent (input/output checks, tool-call
  limits) before exposing it to real users.

For all of the above with structured exercises, code, and
deployment, see the full
[AI Engineering Buildcamp: From RAG to Agents](https://maven.com/alexey-grigorev/from-rag-to-agents)
course.
