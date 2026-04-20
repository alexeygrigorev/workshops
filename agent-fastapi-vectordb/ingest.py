import os

from qdrant_client import QdrantClient, models

from faq import load_documents
from search import COLLECTION_NAME, EMBEDDING_DIM, EMBEDDING_MODEL


def connect_qdrant():
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY")
    return QdrantClient(url=url, api_key=api_key)


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
        text = f"{doc['section']}\n{doc['question']}\n{doc['answer']}"
        point = models.PointStruct(
            id=i,
            vector=models.Document(text=text, model=EMBEDDING_MODEL),
            payload=doc,
        )
        points.append(point)

    client.upsert(collection_name=COLLECTION_NAME, points=points)


def main():
    client = connect_qdrant()

    documents = load_documents()
    print(f"loaded {len(documents)} FAQ entries")

    recreate_collection(client)
    index_documents(client, documents)
    print(f"indexed {len(documents)} documents into '{COLLECTION_NAME}'")


if __name__ == "__main__":
    main()
