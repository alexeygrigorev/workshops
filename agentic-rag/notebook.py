# %%
# Follow-along code for "From RAG to Agents: Implementing Agentic Search".
#
# This file is intentionally written like a notebook. During the workshop,
# copy each cell into Jupyter and run it in order.

# %%
# Setup

import json
import os
from typing import Any

from openai import OpenAI

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
openai_client = OpenAI()

# %%
# Part 1: load the Evidently documentation

from gitsource import GithubRepositoryDataReader

reader = GithubRepositoryDataReader(
    repo_owner="evidentlyai",
    repo_name="docs",
    allowed_extensions={"md", "mdx"},
)

files = reader.read()
parsed_docs = [doc.parse() for doc in files]

len(parsed_docs)

# %%
# Part 1: chunk the documents

from gitsource import chunk_documents

chunked_docs = chunk_documents(parsed_docs, size=3000, step=1500)
len(chunked_docs)

# %%
# Part 1: build a classic RAG search index

from minsearch import Index

index = Index(
    text_fields=["title", "description", "content"],
    keyword_fields=["filename"],
)

index.fit(chunked_docs)

# %%
# Part 1: search


def search(query: str) -> list[dict[str, Any]]:
    return index.search(query=query, num_results=5)


search("how to create a dashboard")[0]

# %%
# Part 1: prompt builder

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


def build_prompt(question: str, search_results: list[dict[str, Any]]) -> str:
    context = json.dumps(search_results, indent=2)
    return RAG_PROMPT_TEMPLATE.format(question=question, context=context)


question = "How do I create a dashboard in Evidently?"
search_results = search(question)
user_prompt = build_prompt(question, search_results)

print(user_prompt[:1000])

# %%
# Part 1: LLM call


def llm(instructions: str, user_prompt: str, model: str = MODEL_NAME) -> str:
    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": user_prompt},
    ]
    response = openai_client.responses.create(model=model, input=messages)
    return response.output_text


def rag(question: str) -> str:
    search_results = search(question)
    user_prompt = build_prompt(question, search_results)
    return llm(RAG_INSTRUCTIONS, user_prompt)


# %%
# Requires OPENAI_API_KEY.
# print(rag("How do I create a dashboard in Evidently?"))
# print(rag("How do I create a dahsbord in Evidently?"))

# %%
# Part 2: create a one-tool agent with toyaikit

from toyaikit.tools import Tools


AGENT_INSTRUCTIONS = """
You're a documentation assistant.
Answer the user question using the documentation knowledge base.

Use only facts from the knowledge base when answering.
If you cannot find the answer, inform the user.
""".strip()

agent_tools = Tools()
agent_tools.add_tool(search)

agent_tools.get_tools()

# %%
# Part 2: run the toyaikit agent

from toyaikit.chat.interface import IPythonChatInterface
from toyaikit.chat.runners import DisplayingRunnerCallback, OpenAIResponsesRunner
from toyaikit.llm import OpenAIClient

llm_client = OpenAIClient(model=MODEL_NAME, client=openai_client)
chat_interface = IPythonChatInterface()
runner_callback = DisplayingRunnerCallback(chat_interface=chat_interface)

agent = OpenAIResponsesRunner(
    tools=agent_tools,
    developer_prompt=AGENT_INSTRUCTIONS,
    chat_interface=chat_interface,
    llm_client=llm_client,
)

# %%
# Requires OPENAI_API_KEY.
# result = agent.loop("How do I create a dahsbord in Evidently?", callback=runner_callback)
# print(result.last_message)

# %%
# Part 3: rebuild the index over full documents, not chunks

index = Index(
    text_fields=["title", "description", "content"],
    keyword_fields=["filename"],
)

index.fit(parsed_docs)

# %%
# Part 3: create the highlighter

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

# %%
# Part 3: test highlighted snippets

query = "how to create a dashboard"
search_results = index.search(query=query, num_results=5)

snippets = highlighter.highlight(query, search_results)
snippets[0]

# %%
# Part 3: create a file lookup

file_index = {doc["filename"]: doc["content"] for doc in parsed_docs}

filename = next(iter(file_index))
print(filename)
print(file_index[filename][:500])

