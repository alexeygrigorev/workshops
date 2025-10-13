# RAG Evaluations Workshop

This workshop is a part of the
[AI Bootcamp: From RAG to Agents](https://maven.com/alexey-grigorev/from-rag-to-agents) course.

- Video: [TODO: Add YouTube link]

In this workshop, we will learn how to evaluate RAG (Retrieval-Augmented Generation) systems and Agentic RAG implementations.

We will:

- Build a basic RAG system for FAQ answering
- Create an Agentic RAG implementation using `toyaikit`
- Generate synthetic evaluation data
- Implement evaluation metrics (Hit Rate and MRR)
- Evaluate search performance


## Prerequisites

- Python
- OpenAI key


## Environment Setup

Initialize the project with `uv`:

```bash
uv init
uv add openai requests minsearch toyaikit
```


## RAG System Overview

First, let's understand the RAG architecture:

```python
def rag(question):
    search_results = search(question)
    user_prompt = build_prompt(question, search_results)
    return llm(user_prompt, instructions=instructions)
```

A RAG system consists of three main components:

1. **Search** - Retrieve relevant documents
2. **Prompt Building** - Create context from search results
3. **LLM** - Generate answer based on context


## FAQ Use Case

### Data Preparation

Load the FAQ documents:

```python
import requests 

docs_url = 'https://raw.githubusercontent.com/DataTalksClub/llm-zoomcamp/refs/heads/main/03-evaluation/search_evaluation/documents-with-ids.json'

documents = requests.get(docs_url).json()
```

### Search Implementation

Set up the search index using `minsearch`:

```python
from minsearch import Index

index = Index(
    text_fields=["question", "text", "section"],
    keyword_fields=["course"]
)

index.fit(documents)
```

Implement the search function:

```python
def search(question):
    return index.search(
        question,
        boost_dict={'question': 3.0, 'section': 0.3},
        filter_dict={'course': 'data-engineering-zoomcamp'},
        num_results=5
    )
```

Test the search:

```python
question = 'I just discovered the course, can I join now?'
search_results = search(question)
```

### Prompt Engineering

Define instructions and prompt template:

```python
instructions = """
You're a course teaching assistant. Answer the QUESTION based on the CONTEXT from the FAQ database.
Use only the facts from the CONTEXT when answering the QUESTION.
""".strip()

prompt_template = """
<QUESTION>
{question}
</QUESTION>

<CONTEXT>
{context}
</CONTEXT>
""".strip()
```

Build the prompt:

```python
import json

def build_prompt(question, search_results):
    search_json = json.dumps(search_results)
    return prompt_template.format(
        question=question,
        context=search_json
    )
```

### LLM Integration

Implement the LLM function:

```python
from openai import OpenAI

openai_client = OpenAI()

def llm(user_prompt, instructions=None, model="gpt-4o-mini"):
    messages = []

    if instructions:
        messages.append({
            "role": "system",
            "content": instructions
        })

    messages.append({
        "role": "user",
        "content": user_prompt
    })

    response = openai_client.responses.create(
        model=model,
        input=messages
    )

    return response.output_text
```

Test the complete RAG system:

```python
question = 'I just discovered the course, can I join now?'
answer = rag(question)
print(answer)
```


## Agentic RAG

Install `toyaikit`:

```bash
uv add toyaikit
```

Set up the agentic RAG system:

```python
from toyaikit.llm import OpenAIClient
from toyaikit.chat import IPythonChatInterface
from toyaikit.chat.runners import OpenAIResponsesRunner
from toyaikit.chat.runners import DisplayingRunnerCallback
from toyaikit.tools import Tools

agent_tools = Tools()
agent_tools.add_tool(search)

chat_interface = IPythonChatInterface()

runner = OpenAIResponsesRunner(
    tools=agent_tools,
    developer_prompt=instructions,
    chat_interface=chat_interface,
    llm_client=OpenAIClient()
)

runner.run();
```

**Key Insight**: Both RAG and Agentic RAG share the same search component. The main difference is in how they orchestrate the retrieval and generation process.


## Evaluation

### Why Evaluate?

How do we know if our RAG system is performing well? We need metrics to measure retrieval quality.

Common retrieval evaluation metrics (ask ChatGPT: "which metrics we use for evaluating retrieval"):

- Hit Rate
- Mean Reciprocal Rank (MRR)
- Precision
- Recall
- NDCG

We'll focus on **Hit Rate** and **MRR**.

### Evaluation Strategy

**Ideal approach**: Launch system → Collect user data → Label it → Evaluate

**Starting approach**: When launching a new RAG/Agent project, generate synthetic evaluation data.


## Synthetic Data Generation

### Data Generation Instructions

```python
data_gen_instructions = """
You emulate a student who's taking our course.
Formulate 5 questions this student might ask based on a FAQ record. The record
should contain the answer to the questions, and the questions should be complete and not too short.
If possible, use as fewer words as possible from the record. 
""".strip()
```

### Structured Output

Implement structured LLM output:

```python
def llm_structured(instructions, user_prompt, output_type, model="gpt-4o-mini"):
    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": user_prompt}
    ]

    response = openai_client.responses.parse(
        model=model,
        input=messages,
        text_format=output_type
    )

    return response.output_parsed
```

Define output schema:

```python
from pydantic import BaseModel

class Questions(BaseModel):
    questions: list[str]
```

### Generate Questions

For a single document:

```python
questions = llm_structured(
    data_gen_instructions,
    json.dumps(documents[0]),
    Questions
)
```

### Parallel Processing

Speed up generation with parallel processing:

```python
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

def map_progress(pool, seq, f):
    """Map function f over seq using the provided executor pool while
    displaying a tqdm progress bar. Returns a list of results in submission order.
    """
    results = []

    with tqdm(total=len(seq)) as progress:
        futures = []

        for el in seq:
            future = pool.submit(f, el)
            future.add_done_callback(lambda p: progress.update())
            futures.append(future)

        for future in futures:
            result = future.result()
            results.append(result)

    return results

def process(doc):
    out = llm_structured(
        data_gen_instructions,
        json.dumps(doc),
        Questions
    )
    results = []
    for q in out.questions:
        new_doc = doc.copy()
        del new_doc['text']
        new_doc['question'] = q
        results.append(new_doc)
    return results

with ThreadPoolExecutor(max_workers=4) as pool:
    ground_truth = map_progress(pool, documents, process)
```

Flatten the results:

```python
import pandas as pd

ground_truth_flat = [item for sublist in ground_truth for item in sublist]
df_ground_truth = pd.DataFrame(ground_truth_flat)
```

**Key insight**: Because of how we generated the data, we know which document is correct for each question.


## Evaluation Metrics

### Generate Relevance Data

Search for each question and collect retrieved document IDs:

```python
relevance_total = []

for q in ground_truth_flat:
    doc_id = q['id']
    results = search(q['question'])
    relevance = [d['id'] == doc_id for d in results]
    relevance_total.append(relevance)
```

Data structure:
- `question`: Generated question
- `expected_id`: Correct document ID (one ID)
- `retrieved_ids`: List of retrieved document IDs
- `relevance`: Boolean array indicating matches

### Example Relevance Data

```python
example = [
    [True, False, False, False, False],  # 1
    [False, False, False, False, False], # 0
    [False, False, False, False, False], # 0
    [False, False, False, False, False], # 0
    [False, False, False, False, False], # 0
    [True, False, False, False, False],  # 1
    [True, False, False, False, False],  # 1
    [True, False, False, False, False],  # 1
    [True, False, False, False, False],  # 1
    [True, False, False, False, False],  # 1
    [False, False, True, False, False],  # 1/3
    [False, False, False, False, False], # 0
]
```

`True` if the retrieved document matches the expected document, `False` otherwise.

### Hit Rate

Hit Rate measures if the correct document appears anywhere in the results:

```python
def hit_rate(relevance_total):
    cnt = 0

    for line in relevance_total:
        if True in line:
            cnt = cnt + 1

    return cnt / len(relevance_total)
```

For the example:

```python
hit_rate(example)
# 0.5833333333333334
```

### Mean Reciprocal Rank (MRR)

MRR measures how high the correct document is ranked:

```python
def mrr(relevance_total):
    total_score = 0.0

    for line in relevance_total:
        for rank in range(len(line)):
            if line[rank] == True:
                total_score = total_score + 1 / (rank + 1)

    return total_score / len(relevance_total)
```

For the example:

```python
mrr(example)
# 0.5277777777777778
```

### Evaluation Function

Combine metrics into a single evaluation function:

```python
def evaluate(ground_truth, search_function):
    relevance_total = []

    for q in tqdm(ground_truth):
        doc_id = q['id']
        results = search_function(q['question'])
        relevance = [d['id'] == doc_id for d in results]
        relevance_total.append(relevance)

    return {
        'hit_rate': hit_rate(relevance_total),
        'mrr': mrr(relevance_total),
    }
```

Run evaluation:

```python
results = evaluate(ground_truth_flat, search)
print(f"Hit Rate: {results['hit_rate']:.3f}")
print(f"MRR: {results['mrr']:.3f}")
```


## Summary

In this workshop, we:

- Built a complete RAG system with search, prompt engineering, and LLM integration
- Implemented an Agentic RAG using `toyaikit`
- Generated synthetic evaluation data using structured LLM outputs
- Implemented Hit Rate and MRR evaluation metrics
- Created a reusable evaluation framework

## Next Steps

- Experiment with different search parameters (boost values, number of results)
- Try different prompt templates
- Compare RAG vs Agentic RAG performance
- Implement additional metrics (Precision, Recall, NDCG)
- Collect real user data for evaluation
- Optimize based on evaluation results
