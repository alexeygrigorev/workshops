import os
from functools import lru_cache

from minsearch import AppendableIndex
from qdrant_client import QdrantClient, models

from faq import load_documents


COLLECTION_NAME = "faq"
EMBEDDING_MODEL = "jinaai/jina-embeddings-v2-small-en"
EMBEDDING_DIM = 512
DEFAULT_SEARCH_BACKEND = "minsearch"
SEARCH_BOOSTS = {
    "question": 3.0,
    "section": 0.5,
    "answer": 1.0,
}


class MinsearchBackend:
    def __init__(self, documents):
        self.index = AppendableIndex(
            text_fields=["question", "answer", "section"],
            keyword_fields=["course"],
        )
        self.index.fit(documents)

    def search(self, query: str, course: str | None = None, limit: int = 5):
        search_kwargs = {
            "query": query,
            "boost_dict": SEARCH_BOOSTS,
            "num_results": limit,
        }
        if course:
            search_kwargs["filter_dict"] = {"course": course}

        results = self.index.search(**search_kwargs)

        hits = []
        for rank, doc in enumerate(results, start=1):
            hit = dict(doc)
            hit.setdefault("score", round(1.0 / rank, 3))
            hits.append(hit)

        return hits


class QdrantBackend:
    def __init__(self, url: str, api_key: str | None = None):
        self.client = QdrantClient(url=url, api_key=api_key)

    def search(self, query: str, course: str | None = None, limit: int = 5):
        query_filter = None
        if course:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="course",
                        match=models.MatchValue(value=course),
                    )
                ]
            )

        results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=models.Document(text=query, model=EMBEDDING_MODEL),
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

        hits = []
        for point in results.points:
            payload = point.payload or {}
            hits.append(
                {
                    "id": payload.get("id"),
                    "course": payload.get("course"),
                    "section": payload.get("section"),
                    "question": payload.get("question"),
                    "answer": payload.get("answer"),
                    "score": float(point.score),
                }
            )

        return hits


def build_search_backend(search_backend: str | None = None):
    backend = (search_backend or os.getenv("SEARCH_BACKEND", DEFAULT_SEARCH_BACKEND)).lower()

    if backend == "minsearch":
        documents = load_documents()
        return MinsearchBackend(documents)

    if backend == "qdrant":
        return QdrantBackend(
            url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )

    raise ValueError(f"unknown SEARCH_BACKEND: {backend}")


@lru_cache(maxsize=2)
def get_search_backend(search_backend: str | None = None):
    return build_search_backend(search_backend)
