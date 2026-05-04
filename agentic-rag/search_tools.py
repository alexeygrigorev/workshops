from typing import Any

from gitsource import GithubRepositoryDataReader, chunk_documents
from minsearch import Highlighter, Index, Tokenizer
from minsearch.tokenizer import DEFAULT_ENGLISH_STOP_WORDS


def load_evidently_docs() -> list[dict[str, Any]]:
    reader = GithubRepositoryDataReader(
        repo_owner="evidentlyai",
        repo_name="docs",
        allowed_extensions={"md", "mdx"},
    )

    files = reader.read()
    return [doc.parse() for doc in files]


def build_chunked_index(parsed_docs: list[dict[str, Any]], size: int = 3000, step: int = 1500):
    chunked_docs = chunk_documents(parsed_docs, size=size, step=step)

    index = Index(
        text_fields=["title", "description", "content"],
        keyword_fields=["filename"],
    )
    index.fit(chunked_docs)

    return index, chunked_docs


def build_full_document_index(parsed_docs: list[dict[str, Any]]):
    index = Index(
        text_fields=["title", "description", "content"],
        keyword_fields=["filename"],
    )
    index.fit(parsed_docs)
    return index


def build_highlighter():
    stopwords = DEFAULT_ENGLISH_STOP_WORDS | {"evidently"}
    tokenizer = Tokenizer(stemmer="snowball", stop_words=stopwords)

    return Highlighter(
        highlight_fields=["content"],
        max_matches=3,
        snippet_size=50,
        tokenizer=tokenizer,
    )


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


def create_search_tools(parsed_docs: list[dict[str, Any]]) -> SearchTools:
    index = build_full_document_index(parsed_docs)
    highlighter = build_highlighter()
    file_index = {doc["filename"]: doc["content"] for doc in parsed_docs}
    return SearchTools(index=index, highlighter=highlighter, file_index=file_index)
