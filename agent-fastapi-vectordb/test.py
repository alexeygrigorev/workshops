import requests

URL = "http://localhost:9696"
# URL = "https://agent-fastapi-vectordb.fly.dev"


def test_search():
    payload = {
        "query": "I just discovered the course, can I join now?",
        "course": "data-engineering-zoomcamp",
        "limit": 3,
    }
    response = requests.post(f"{URL}/search", json=payload)
    print("search:", response.status_code)
    for hit in response.json()["hits"]:
        print(f"  {hit['score']:.3f}  {hit['question']}")


def test_ask():
    payload = {
        "question": "I just discovered the course, can I still join?",
        "course": "data-engineering-zoomcamp",
    }
    response = requests.post(f"{URL}/ask", json=payload)
    print("ask:", response.status_code)
    body = response.json()
    print("answer:", body["answer"])


if __name__ == "__main__":
    test_search()
    print()
    test_ask()
