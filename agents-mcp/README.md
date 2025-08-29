# Create a Coding Agent

This workshop is a part of the
[AI Bootcamp: From RAG to Agents](https://maven.com/alexey-grigorev/from-rag-to-agents) course.

- Video: TBA

Previously, in the ["Create Your Own Coding Agent" workshop](../coding-agent/)
we created a coding agent that could create a Django application
from a single prompt.

In this workshop, we will deep dive into agents.

We will

- look into function calling - the thing that distinguishes agents from Q&A bots
- implement a deep research agent that  
- ...
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

After the workshop, check the code for OpenAIAgentsSDKRunner to
see how it's implemented. When you work with this framework,
you will need to implement it yourself.