# %%
# Part 3: define the two-tool search class


class SearchTools:
    """Search and file retrieval tools over an indexed documentation store."""

    def __init__(self, index, highlighter, file_index: dict[str, str]):
        self.index = index
        self.highlighter = highlighter
        self.file_index = file_index

    def search(self, query: str) -> list[dict[str, Any]]:
        """
        Search the documentation database and return highlighted snippets.

        Args:
            query: The search query to look up in the index.

        Returns:
            Matching documents with short highlighted snippets.
        """
        search_results = self.index.search(query=query, num_results=5)
        return self.highlighter.highlight(query, search_results)

    def get_file(self, filename: str) -> str:
        """
        Retrieve the full contents of a documentation file.

        Args:
            filename: The filename to retrieve.

        Returns:
            The full file contents, or an error message if the file is missing.
        """
        if filename in self.file_index:
            return self.file_index[filename]
        return f"file {filename} does not exist"


search_tools = SearchTools(index, highlighter, file_index)

# %%
# Part 3: smoke-test both tools

snippets = search_tools.search("create a dashboard")
snippets[0]

# %%

filename = snippets[0]["filename"]
print(filename)
print(search_tools.get_file(filename)[:500])

# %%
# Part 3: register both tools

agentic_tools = Tools()
agentic_tools.add_tools(search_tools)

agentic_tools.get_tools()

# %%
# Part 3: stronger instructions for agentic search

AGENTIC_SEARCH_INSTRUCTIONS = """
You're a documentation assistant.

Answer the user question using only the documentation knowledge base.

Make 3 iterations:

1) First iteration:
   - Perform one search using the search tool to identify potentially relevant documents.
   - Explain in 2-3 sentences why this search query is appropriate for the user question.

2) Second iteration:
   - Analyze the results from the previous search.
   - Based on the filenames or documents returned, perform:
       - Up to 2 additional search queries to refine or expand coverage, and
       - One or more get_file calls to retrieve the full content of the most relevant documents.
   - For each search or get_file call, explain in 2-3 sentences why this action is necessary and how it helps answer the question.

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
- Prefer retrieving and analyzing full documents via get_file before producing the final answer.
""".strip()

agentic_search_agent = OpenAIResponsesRunner(
    tools=agentic_tools,
    developer_prompt=AGENTIC_SEARCH_INSTRUCTIONS,
    chat_interface=chat_interface,
    llm_client=llm_client,
)

# %%
# Requires OPENAI_API_KEY.
# result = agentic_search_agent.loop(
#     "how can I create evidently dahsbord? show me the code",
#     callback=runner_callback,
# )
# print(result.last_message)

# %%
# Part 4: create the PydanticAI agent

from pydantic_ai import Agent


pydantic_search_agent = Agent(
    name="search",
    model=f"openai:{MODEL_NAME}",
    instructions=AGENTIC_SEARCH_INSTRUCTIONS,
    tools=[search_tools.search, search_tools.get_file],
)

# %%
# Requires OPENAI_API_KEY and a notebook that supports top-level await.
# result = await pydantic_search_agent.run(
#     "how do I use evidently to monitor my machine learning models?"
# )
# print(result.output)

# %%
# Part 4: inspect messages


def print_messages(messages):
    for message in messages:
        print(message.kind)
        for part in message.parts:
            part_kind = part.part_kind
            if part_kind == "user-prompt":
                print("USER:", part.content)
            if part_kind == "tool-call":
                print("TOOL CALL:", part.tool_name, part.args)
            if part_kind == "tool-return":
                print("TOOL RETURN:", part.tool_name)
            if part_kind == "text":
                print(part.content)
        print()


# %%
# Part 4: multi-turn PydanticAI conversation
#
# from pydantic_ai.usage import RunUsage
#
# messages = []
# usage = RunUsage()
#
# while True:
#     user_prompt = input("You: ")
#     if user_prompt.lower().strip() == "stop":
#         break
#
#     result = await pydantic_search_agent.run(user_prompt, message_history=messages)
#     usage = usage + result.usage()
#
#     print_messages(result.new_messages())
#     messages.extend(result.new_messages())
#
# print(usage)
