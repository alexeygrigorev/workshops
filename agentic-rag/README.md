# From RAG to Agents: Implementing Agentic Search

This workshop is a stripped-down version of two modules from the
[AI Engineering Buildcamp: From RAG to Agents](https://maven.com/alexey-grigorev/from-rag-to-agents)
course - the *RAG* module and the *Agents* module - distilled into a
single hands-on session. If you want the full version (multiple use
cases, evaluation, monitoring, guardrails, capstone project), take
the course.

It accompanies the tutorial
["From RAG to Agents: Implementing Agentic Search"](https://www.datamakersfest.com/agenda)
at Datamakers Fest.

- Video: [TODO: Add YouTube link]

Retrieval Augmented Generation (RAG) put LLMs in contact with your
data. Agents put them in the driver's seat.

In this workshop, you'll start by building a classic RAG system over
real-world documentation (the [Evidently AI](https://github.com/evidentlyai/docs)
docs) and then progressively evolve it into an agentic search
workflow - one that doesn't just answer questions but actively
reasons, explores, and decides what to read next.

Step by step, you'll:

- Build a classic RAG system over a real documentation dataset
- See the limits of "chunk + retrieve" RAG
- Implement custom tools and wire them into an orchestrated agent
- Build an agentic search flow with two tools:
  - `search` - returns highlighted snippets
  - `get_file` - fetches the full document on demand

After Part 3, we'll show how to swap `toyaikit` for PydanticAI -
the same agent, with a production-grade framework underneath.

If you know Python and have an OpenAI-compatible API key, you're
ready to go.


## Prerequisites

- Python
- OpenAI key (any OpenAI-compatible provider also works)


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

* Create a repository on GitHub, initialize it with `README.md`
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

### Installing required libraries

Initialize the project with `uv` and install the dependencies:

```bash
uv init
uv add jupyter openai minsearch gitsource
```

Start Jupyter:

```bash
uv run jupyter notebook
```


## The use case: Evidently documentation

Throughout the workshop, our knowledge base is the
[Evidently AI documentation](https://github.com/evidentlyai/docs) -
a real, evolving set of Markdown files. This is exactly the dataset
used in the course.

Why documentation? LLMs have a knowledge cutoff, but library
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
from gitsource import GithubRepositoryDataReader, chunk_documents

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
them into smaller chunks. `chunk_documents(size=3000, step=1500)`
makes 3000-character chunks with 1500-character overlap, so we
don't lose information at chunk boundaries.

```python
chunked_docs = chunk_documents(parsed_docs, size=3000, step=1500)
```

### Indexing and searching

We'll use [`minsearch`](https://github.com/alexeygrigorev/minsearch),
a small in-memory search library:

```python
from minsearch import AppendableIndex

index = AppendableIndex(
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
prompt that contains the user's question and the retrieved chunks:

```python
import json

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

def build_prompt(question, search_results):
    context = json.dumps(search_results, indent=2)
    return RAG_PROMPT_TEMPLATE.format(question=question, context=context)
```

Wire it up to OpenAI:

```python
from openai import OpenAI

openai_client = OpenAI()

def llm(user_prompt, model="gpt-4o-mini"):
    messages = [
        {"role": "system", "content": RAG_INSTRUCTIONS},
        {"role": "user", "content": user_prompt}
    ]
    response = openai_client.responses.create(model=model, input=messages)
    return response.output_text
```

Putting it together:

```python
def rag(question):
    search_results = search(question)
    user_prompt = build_prompt(question, search_results)
    return llm(user_prompt)
```

Try it:

```python
print(rag('How do I create a dashboard in Evidently?'))
```

You should get a grounded answer.

### Where classic RAG breaks down

This works for clean, simple questions. But notice what's happening:

- Chunking loses context. If the answer is split across chunks
  1, 3, and 5 - and we retrieve only chunks 2 and 4 - we're stuck.
- One search per question. If the first query fails, we're done.
- The LLM has no say in retrieval. It only sees what came back.
- No way to "open" a document. A snippet isn't always enough.

Now try the same question with a typo and see how it goes:

```python
print(rag('How do I create a dahsbord in Evidently?'))
```

The answer gets noticeably worse - or the system says it can't
find anything. The literal token `dahsbord` doesn't match anything
in the index, and our pipeline has no way to fix that.

To do better, we need to put the LLM *in the driver's seat*. That's
what an agent does.


## Part 2: From RAG to an Agent

### The agentic flow

In an agent, the LLM decides what to do next. We give it tools - in
our case, search functions - and it chooses when and how to use
them.

The flow:

1. The user asks a question.
2. We send the question to the LLM along with the list of available tools.
3. The LLM either:
   - replies directly, OR
   - asks us to call one of the tools with specific arguments.
4. If the LLM asks for a tool call, we execute it and return the result.
5. The LLM looks at the result and either calls another tool or replies.
6. We repeat until the LLM produces a final answer.

What makes this *agentic* is step 3 - the LLM, not us, decides when
and how to search.

Under the hood this is a small request-response loop, often called
the *agentic loop*: send messages to the LLM, run any tool calls it
asks for, append the results, and ask again until it stops asking
for tools. We won't implement it here - the
[AI Engineering Buildcamp](https://maven.com/alexey-grigorev/from-rag-to-agents)
course walks through it step by step, and you can also read the
short, readable implementation in the
[`toyaikit`](https://github.com/alexeygrigorev/toyaikit) source.

### Using a framework: `toyaikit`

Instead of writing the loop ourselves, we'll use
[`toyaikit`](https://github.com/alexeygrigorev/toyaikit) - a tiny
educational framework that wraps the OpenAI Responses API.

> `toyaikit` is great for learning. For production you'll want a
> "real" framework. We'll switch to PydanticAI at the end of the
> workshop.

Install it:

```bash
uv add toyaikit
```

`toyaikit` builds the JSON schema for each tool from the function's
type hints and docstring, so we don't have to write it by hand.
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

The instructions we'll give the agent:

```python
instructions = """
You're a documentation assistant.
Answer the user question using the documentation knowledge base.

Use only facts from the knowledge base when answering.
If you cannot find the answer, inform the user.
""".strip()
```

Wrap the function in a `Tools` collection:

```python
from toyaikit.tools import Tools

agent_tools = Tools()
agent_tools.add_tool(search)

# Inspect the schema toyaikit generated:
agent_tools.get_tools()
```

Wire up the LLM client and a chat interface, then create a runner:

```python
from openai import OpenAI
from toyaikit.llm import OpenAIClient
from toyaikit.chat.interface import IPythonChatInterface
from toyaikit.chat.runners import OpenAIResponsesRunner, DisplayingRunnerCallback

llm_client = OpenAIClient(
    model="gpt-4o-mini",
    client=OpenAI()
)

chat_interface = IPythonChatInterface()
runner_callback = DisplayingRunnerCallback(chat_interface=chat_interface)

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

Or run it as an interactive chat (type `stop` to exit). Capture the
result so the notebook doesn't dump the whole conversation when the
cell finishes:

```python
result = agent.run()
```

We've solved the typo problem - the LLM rewrote `dahsbord` into
`dashboard` before searching. But we still have the chunking
problem from Part 1: if the right answer spans several chunks,
we're guessing. Let's fix that next.


## Part 3: Agentic Search - Going Beyond RAG

We have an agent now. The big unlock is that an agent isn't limited
to one tool - we can give it more, and let it choose between them.
So let's use that.

### The chunking problem

Traditional RAG has a fundamental limitation. We take a big
document, chunk it, and *hope* the retrieved chunks contain what we
need. If we retrieve chunks 2 and 4 out of 5, we're missing
information from 1, 3, and 5.

Now think about how *you* read documentation. You don't get
pre-chunked fragments. You:

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
from minsearch import AppendableIndex

reader = GithubRepositoryDataReader(
    repo_owner="evidentlyai",
    repo_name="docs",
    allowed_extensions={"md", "mdx"},
)
files = reader.read()

parsed_docs = [doc.parse() for doc in files]

index = AppendableIndex(
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

highlighter = Highlighter(
    highlight_fields=["content"],
    max_matches=3,
    snippet_size=50,
    tokenizer=Tokenizer(stemmer="snowball", stop_words=stopwords)
)
```

What this does:

- `highlight_fields` - which fields to extract snippets from
- `max_matches=3` - up to 3 snippets per document (concise)
- `snippet_size=50` - ~50 tokens per snippet (enough context to
  decide relevance, not enough to drown the prompt)
- `stop_words` - skip noise words; `"evidently"` appears everywhere
  in this corpus so we treat it as a stop word
- `stemmer="snowball"` - matches word variations (`use`/`using`)

### File index: opening full documents on demand

We also need a way to look up the full content of a document by
filename. A simple dict does the job:

```python
file_index = {doc["filename"]: doc["content"] for doc in parsed_docs}
```

### The two-tool class

Now define a tools class with the two methods:

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

```python
search_tools = SearchTools(index, highlighter, file_index)
```

### Agent instructions

The instructions guide the agent through a *human-like* research
flow: search broadly, follow up on the most promising files, then
synthesize.

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

This three-iteration pattern mirrors how a human researches: start
broad, dive deeper into the most relevant sources, then consolidate.

### Running the two-tool agent

We already have `toyaikit` wired up. Swap the single `search`
function for our `SearchTools` instance and use the new
instructions:

```python
from toyaikit.tools import Tools
from toyaikit.chat.runners import OpenAIResponsesRunner

agent_tools = Tools()
agent_tools.add_tools(search_tools)

agent = OpenAIResponsesRunner(
    tools=agent_tools,
    developer_prompt=instructions,
    chat_interface=chat_interface,
    llm_client=llm_client,
)
```

Note `add_tools` (plural) - it discovers all public methods on the
`search_tools` instance and registers them as tools, schemas and
all.

Run it on a single question with step-by-step output:

```python
result = agent.loop(
    'how can I create evidently dahsbord? show me the code',
    callback=runner_callback
)
```

Watch what happens:

1. The agent searches with a fixed-up query.
2. It looks at the snippets, picks the most promising filename(s),
   and calls `get_file` to read them in full.
3. It synthesizes the answer from the full content - including code
   examples it pulled out of the actual document.

This is agentic search: no information lost to chunking, no
guessing about which fragment to retrieve. The agent reads what it
needs to read.

You can also run it as an interactive chat (type `stop` to exit).
Capture the result so the notebook doesn't dump the whole
conversation:

```python
result = agent.run()
```


## Part 4: From `toyaikit` to PydanticAI

`toyaikit` is great for learning - it's small enough that you can
read its source in an afternoon. For production, you'll want a
framework that supports more providers, has better tracing, and is
maintained as a library.

[PydanticAI](https://ai.pydantic.dev/) is a good fit. Install it:

```bash
uv add pydantic-ai
```

Here's how to take the same `SearchTools` and run it under
PydanticAI - no other changes.

### Collecting the tools

PydanticAI takes a list of plain Python callables as tools. We can
list them by hand:

```python
tools = [search_tools.search, search_tools.get_file]
```

Or reuse the same helper from `toyaikit` to grab all instance
methods automatically (so when you add a third tool to
`SearchTools`, the agent picks it up):

```python
from toyaikit.tools import get_instance_methods

tools = get_instance_methods(search_tools)
```

### Creating the agent

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

PydanticAI is async, so we `await`. The snippets below assume
you're in a Jupyter notebook (which has a running event loop). If
you're running from a `.py` file, wrap the calls in
`asyncio.run(main())`.

```python
query = 'how do I use evidently to monitor my machine learning models?'

result = await search_agent.run(query)

print(result.output)
```

The agent runs the same agentic search pattern: search → snippets →
`get_file` → synthesize.

### Inspecting the conversation

PydanticAI exposes structured messages, which makes debugging much
nicer than poking at raw API responses:

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

You can also look at usage:

```python
result.usage()
```

### Multi-turn conversations

For a follow-up question, pass the previous messages as
`message_history`:

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
  - `search` returns highlighted snippets to *decide* what to read
  - `get_file` returns the full document to *actually* read it
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
