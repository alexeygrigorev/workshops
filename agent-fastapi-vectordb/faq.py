import requests


BASE_FAQ_URL = "https://datatalks.club/faq"
COURSES_INDEX_URL = f"{BASE_FAQ_URL}/json/courses.json"
COURSES = [
    {"id": "llm-zoomcamp", "name": "LLM Zoomcamp"},
    {"id": "ml-zoomcamp", "name": "ML Zoomcamp"},
    {"id": "mlops-zoomcamp", "name": "MLOps Zoomcamp"},
    {"id": "data-engineering-zoomcamp", "name": "Data Engineering Zoomcamp"},
]


def load_documents():
    response = requests.get(COURSES_INDEX_URL, timeout=30)
    response.raise_for_status()

    documents = []
    courses_index = response.json()

    for course in courses_index:
        course_url = f"{BASE_FAQ_URL}/{course['path']}"
        course_response = requests.get(course_url, timeout=30)
        course_response.raise_for_status()
        documents.extend(course_response.json())

    return documents
