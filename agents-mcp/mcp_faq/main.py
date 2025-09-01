import requests 
from minsearch import AppendableIndex
from fastmcp import FastMCP
from toyaikit.tools import wrap_instance_methods

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


def init_mcp():
    mcp = FastMCP("Demo 🚀")
    agent_tools = init_tools()
    wrap_instance_methods(mcp.tool, agent_tools)
    return mcp


if __name__ == "__main__":
    mcp = init_mcp()
    mcp.run(transport="sse")