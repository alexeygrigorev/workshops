# Agents and MCP

This workshop is a part of the
[AI Bootcamp: From RAG to Agents](https://maven.com/alexey-grigorev/from-rag-to-agents) course.

- Video: https://www.youtube.com/watch?v=W2EDdZplLcU

Previously, in the ["Create Your Own Coding Agent" workshop](../coding-agent/)
we created a coding agent that could create a Django application
from a single prompt.

In this workshop, we will deep dive into agents.

We will

- look into function calling - the thing that distinguishes agents from Q&A bots
- use OpenAI Agents SDK and PydanticAI 
- wrap it into an MCP server 
- add this server to our Agent
- use the server in Cursor 


## Prerequisites

- Python
- OpenAI key
- Anthropic key (optional)
- Github (optional)



## Introduction

We will make a system that answers questions from students 
of a course.

We have some FAQ documents like [that](https://docs.google.com/document/d/19bnYs80DwuUimHM65UV3sylsCn2j1vziPOwzBwQrebw/edit?tab=t.0).
We [parsed](https://github.com/alexeygrigorev/llm-rag-workshop/blob/main/notebooks/parse-faq.ipynb) them into [JSON](https://github.com/alexeygrigorev/llm-rag-workshop/blob/main/notebooks/documents.json).

We will use this JSON document to build the chatbot that 
answers our questions.

In the course we will have two more use cases:

- Deep research on the podcast transcripts database
- RAG on a framework documentation


## Agents

### Agentic flow

Agentic conversational systems can use tools.
This is the main difference between them and the "usual" ones that
simply use an LLM to answer your question.

Suppose we have a knowledge database with our FAQ and a `search` 
function that can look up things there.

The agentic flow is following:

- User types in their question
- The system sends the question to the LLM provider
- The LLM makes a decision whether to invoke the `search` function or give the answer directly
- If the decision is to give the answer directly, we output it to the user and wait for follow-up input
- If the decision is to invoke the function, we invoke it, and send back the results to the LLM
- LLM analyzes the results and gives the final output. We display the output and wait for follow-up input

What makes this system "agentic" is its ability to decide when to use 
tools - the `search` function.

Let's implement it

### FAQ Search

First we get the FAQ data:

```python
import requests 

docs_url = 'https://github.com/alexeygrigorev/llm-rag-workshop/raw/main/notebooks/documents.json'
docs_response = requests.get(docs_url)
documents_raw = docs_response.json()

documents = []

for course in documents_raw:
    course_name = course['course']

    for doc in course['documents']:
        doc['course'] = course_name
        documents.append(doc)
```

We use `minsearch` for in-memory search in these documents.
You can install it with `pip install minsearch`.

Let's use it:

```python
from minsearch import AppendableIndex

index = AppendableIndex(
    text_fields=["question", "text", "section"],
    keyword_fields=["course"]
)

index.fit(documents)
```

And implement our `search` function:

```python
def search(query):
    boost = {'question': 3.0, 'section': 0.5}

    results = index.search(
        query=query,
        filter_dict={'course': 'data-engineering-zoomcamp'},
        boost_dict=boost,
        num_results=5,
    )

    return results
```

LLMs are language-agnostic, so we need to provide it with a description
of our functions. In our case, it looks like that:

```python
search_tool = {
    "type": "function",
    "name": "search",
    "description": "Search the FAQ database",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query text to look up in the course FAQ."
            }
        },
        "required": ["query"],
        "additionalProperties": False
    }
}
```

Now let's use it with OpenAI:


```python
from openai import OpenAI
openai_client = OpenAI()

developer_prompt = """
You're a course teaching assistant. 
You're given a question from a course student and your task is to answer it.
""".strip()

tools = [search_tool]

question = 'I just discovered the course. Can I still join it?'

chat_messages = [
    {"role": "developer", "content": developer_prompt},
    {"role": "user", "content": question}
]

response = openai_client.responses.create(
    model='gpt-4o-mini',
    input=chat_messages,
    tools=tools
)
```

A few things:

- `developer_prompt` is the instructions for our agent - we explain it what its task is 
- `tools` - tools available for our agent 
- `chat_messages` - our conversation history

Compare the results with and without tools.

After invoking, we can see what it returns:

```python
response.output
```

Now if we see that there's a decision to invoke a function,
we need to do it, and put everything back to `chat_messages`:


```python
import json

chat_messages.extend(response.output)

# if we have multiple function calls, do it for each
call = response.output[0]

results = search("join course")
result_json = json.dumps(results, indent=2)

chat_messages.append({
    "type": "function_call_output",
    "call_id": call.call_id,
    "output": result_json,
})
```

And then invoke the LLM again:

```python
response = openai_client.responses.create(
    model='gpt-4o-mini',
    input=chat_messages,
    tools=tools
)

response.output_text
```

LLMs are stateless: the next invocation doesn't know anything 
about the previous. That's why we need to include everything 
in `chat_messages`. Otherwise the LLM will not know about the
initial question and its decision to invoke the `search` function.

This is how we implement _memory_ for our agent. 

We can also experiment with the system prompt:

```python
developer_prompt = """
You're a course teaching assistant. 
You're given a question from a course student and your task is to answer it.

If you want to look up the answer, explain why before making the call
""".strip()
```

Or this:

```python
developer_prompt = """
You're a course teaching assistant. 
You're given a question from a course student and your task is to answer it.

If you want to look up the answer, explain why before making the call. Use as many 
keywords from the user question as possible when making first requests.

Make multiple searches. Try to expand your search by using new keywords based on the results you
get from the search.

At the end, make a clarifying question based on what you presented and ask if there are 
other areas that the user wants to explore.
""".strip()
```

The last one makes multiple invocations of `search`, so we need to hanlde
them.

Let's make this code a little more generic. First, define the 
`make_call` function:

```python
def make_call(call):
    args = json.loads(call.arguments)
    f_name = call.name
    f = globals()[f_name]
    result = f(**args)
    result_json = json.dumps(result, indent=2)
    return {
        "type": "function_call_output",
        "call_id": call.call_id,
        "output": result_json,
    }
```

Now invoke it again:

```python
response = openai_client.responses.create(
    model='gpt-4o-mini',
    input=chat_messages,
    tools=tools
)
```

And iterate over the responses:

```python
for entry in response.output:
    chat_messages.append(entry)

    if entry.type == 'message':
        print('assistant')
        print(entry.content[0].text)

    if entry.type == 'function_call':
        print('function call:', entry.name, entry.arguments)
        result = make_call(entry)
        print('results:', result['output'][:50], '...')
        chat_messages.append(result)

    print()
```

After that we want to make the API call again. And again - until
there are no more function calls. 

So we need to put our code in a while loop, and run it until 
we need the next input from the user. 

Then we repeat it.

We can implement it ourselves (try doing it after this workshop -
it's very helpful for understading how it works), but we can 
also use `toyaikit` - a library that simplifies the interactions
with the API:

```bash
pip install toyaikit
```

Note: toyaikit is not a library for using in production. It's good
for education, but for real-life projects, you should use 
other frameworks (we cover some of them, like Agents SDK and PydanticAI)

So let's use it:

```python
from toyaikit.llm import OpenAIClient
from toyaikit.tools import Tools
from toyaikit.chat import IPythonChatInterface
from toyaikit.chat.runners import OpenAIResponsesRunner
from toyaikit.chat.runners import DisplayingRunnerCallback

agent_tools = Tools()
agent_tools.add_tool(search, search_tool)

chat_interface = IPythonChatInterface()

runner = OpenAIResponsesRunner(
    tools=agent_tools,
    developer_prompt=developer_prompt,
    chat_interface=chat_interface,
    llm_client=OpenAIClient()
)

messages = runner.loop(prompt='how do I install kafka')

# with displaying
callback = DisplayingRunnerCallback(chat_interface)
messages = runner.loop(prompt='how do I install kafka', callback=callback)
```

This is one loop of the QA flow. 
If we have a follow-up input, we invoke it again:

```python
new_messages = runner.loop(
    prompt='I want to run it in python',
    previous_messages=messages,
    callback=callback
)
```


We can also run it in the "chat" more:

```python
messages = runner.run();
```

With toyaikit (and all other agentic frameworks) you don't need
to specify the function schema, the framework can infer it 
from the docstrings and typehints.

Let's ask ChatGPT to add them:

```python
from typing import List, Dict, Any

def search(query: str) -> List[Dict[str, Any]]:
    """
    Search the FAQ database for entries matching the given query.

    Args:
        query (str): Search query text to look up in the course FAQ.

    Returns:
        List[Dict[str, Any]]: A list of search result entries, each containing relevant metadata.
    """
    boost = {'question': 3.0, 'section': 0.5}

    results = index.search(
        query=query,
        filter_dict={'course': 'data-engineering-zoomcamp'},
        boost_dict=boost,
        num_results=5,
        output_ids=True
    )

    return results
```

And use it with the `Tools` class:

```python
agent_tools = Tools()
agent_tools.add_tool(search)
agent_tools.get_tools()
```

We can add another function easily:

```python
def add_entry(question: str, answer: str) -> None:
    """
    Add a new entry to the FAQ database.

    Args:
        question (str): The question to be added to the FAQ database.
        answer (str): The corresponding answer to the question.
    """
    doc = {
        'question': question,
        'text': answer,
        'section': 'user added',
        'course': 'data-engineering-zoomcamp'
    }
    index.append(doc)
```

Add it to tools:

```python
agent_tools.add_tool(add_entry)
```


Let's run it:

```python
runner = OpenAIResponsesRunner(
    tools=agent_tools,
    developer_prompt=developer_prompt,
    chat_interface=chat_interface,
    llm_client=OpenAIClient()
)
runner.run();
```



Ask it:

- How do I do well in module 1?
- Add this back to FAQ

We can organize all the tools in one class. This is better OOP design:
instead of a global dependency on `index`, we put it inside the class:


```python
class SearchTools:

    def __init__(self, index):
        self.index = index

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search the FAQ database for entries matching the given query.
    
        Args:
            query (str): Search query text to look up in the course FAQ.
    
        Returns:
            List[Dict[str, Any]]: A list of search result entries, each containing relevant metadata.
        """
        boost = {'question': 3.0, 'section': 0.5}
    
        results = self.index.search(
            query=query,
            filter_dict={'course': 'data-engineering-zoomcamp'},
            boost_dict=boost,
            num_results=5,
            output_ids=True
        )
    
        return results

    def add_entry(self, question: str, answer: str) -> None:
        """
        Add a new entry to the FAQ database.
    
        Args:
            question (str): The question to be added to the FAQ database.
            answer (str): The corresponding answer to the question.
        """
        doc = {
            'question': question,
            'text': answer,
            'section': 'user added',
            'course': 'data-engineering-zoomcamp'
        }
        self.index.append(doc)
```

Add it to tools:

```python
search_tools = SearchTools(index)

agent_tools = Tools()
agent_tools.add_tools(search_tools)
```

And run:

```python
runner = OpenAIResponsesRunner(
    tools=agent_tools,
    developer_prompt=developer_prompt,
    chat_interface=chat_interface,
    llm_client=OpenAIClient()
)

runner.run();
```

We can see that new documents are added:


```python
index.docs[-1]
```


## Agents SDK

Let's see how to implement this with OpenAI Agents SDK

```bash
pip insall openai-agents
```

```python
from agents import Agent, function_tool
```

Agent:

```python
developer_prompt = """
You're a course teaching assistant. 
You're given a question from a course student and your task is to answer it.

If you want to look up the answer, explain why before making the call. Use as many 
keywords from the user question as possible when making first requests.

Make multiple searches. Try to expand your search by using new keywords based on the results you
get from the search.

At the end, make a clarifying question based on what you presented and ask if there are 
other areas that the user wants to explore.
""".strip()

tools = [
    function_tool(search_tools.search),
    function_tool(search_tools.add_entry)
]

agent = Agent(
    name="JokeAgent",
    instructions=developer_prompt,
    tools=tools,
    model='gpt-4o-mini'
)
```

We can simplify adding tools with toyaikit:

```python
from toyaikit.tools import wrap_instance_methods
tools = wrap_instance_methods(function_tool, search_tools)
```

Let's run it:


```python
from toyaikit.chat import IPythonChatInterface
from toyaikit.chat.runners import OpenAIAgentsSDKRunner

chat_interface = IPythonChatInterface()
runner = OpenAIAgentsSDKRunner(
    chat_interface=chat_interface,
    agent=agent
)

await runner.run();
```

After the workshop, check the code for
[`OpenAIAgentsSDKRunner`](https://github.com/alexeygrigorev/toyaikit/blob/main/toyaikit/chat/runners.py#L169)
to see how it's implemented. When you work with Agents SDK,
you will need to implement it yourself.

Let's test it:

- "How do I do well in module 1?"
- "How about Docker?"
- "Add this back to FAQ"

Also, it provides a very convenient way to run multiple agents.
You can [_handoff_ a task to another agent](https://openai.github.io/openai-agents-python/handoffs/).
You can implement it yourself by creating a tool that
wraps up the code for invoking another agent.
But Agents SDK can do it for you. We will not cover it here
but we will talk about it in the course. (Also it's fairy
easy to implement it yourself.)

## Pydantic AI

Another framework that makes it easier to interact with SDKs 
is [PydanticAI](https://ai.pydantic.dev/). Like Agents SDK,
it's also a wrapper around the OpenAI API. But unlike Agents SDK,
it works with other providers too, like Anthropic or Groq.

```bash
pip install pydantic-ai
```

Let's implement the same code with Pydantic AI:

```python
from pydantic_ai import Agent

tools = [
    search_tools.search,
    search_tools.add_entry
]

agent = Agent(
    name="faq_agent",
    instructions=developer_prompt,
    tools=tools,
    model='gpt-4o-mini'
)
```

Note that we don't need to decorate the tools, but we can 
do it if we want (see [here](https://ai.pydantic.dev/agents/))

We can also use a helper function from toyaikit to 
get a list of all instance methods: 

```python
from toyaikit.tools import get_instance_methods
tools = get_instance_methods(search_tools)
```

Let's run it:

```python
from toyaikit.chat import IPythonChatInterface
from toyaikit.chat.runners import PydanticAIRunner

chat_interface = IPythonChatInterface()
runner = PydanticAIRunner(
    chat_interface=chat_interface,
    agent=deep_research_agent
)

await runner.run();
```

Here I use toyaikit for simplicity, but later you will
probably need to implement this code yourself, so check 
[the implementation](https://github.com/alexeygrigorev/toyaikit/blob/main/toyaikit/chat/runners.py#L216).


## MCP (Model-Context Protocol)

Anthropic says that [MCP is like USB but for agent tools](https://modelcontextprotocol.io/docs/getting-started/intro).

Imagine you want to use a database in your application. You can 
spend a few days implementing the access to the DB using function
calls. And everyone who needs this will need to do it too.

Or, the database developer releases an MCP server, and everyone 
can use it. 

Let's put our FAQ data inside a database. Like previously,
we will have two methods: search and add_entry.

This is a separate project, so let's start a new `uv` project:

```bash
pip install uv # if you don't have uv
uv init
uv add minsearch requests fastmcp
```

Create a file `search_tools.py`:

```python
from typing import List, Dict, Any

class SearchTools:

    def __init__(self, index):
        self.index = index

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search the FAQ database for entries matching the given query.
    
        Args:
            query (str): Search query text to look up in the course FAQ.
    
        Returns:
            List[Dict[str, Any]]: A list of search result entries, each containing relevant metadata.
        """
        boost = {'question': 3.0, 'section': 0.5}
    
        results = self.index.search(
            query=query,
            filter_dict={'course': 'data-engineering-zoomcamp'},
            boost_dict=boost,
            num_results=5,
        )
    
        return results

    def add_entry(self, question: str, answer: str) -> None:
        """
        Add a new entry to the FAQ database.
    
        Args:
            question (str): The question to be added to the FAQ database.
            answer (str): The corresponding answer to the question.
        """
        doc = {
            'question': question,
            'text': answer,
            'section': 'user added',
            'course': 'data-engineering-zoomcamp'
        }
        self.index.append(doc)
```

There's nothing new in this code - I copy-pasted it from before.

Now let's create the main scrip - `main.py`. It will 
create the index and the tools.

```python
import requests 
from minsearch import AppendableIndex

from search_tools import SearchTools

def init_index():
    docs_url = 'https://github.com/alexeygrigorev/llm-rag-workshop/raw/main/notebooks/documents.json'
    docs_response = requests.get(docs_url)
    documents_raw = docs_response.json()

    documents = []

    for course in documents_raw:
        course_name = course['course']

        for doc in course['documents']:
            doc['course'] = course_name
            documents.append(doc)


    index = AppendableIndex(
        text_fields=["question", "text", "section"],
        keyword_fields=["course"]
    )

    index.fit(documents)
    return index


def init_tools():
    index = init_index()
    return SearchTools(index)


if __name__ == "__main__":
    tools = init_tools()
    print(tools.search("How do I install Kafka?"))
```

This is actually a good improvement - we could import the
`init_tools` function from main and already use it in our 
previous code (althougth in this case I'd keep it all inside
`search_tools.py`)

Now let's expose these tools with MCP. For that, we will need 
to create an MCP server. There are many frameworks for creating
them. We will use [FastMCP](https://github.com/jlowin/fastmcp):

```bash
uv add fastmcp # but we already did it before
```

This is the simplest possible MCP server (taken from the docs):

```python
from fastmcp import FastMCP

mcp = FastMCP("Demo 🚀")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

if __name__ == "__main__":
    mcp.run()
```

We see that we simply add an annotation to our functions 
and that's all we need to do.

Like previously, we can use toyaikit's helpers for doing 
this for all the methods of the `SearchTools` class

Add this to `main.py`

```python
from fastmcp import FastMCP
from toyaikit.tools import wrap_instance_methods


def init_mcp():
    mcp = FastMCP("Demo 🚀")
    agent_tools = init_tools()
    wrap_instance_methods(mcp.tool, agent_tools)
    return mcp


if __name__ == "__main__":
    mcp = init_mcp()
    mcp.run()
```

Let's run it!

```python
uv run python main.py
```

It uses standard input/output as transport:

```
📦 Transport:       STDIO 
```

Which means, we can paste things into our terminal to test it 
(and simulate the interaction with the server)

First, we need to initialize the connection. We do it with the 
handshake sequence:

1. Send the ininialization request
2. Confirm the initialization
3. Now can see the list of available tools 

Let's do this. Send the initialization request:

```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {"roots": {"listChanged": true}, "sampling": {}}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}
```

We get back something like that:

```json
{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"experimental":{},"prompts":{"listChanged":false},"resources":{"subscribe":false,"listChanged":false},"tools":{"listChanged":true}},"serverInfo":{"name":"Demo 🚀","version":"1.13.1"}}}
```

This is a confirmation that we can proceed. 

Next, confirm the initialization:

```json
{"jsonrpc": "2.0", "method": "notifications/initialized"}
```

We don't get back anything.

Now we can see the list of available tools:

```json
{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
```

We get back the list:

```json
{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"add_entry","description":"Add a new entry to the FAQ database.\n\nArgs:\n    question (str): The question to be added to the FAQ database.\n    answer (str): The corresponding answer to the question.","inputSchema":{"properties":{"question":{"title":"Question","type":"string"},"answer":{"title":"Answer","type":"string"}},"required":["question","answer"],"type":"object"},"_meta":{"_fastmcp":{"tags":[]}}},{"name":"search","description":"Search the FAQ database for entries matching the given query.\n\nArgs:\n    query (str): Search query text to look up in the course FAQ.\n\nReturns:\n    List[Dict[str, Any]]: A list of search result entries, each containing relevant metadata.","inputSchema":{"properties":{"query":{"title":"Query","type":"string"}},"required":["query"],"type":"object"},"outputSchema":{"properties":{"result":{"items":{"additionalProperties":true,"type":"object"},"title":"Result","type":"array"}},"required":["result"],"title":"_WrappedResult","type":"object","x-fastmcp-wrap-result":true},"_meta":{"_fastmcp":{"tags":[]}}}]}}
```

If we format it, we see that we have two tools: `search` and `add_entry`:

```json
{
    "jsonrpc": "2.0",
    "id": 2,
    "result": {
        "tools": [
            {
                "name": "add_entry",
                "description": "Add a new entry to the FAQ database.\n\nArgs:\n    question (str): The question to be added to the FAQ database.\n    answer (str): The corresponding answer to the question.",
                "inputSchema": {
                    "properties": {
                        "question": {
                            "title": "Question",
                            "type": "string"
                        },
                        "answer": {
                            "title": "Answer",
                            "type": "string"
                        }
                    },
                    "required": [
                        "question",
                        "answer"
                    ],
                    "type": "object"
                },
                "_meta": {
                    "_fastmcp": {
                        "tags": []
                    }
                }
            },
            {
                "name": "search",
                "description": "Search the FAQ database for entries matching the given query.\n\nArgs:\n    query (str): Search query text to look up in the course FAQ.\n\nReturns:\n    List[Dict[str, Any]]: A list of search result entries, each containing relevant metadata.",
                "inputSchema": {
                    "properties": {
                        "query": {
                            "title": "Query",
                            "type": "string"
                        }
                    },
                    "required": [
                        "query"
                    ],
                    "type": "object"
                },
                "outputSchema": {
                    "properties": {
                        "result": {
                            "items": {
                                "additionalProperties": true,
                                "type": "object"
                            },
                            "title": "Result",
                            "type": "array"
                        }
                    },
                    "required": [
                        "result"
                    ],
                    "title": "_WrappedResult",
                    "type": "object",
                    "x-fastmcp-wrap-result": true
                },
                "_meta": {
                    "_fastmcp": {
                        "tags": []
                    }
                }
            }
        ]
    }
}
```

Note: the schema for tools is somewhat similar to the OpenAI's function
calling, but not the same. 

Invoke a function:

```json
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "search", "arguments": {"query": "how do I run kafka?"}}}
```

And we get back the response:

```json
{"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"..."}],"isError":false}}
```

Let's invoke it from Jupyter.

First, we will use a simple MCP client
from toyaikit. You can check the implementation
[here](https://github.com/alexeygrigorev/toyaikit/blob/main/toyaikit/mcp/client.py). 
It's very similar to simply copying things to the terminal.
I asked Claude to implement it.

If you need an MCP client, you should use the built-in one
from FastMCP. However, it's async (which is good for production
cases), so testing it inside Jupyter is difficult.

Let's continue in Jupyter:

```python
from toyaikit.mcp import MCPClient, SubprocessMCPTransport

command = "uv run python main.py".split()
workdir = "faq-mcp"

client = MCPClient(
    transport=SubprocessMCPTransport(
        server_command=command,
        workdir=workdir
    )
)
```

Like we saw previously, we now need to:

- start the server (run the command)
- send "initialize"
- send "initialized"
- get tools 

This is how it looks in code:

```python
client.start_server()

client.initialize()
client.initialized()
client.get_tools()
```

Or we can do all 4 with one command:

```python
client.full_initialize()
```

Let's invoke the search tool:

```python
result = client.call_tool('search', {'query': 'how do I run docker?'})
```

Now if we want to use MCP with plain OpenAI API,
we need to convert the MCP tools into the function calling 
schemas. I implemented it in toyaikit, you can see the code 
here: TODO.

Let's use it:

```python
from toyaikit.llm import OpenAIClient
from toyaikit.mcp import MCPTools
from toyaikit.chat import IPythonChatInterface
from toyaikit.chat.runners import OpenAIResponsesRunner

mcp_tools = MCPTools(client)

chat_interface = IPythonChatInterface()

runner = OpenAIResponsesRunner(
    tools=mcp_tools,
    developer_prompt=developer_prompt,
    chat_interface=chat_interface,
    llm_client=OpenAIClient(model='gpt-4o-mini')
)
```

Run it:

```python
runner.run();
```


If we want to use the client from FastMCP,
it looks like that (but we won't do it here):

```python
import asyncio

async def main():
    async with Client("uv run python main.py") as mcp_client:
        # ...

if __name__ == "__main__":
    test = asyncio.run(main())
```


## PydanticAI with MCP

In practice you probably won't ever need to implement the
client yourself when we integrate tools into our agents:
frameworks like Agents SDK and PydanticAI can do it. 

Let's see how to do it with PydanticAI.

Make sure you have Pydantic AI with MCP support:

```bash
pip install pydantic-ai[mcp]
# or uv add
```

At the moment of writing, there are problems with running
this code on Windows. If you're on Windows, skip to 
"Running MCP with SSE". 

We will run it in Terminal (because of async-io) - but 
the code with SSE we will create later will also work in Jupyter.
If you only use Jupyter, also skip to "Running MCP with SSE". 

Here's our script test.py - create it in a separate folder:

```python
# test.py
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from toyaikit.chat.interface import StdOutputInterface
from toyaikit.chat.runners import PydanticAIRunner

mcp_client = MCPServerStdio(
    command="uv",
    args=["run", "python", "main.py"],
    cwd="faq-mcp"
)


developer_prompt = """
You're a course teaching assistant. 
You're given a question from a course student and your task is to answer it.

If you want to look up the answer, explain why before making the call. Use as many 
keywords from the user question as possible when making first requests.

Make multiple searches. Try to expand your search by using new keywords based on the results you
get from the search.

At the end, make a clarifying question based on what you presented and ask if there are 
other areas that the user wants to explore.
""".strip()


agent = Agent(
    name="faq_agent",
    instructions=developer_prompt,
    toolsets=[mcp_client],
    model='gpt-4o-mini'
)


chat_interface = StdOutputInterface()
runner = PydanticAIRunner(
    chat_interface=chat_interface,
    agent=agent
)


if __name__ == "__main__":
    import asyncio
    asyncio.run(runner.run())
```

We'll deal with dependencies using `uv`, so let's create an empty project

```bash
uv init 
uv add pydantic-ai[mcp] openai toyaikit
```

Run:

```bash
uv run python test.py
```

## Running MCP with SSE 

Previously we used Standard Input/Output as the transport for MCP.
We can also use HTTP (SSE) for that.

The only thing we need to change is how we run our server:

```python
mcp.run(transport="sse")
```

It's now available at "http://localhost:8000/sse". 

When it comes to our code, we only need to change this part:

```python
from pydantic_ai.mcp import MCPServerSSE

mcp_client = MCPServerSSE(
    url='http://localhost:8000/sse'
)
```

How it will use HTTP for communication.


## Adding MCP Server to Cursor

Now we can use this MCP server with any MCP Client.
For example, Cursor.

Add this server to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "faqmcp": {
      "command": "uv",
      "args": [
        "run",
        "--project", "faq-mcp",
        "python",
        "faq-mcp/main.py"
      ]
    }
  }
}
```

If we run our MCP server with SSE transport, we configure it this
way: 


```json
{
  "mcpServers": {
    "faqmcp": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

If you don't get asked if you want to enable it, go to Preferenes -> Cursor settings -> MCP and Integrations, find your MCP server and enable it.
 

Examples of prompts:

- "Write code for module 1, check the FAQ for requirements"
- "Implement kafka connection with Python. Use FAQ to do comprehensive research first and then explain your choices."

Note: this isn't really a good usecase for Cursor. 
A more powerful usecase would be adding search for some frameworks.
LLMs have some knowledge cutoff, while frameworks keep developing.
So having access to fresh information is important.

In the course we create MCP server for
[Evidently documentation](https://docs.evidentlyai.com/introduction)
and can use it directly from Cursor. 
