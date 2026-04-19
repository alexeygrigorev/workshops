import requests

from qdrant_client import QdrantClient, models


DOCS_URL = (
    "https://raw.githubusercontent.com/DataTalksClub/llm-zoomcamp/"
    "refs/heads/main/03-evaluation/search_evaluation/documents-with-ids.json"
)

COLLECTION_NAME = "faq"
EMBEDDING_MODEL = "jinaai/jina-embeddings-v2-small-en"
EMBEDDING_DIM = 512


def load_documents():
    return requests.get(DOCS_URL).json()


def build_text(doc):
    return f"{doc['question']}\n\n{doc['text']}"


def recreate_collection(client):
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=EMBEDDING_DIM,
            distance=models.Distance.COSINE,
        ),
    )


def index_documents(client, documents):
    points = []
    for i, doc in enumerate(documents):
        point = models.PointStruct(
            id=i,
            vector=models.Document(text=build_text(doc), model=EMBEDDING_MODEL),
            payload=doc,
        )
        points.append(point)

    client.upsert(collection_name=COLLECTION_NAME, points=points)


def main():
    client = QdrantClient("http://localhost:6333")
    documents = load_documents()
    print(f"loaded {len(documents)} documents")

    recreate_collection(client)
    index_documents(client, documents)
    print(f"indexed {len(documents)} documents into '{COLLECTION_NAME}'")


if __name__ == "__main__":
    main()
