# Coding Agent v2

In this workshop, we are going to implement a coding agent that has skills.

Plan:

1. Start with a short introduction to tool calling
2. Build the coding agent itself
3. Add skills
4. Run the same agent with PydanticAI


Related workshops and repos:

- [coding-agent](../coding-agent/)
- [agent-skills](../agent-skills/)
- [now-workshop-agents](https://github.com/alexeygrigorev/now-workshop-agents)


## Prerequisites

- Python 3.10+
- OpenAI API key
- Groq API key (optional)
- GitHub account


## Environment

We will use GitHub Codespaces for this workshop.

If you don't want to use Codespaces, you can use a local environment instead. The main requirement is that you have Python installed. The rest of the workshop should work fine locally too.

### Setting up GitHub Codespaces

1. Create a new empty GitHub repository for this workshop
2. Open that repository on GitHub
3. Click `Code`
4. Open the `Codespaces` tab
5. Click `Create codespace on main`
6. Wait until the VS Code web environment starts
7. Open the terminal inside the codespace

### Getting an OpenAI API key

OpenAI key is required for this workshop.

1. Create an account or sign in at [platform.openai.com](https://platform.openai.com/)
2. Open the API keys page: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
3. Click `Create new secret key`
4. Copy the key and store it somewhere safe

### Getting a Groq API key

Groq is optional, but we will show how to use it with the OpenAI SDK.

1. Create an account or sign in at [console.groq.com](https://console.groq.com/)
2. Open the API keys page: [console.groq.com/keys](https://console.groq.com/keys)
3. Click `Create API Key`
4. Copy the key and store it somewhere safe

### Adding keys to Codespaces

Add your keys as Codespaces secrets so they are available as environment variables inside the codespace.

1. On GitHub, click your profile picture and open `Settings`
2. In the sidebar, open `Codespaces`
3. Next to `Codespaces secrets`, click `New secret`
4. Create `OPENAI_API_KEY` and paste your OpenAI key
5. Give your repository access to that secret
6. Optionally create `GROQ_API_KEY` the same way

After creating or updating secrets, restart the codespace or create a new one so the variables are available.

All commands below should be run from the root of that repository inside the codespace.

Initialize the project:

```bash
pip install uv
uv init
uv add jupyter openai
```

Start Jupyter:

```bash
uv run jupyter notebook
```

All Python snippets below are meant to be run inside the notebook. If you want to run them from the terminal instead, use `uv run python`.

### OpenAI Client Setup

We will use these two variables throughout the OpenAI SDK sections of the workshop:

```python
from openai import OpenAI

openai_client = OpenAI()
model = 'gpt-5.4-mini'
```

### Optional: Groq with the OpenAI SDK

If you want to use Groq instead, keep the same variable names and switch `openai_client` and `model`:

```python
from openai import OpenAI
import os

openai_client = OpenAI(
    api_key=os.getenv('GROQ_API_KEY'),
    base_url='https://api.groq.com/openai/v1'
)
model = 'llama-3.3-70b-versatile'
```


## Part 1: Tool Calls Intro

We start by comparing simple messaging with tool calling using the OpenAI Responses API.

### Tools

Tools are functions the agent can call to interact with the world.

Without tools, the model only sees the prompt and can only guess. With tools, it can inspect files, run commands, search in code, and use the results before answering.

In other words, the flow looks like this:

- user gives input
- agent sees the input, instructions, available tools, and message history
- agent decides: respond directly or call a tool
- if it calls a tool, we execute it, add the result back to the conversation, and continue
- when it has enough information, it sends the final answer

This is why tools matter for coding agents. A coding agent should not only talk about code. It should be able to inspect a real project, read files, make changes, and verify the result.

Later in this workshop, our coding agent will use these core tools:

1. `read_file`
2. `write_file`
3. `see_file_tree`
4. `execute_bash_command`
5. `search_in_files`

### Goal

We will start with a smaller example before moving to the full coding-agent toolset.

In this example, we will ask the same question several times and see how the answer changes as we give the model more capabilities.

Questions:

- `What's in this folder?`
- `What dependencies does this project have?`
- `What's in this folder and inside the files?`

### Without Tools

First, let's ask the model a question without any tools:

```python
system_prompt = "You are a helpful coding assistant."
user_prompt = "What's in this folder?"

chat_messages = [
    {"role": "developer", "content": system_prompt},
    {"role": "user", "content": user_prompt}
]

response = openai_client.responses.create(
    model=model,
    input=chat_messages,
)

print(response.output_text)
```

Without tools, the model can only guess. Now let's add tools one by one.

### Defining the First Tool

First, define `see_file_tree` as a normal Python function:

```python
import os

def see_file_tree(root_dir: str = ".") -> list[str]:
    tree = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in {".git", ".venv", "__pycache__"}]

        for name in sorted(dirnames + filenames):
            full_path = os.path.join(dirpath, name)
            tree.append(os.path.relpath(full_path, root_dir))

    return tree
```

Let's test it:

```python
see_file_tree(".")[:20]
```

At this point, this is just a regular Python function. The LLM still doesn't know that it exists.

Now we need to make it available to the LLM. For that, we pass a tool description that tells the model:

- the tool name
- what the tool does
- which arguments it accepts
- which arguments are required

This is the schema the model sees:

```python
see_file_tree_description = {
    "type": "function",
    "name": "see_file_tree",
    "description": "List files and directories in the current project.",
    "parameters": {
        "type": "object",
        "properties": {
            "root_dir": {
                "type": "string",
                "description": "Directory to list. Defaults to the current directory.",
            }
        },
        "required": [],
        "additionalProperties": False,
    },
}
```

### Using the First Tool

Now let's include the tool in the request:

```python
response = openai_client.responses.create(
    model=model,
    input=chat_messages,
    tools=[see_file_tree_description]
)
```

Inspect what the model returned.

Let's look at the structured output:

```python
response.output
```

`response.output` contains everything the model returned. In a text-only response, this is usually a message. In a tool-calling response, one of the items can be a `function_call`.

Let's look at the first item:

```python
call = response.output[0]
call
```

The most important fields here are:

- `type` - tells us whether this is a message or a function call
- `name` - the tool the model wants to call
- `arguments` - the JSON arguments for that tool
- `call_id` - the identifier we use when sending the tool result back

Inspect them directly:

```python
call.type
call.name
call.arguments
call.call_id
```

If you want to inspect the entire raw response structure, use:

```python
import json

print(json.dumps(response.model_dump(), indent=2))
```

At this point, the model is not executing the function by itself. It is only telling us which tool it wants to call and with which arguments.

Parse the arguments and run the Python function.

The arguments come back as JSON, so first we parse them:

```python
args = json.loads(call.arguments)
args
```

Now run the actual Python function:

```python
result = see_file_tree(**args)
result[:20]
```

This is the key idea of tool calling:

- the model decides which tool to use
- our Python code executes the tool
- then we send the result back to the model

Add the tool result to the conversation.

Because the model is stateless, we need to maintain the conversation history ourselves.

We first add all the output:

```python
chat_messages.extend(response.output)
```

Now append the tool result as `function_call_output`:

```python
chat_messages.append({
    "type": "function_call_output",
    "call_id": call.call_id,
    "output": json.dumps(result),
})
```

The `call_id` matters because it tells the model which tool call this output belongs to.

Ask the model again.

Now that the model has the tool result, we call it one more time:

```python
response = openai_client.responses.create(
    model=model,
    input=chat_messages,
    tools=[see_file_tree_description]
)
```

And now we can read the final text answer:

```python
print(response.output_text)
```

### Adding the Second Tool

If we want the model to go beyond the directory tree and inspect actual files, we need another tool. Let's allow the agent to read files.
 
Define `read_file`:

```python
def read_file(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()
```

Test it directly:

```python
read_file("pyproject.toml")
```

Again, this is just a normal Python function so far.

Describe the tool for the model.

```python
read_file_description = {
    "type": "function",
    "name": "read_file",
    "description": "Read the contents of a file in the current project.",
    "parameters": {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Path to the file to read.",
            }
        },
        "required": ["filepath"],
        "additionalProperties": False,
    },
}
```

### Using the Second Tool

Now we ask a question that should make the agent inspect project files.

Now we ask a narrower question:

- `What dependencies does this project have?`

To answer it, the model should inspect one of the important project files, most likely `pyproject.toml`.

We will already make both tools available here. The model may only need `read_file`, but we want to keep the setup aligned with the next step.

```python
user_prompt = "What dependencies does this project have?"

chat_messages = [
    {"role": "developer", "content": system_prompt},
    {"role": "user", "content": user_prompt}
]
```

Send the request:

```python
response = openai_client.responses.create(
    model=model,
    input=chat_messages,
    tools=[see_file_tree_description, read_file_description]
)
```

Go through the response and make tool calls:

```python
chat_messages.extend(response.output)

for item in response.output:
    if item.type == 'function_call':
        f_name = item.name
        args = json.loads(item.arguments)
        print(f'tool_call: {f_name}({args})')

        if f_name == 'see_file_tree':
            result = see_file_tree(**args)
        elif f_name == 'read_file':
            result = read_file(**args)
        else:
            raise Exception(f'unknown function {f_name}')

        chat_messages.append({
            "type": "function_call_output",
            "call_id": item.call_id,
            "output": json.dumps(result),
        })
```

See what's inside `chat_messages`:

```python
chat_messages
```

We iterate until we have an answer.

When we have it, we print it:

```python
item = response.output[0]
print(item.content[0].text)
```

Let's put this together:

```python
chat_messages.extend(response.output)

for item in response.output:
    if item.type == 'function_call':
        f_name = item.name
        args = json.loads(item.arguments)
        print(f'tool_call: {f_name}({args})')

        if f_name == 'see_file_tree':
            result = see_file_tree(**args)
        elif f_name == 'read_file':
            result = read_file(**args)
        else:
            raise Exception(f'unknown function {f_name}')

        chat_messages.append({
            "type": "function_call_output",
            "call_id": item.call_id,
            "output": json.dumps(result),
        })
    elif item.type == 'message':
        print(item.content[0].text)
```

### Generalizing to a Loop

In the previous example we manually execute the cells until we get a response. We can replace that with a while loop: we iterate until we have no tool calls.

We can implement it like this:

```python
chat_messages = [
    {"role": "developer", "content": system_prompt},
    {"role": "user", "content": user_prompt}
]

while True:
    response = openai_client.responses.create(
        model=model,
        input=chat_messages,
        tools=[see_file_tree_description, read_file_description]
    )

    has_tool_calls = False

    chat_messages.extend(response.output)

    for item in response.output:
        if item.type == 'function_call':
            has_tool_calls = True

            f_name = item.name
            args = json.loads(item.arguments)
            print(f'tool_call: {f_name}({args})')

            if f_name == 'see_file_tree':
                result = see_file_tree(**args)
            elif f_name == 'read_file':
                result = read_file(**args)
            else:
                raise Exception(f'unknown function {f_name}')

            chat_messages.append({
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": json.dumps(result),
            })
        elif item.type == 'message':
            print(item.content[0].text)

    if not has_tool_calls:
        break
```

The structure is still the same:

1. ask the model
2. inspect `response.output`
3. execute the requested tool
4. append `function_call_output`
5. ask again

### Outer Q&A Loop

What if we want to conitunue the conversation? Let's add input:

```python
chat_messages = [
    {"role": "developer", "content": system_prompt}
]

while True:
    user_prompt = input("You:").strip()

    if user_prompt.lower() == "stop":
        print("Chat ended.")
        break

    chat_messages.append({
        "role": "user",
        "content": user_prompt,
    })

    while True:
        response = openai_client.responses.create(
            model=model,
            input=chat_messages,
            tools=[see_file_tree_description, read_file_description]
        )

        has_tool_calls = False

        for item in response.output:
            chat_messages.append(item)

            if item.type == 'function_call':
                has_tool_calls = True

                f_name = item.name
                args = json.loads(item.arguments)
                print(f'tool_call: {f_name}({args})')

                if f_name == 'see_file_tree':
                    result = see_file_tree(**args)
                elif f_name == 'read_file':
                    result = read_file(**args)
                else:
                    raise Exception(f'unknown function {f_name}')

                chat_messages.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result),
                })
            elif item.type == 'message':
                print(item.content[0].text)

        if not has_tool_calls:
            break
```

Now we have two loops:

1. the inner loop handles tool calls until the model is ready to answer
2. the outer loop keeps the conversation going until the user types `stop`

This is the basic shape of an interactive agent.

Ask: "explore the repo and tell me what you find".


## Part 2: Coding Agent

### Agentic framework

Now we'll use a framework for implementing this agentic loop. Install `toyaikit`:

```bash
uv add toyaikit
```

In Part 1 we wrote the loops ourselves. Now let's port exactly the same idea to `toyaikit`.

```python
from toyaikit.tools import Tools
from toyaikit.chat import IPythonChatInterface
from toyaikit.llm import OpenAIClient
from toyaikit.chat.runners import OpenAIResponsesRunner
```

Register the two tools we already have:

```python
tools_obj = Tools()
tools_obj.add_tool(see_file_tree, see_file_tree_description)
tools_obj.add_tool(read_file, read_file_description)
```

Create the runner:

```python
chat_interface = IPythonChatInterface()
llm_client = OpenAIClient(client=openai_client, model=model)

runner = OpenAIResponsesRunner(
    tools=tools_obj,
    developer_prompt=system_prompt,
    chat_interface=chat_interface,
    llm_client=llm_client
)
```

Run it:

```python
results = runner.run()
```

Type `stop` to end the chat loop.

The important point is that the agent behavior did not change. We only replaced our manual outer and inner loops with a framework that does the same thing for us.

### Tool Definitions from Docstrings

In Part 1 we had to maintain function schemas such as `see_file_tree_description` and `read_file_description`.

That is fine for learning, but it becomes annoying once we have more tools.

With `toyaikit` (or any other agentic framework), if we provide:

- type hints
- docstrings

then we no longer need to write the tool definitions manually. The framework can infer them.

```python
def see_file_tree(root_dir: str = ".") -> list[str]:
    """List files and directories in the current project.

    Args:
        root_dir: Directory to list. Defaults to the current directory.
    """
    tree = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in {".git", ".venv", "__pycache__"}]

        for name in sorted(dirnames + filenames):
            full_path = os.path.join(dirpath, name)
            tree.append(os.path.relpath(full_path, root_dir))

    return tree


def read_file(filepath: str) -> str:
    """Read the contents of a file in the current project.

    Args:
        filepath: Path to the file to read.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()
```

Then we can simply do:

```python
tools_obj = Tools()
tools_obj.add_tool(see_file_tree)
tools_obj.add_tool(read_file)
```

No separate schema dictionary is needed anymore.

### Grouping Tools in a Class

We also want some structure.

For a coding agent, several tools need shared state, especially the project directory they operate on.

Instead of passing many unrelated functions around, we can group them into a class.

Let's start with a small class that contains the tools we already have:

```python
import os
from pathlib import Path

class ProjectTools:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def see_file_tree(self, root_dir: str = ".") -> list[str]:
        """List files and directories in the project.

        Args:
            root_dir: Directory to list relative to the project root.
        """
        abs_root = self.project_dir / root_dir
        tree = []

        for dirpath, dirnames, filenames in os.walk(abs_root):
            dirnames[:] = [d for d in dirnames if d not in {".git", ".venv", "__pycache__"}]

            for name in sorted(dirnames + filenames):
                full_path = os.path.join(dirpath, name)
                tree.append(os.path.relpath(full_path, self.project_dir))

        return tree

    def read_file(self, filepath: str) -> str:
        """Read the contents of a file relative to the project root.

        Args:
            filepath: Path to the file to read.
        """
        abs_path = self.project_dir / filepath
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()

    def search_in_files(self, search_term: str) -> list[str]:
        """Search for a string in project files.

        Args:
            search_term: Text to search for.
        """
        matches = []

        for dirpath, dirnames, filenames in os.walk(self.project_dir):
            dirnames[:] = [d for d in dirnames if d not in {".git", ".venv", "__pycache__"}]

            for filename in filenames:
                abs_path = Path(dirpath) / filename

                try:
                    content = abs_path.read_text(encoding="utf-8")
                except Exception:
                    continue

                if search_term in content:
                    matches.append(str(abs_path.relative_to(self.project_dir)))

        return matches
```

Initialize it for the current repository:

```python
project_tools = ProjectTools(Path("."))
```

Try one of the methods directly:

```python
project_tools.search_in_files("agent")
```

And pass the whole instance to `toyaikit`:

```python
tools_obj = Tools()
tools_obj.add_tools(project_tools)
```

This is already better structured:

- both tools share the same project root
- both tools live in one place
- `toyaikit` can infer schemas from the method signatures and docstrings

### Full Tool Class

For the actual coding agent, we want more than just `see_file_tree` and `read_file`.

We already have a ready implementation here:

- [`coding-agent/tools.py`](../coding-agent/tools.py)

Download a local copy:

```bash
wget https://raw.githubusercontent.com/alexeygrigorev/workshops/refs/heads/main/coding-agent/tools.py
```

These are going to be our tools:

1. `read_file` - read a file relative to the project directory
2. `write_file` - write a file and create missing directories if needed
3. `see_file_tree` - list the project files while skipping noisy folders such as `.git` and `.venv`
4. `execute_bash_command` - run shell commands in the project directory
5. `search_in_files` - search for text inside project files

Now use this class in the current repository:

```python
import tools
agent_tools = tools.AgentTools(Path("."))

tools_obj = Tools()
tools_obj.add_tools(agent_tools)
```

Test it:

```python
project_tools.search_in_files('agent')
```

Let's create an agent for it:

```python
chat_interface = IPythonChatInterface()
llm_client = OpenAIClient(client=openai_client, model=model)

runner = OpenAIResponsesRunner(
    tools=tools_obj,
    developer_prompt=system_prompt,
    chat_interface=chat_interface,
    llm_client=llm_client
)
```

Run it:

```python
runner.run();
```

Test it with a prompt: "create a browser based vanilla js snake game in snake.html".


## Part 3: Template

### Structure and Constraints

Now we can talk about the actual coding-agent project.

We do not want the agent to work in a completely unconstrained environment. If we just say "build me an app" with no structure, the agent has to invent:

- which framework to use
- where files should go
- how the app is organized
- how to run it
- how to verify it

That makes the task slower and less reliable.

A template gives the agent constraints and structure:

- the file tree is already there
- the framework is already chosen
- the important files already exist
- there is a known place for HTML, views, settings, and URLs

This helps the agent work faster because it spends less time inventing structure and more time modifying the existing project correctly.

### Adding Django

We will use a prepared Django template project:

```bash
git clone https://github.com/alexeygrigorev/django_template.git
```

If you want to make sure the template works before using it with the agent, run it once:

```bash
cd django_template
uv sync
make migrate
make run
```

Create a helper that copies the template into a new project folder:

```python
import os
import shutil


def start(project_name):
    if not project_name:
        print("Project name cannot be empty.")
        return

    if os.path.exists(project_name):
        print(f"Directory '{project_name}' already exists.")
        return

    shutil.copytree("django_template", project_name)
    print(f"Django template copied to '{project_name}' directory.")
    return project_name
```

Use it:

```python
project_name = input("Enter the new Django project name: ").strip()
start(project_name)
```

Now point the same tool class at the new Django project:

```python
project_path = Path(project_name)
agent_tools = tools.AgentTools(project_path)
```

### A More Detailed Prompt

To make it work better, we need a stronger prompt than the exploratory prompt from Part 1:

```python
djago_agent_prompt = """
You are a coding agent. Your task is to modify the provided Django project template
according to user instructions. You don't tell the user what to do; you do it yourself using the
available tools. First, think about the sequence of steps you will do, and then
execute the sequence.
Always ensure changes are consistent with Django best practices and the project's structure.

## Project Overview

The project is a Django 5.2.4 web application scaffolded with standard best practices. It uses:
- Python 3.12+
- Django 5.2.4 (as specified in pyproject.toml)
- uv for Python environment and dependency management
- SQLite as the default database (see settings.py)
- Standard Django apps and a custom app called myapp
- HTML templates for rendering views
- TailwindCSS for styling

## File Tree

├── .python-version
├── README.md
├── manage.py
├── pyproject.toml
├── uv.lock
├── myapp/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   │   └── __init__.py
│   ├── models.py
│   ├── templates/
│   │   └── home.html
│   ├── tests.py
│   └── views.py
├── myproject/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── templates/
    └── base.html

## Content Description

- manage.py: Standard Django management script for running commands.
- README.md: Setup and run instructions, including use of uv for dependency management.
- pyproject.toml: Project metadata and dependencies (Django 5.2.4).
- uv.lock: Lock file for reproducible Python environments.
- .python-version: Specifies the Python version for the project.
- myapp/: Custom Django app with models, views, admin, tests, and a template (home.html).
  - migrations/: Contains migration files for database schema.
- myproject/: Django project configuration (settings, URLs, WSGI/ASGI entrypoints).
  - settings.py: Configures installed apps, middleware, database (SQLite), templates, etc.
- templates/: Project-level templates, including base.html.

You have full access to modify, add, or remove files and code within this structure using your available tools.

## Additional instructions

- Don't execute "runserver", but you can execute other commands to check if the project is working.
- Make sure you use Tailwind styles for making the result look beatiful
- Use pictograms and emojis when possible. Font-awesome is awailable
- Avoid putting complex logic to templates - do it on the server side when possible
""".strip()
```

### Running the Coding Agent

Now run the agent with the full tool class:

```python
tools_obj = Tools()
tools_obj.add_tools(agent_tools)

chat_interface = IPythonChatInterface()
llm_client = OpenAIClient(client=openai_client, model=model)

runner = OpenAIResponsesRunner(
    tools=tools_obj,
    developer_prompt=djago_agent_prompt,
    chat_interface=chat_interface,
    llm_client=llm_client
)

runner.run()
```

Type `stop` to end the chat loop.

Now we have a real coding agent:

- it works inside a structured project
- it has multiple project-aware tools
- it has a more specific prompt
- and the framework handles the agentic loop for us


## Part 3: Skills

Now we extend the same coding agent with skills.

Skills are reusable instruction files that teach the agent how to handle a specific kind of task.

Instead of putting every possible workflow into one long system prompt, we keep the base agent smaller and let it load extra instructions only when they are relevant.

This matters for two reasons:

- the agent stays simpler and easier to control
- we can add new capabilities without rewriting the whole agent

In this part, we will keep the coding agent from Part 2 and add a tool that can load `SKILL.md` files on demand.

For loading `SKILL.md` files with frontmatter, install:

```bash
uv add python-frontmatter
```

First, create a skills folder and download the example GitHub-fetch skill:

```bash
mkdir -p skills/gh-fetch
wget https://raw.githubusercontent.com/alexeygrigorev/workshops/refs/heads/main/agent-skills/gh-fetch-skill.md -O skills/gh-fetch/SKILL.md
```

Create a data class for skills:

```python
from dataclasses import dataclass
from pathlib import Path
import frontmatter


@dataclass
class Skill:
    name: str
    description: str
    content: str
```

Now the loader:

The skills live as files on disk, but the agent needs a structured way to work with them.

That is why we need a loader. It does three things:

- given a skill name, it reads `skills/<name>/SKILL.md`
- it lists all available skills in the `skills/` folder
- it prepares a short description of the available skills so we can tell the agent what it can load

```python
class SkillLoader:

    def __init__(self, skills_dir: Path | str = None):
        self.skills_dir = Path(skills_dir)

    def load_skill(self, name: str) -> Skill | None:
        skill_file = self.skills_dir / name / "SKILL.md"
        if not skill_file.exists():
            return None

        parsed = frontmatter.load(skill_file)

        return Skill(
            name=parsed.metadata.get("name", name),
            description=parsed.metadata.get("description", ""),
            content=parsed.content,
        )

    def list_skills(self) -> list[Skill]:
        skills = []

        if not self.skills_dir.exists():
            return skills

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            skill = self.load_skill(skill_dir.name)
            if skill:
                skills.append(skill)

        return skills

    def get_description(self) -> str:
        skills = self.list_skills()

        skills_listing = "\n".join(
            f"  - {s.name}: {s.description}"
            for s in skills
        )

        return skills_listing
```

Expose skills as a tool:

The loader is a normal Python object, but the model cannot call Python methods directly.

It only knows how to call tools that are registered in the agent.

So if we want the agent to decide on its own when to load a skill, the skill loader has to be exposed as a tool. Then the model can do this flow itself:

- see from the prompt that some skills are available
- decide that one of them is relevant
- call the `skill` tool with the skill name
- read the returned instructions and continue the task

```python
class SkillsTool:
    """Wrapper for the skill loader that exposes skill() as a tool."""

    def __init__(self, skill_loader: SkillLoader):
        self.skill_loader = skill_loader

    def skill(self, name: str) -> dict:
        """Load a skill to get specialized instructions."""
        result = self.skill_loader.load_skill(name)
        return {
            "name": result.name,
            "description": result.description,
            "content": result.content,
        }
```

For the skills-based agent, we switch to the general-purpose system prompt from the skills workshop:

```python
AGENT_INSTRUCTIONS = """You are a coding agent designed to help with software engineering tasks.

You help users with:
- Writing, editing, and refactoring code
- Debugging and fixing errors
- Explaining code and technical concepts
- Project setup and configuration
- Code reviews and best practices

Your task is to use the available tools to satisfy the requests from the user.

When user asks to implement something, or create something, create and modify the files
using the provided tools. Use your best judgment when deciding how to name files and folders.

# Core Principles

1. Be concise but thorough - Get straight to the point, but don't skip important details
2. Show your work - Explain your reasoning for complex changes
3. Ask questions - When requirements are unclear, ask rather than assume
4. Use tools effectively - ALWAYS use available tools when relevant
5. Code quality matters - Write clean, maintainable code following best practices

# Working with Code

- Prefer editing over creating new files when possible
- Read before writing - Understand existing patterns before making changes
- Test your changes - Run builds/tests and fix any errors you introduce
- Reference precisely - When pointing to code, use file_path:line_number format

You're here to help users build better software efficiently. Start by understanding what they want to accomplish!
""".strip()
```

Initialize the skill loader and inject the available skills into that prompt:

```python
skill_loader = SkillLoader(Path("skills/"))
skills_tool = SkillsTool(skill_loader)

SKILL_INJECTION_PROMPT = f'''
You have the following skills available which you can load with the skills tool:

{skill_loader.get_description()}
'''.strip()

AGENT_WITH_SKILLS_INSTRUCTIONS = AGENT_INSTRUCTIONS + '\n\n' + SKILL_INJECTION_PROMPT
```

Before we add the skills tool, let's create a fresh project folder and point the coding-agent tools to it:

```python
skills_project_name = input("Enter the project name for the skills agent: ").strip()
start(skills_project_name)

project_path = Path(skills_project_name)
agent_tools = tools.AgentTools(project_path)

tools_obj = Tools()
tools_obj.add_tools(agent_tools)
tools_obj.add_tools(skills_tool)
```

Run the updated agent:

```python
runner = OpenAIResponsesRunner(
    tools=tools_obj,
    developer_prompt=AGENT_WITH_SKILLS_INSTRUCTIONS,
    llm_client=llm_client,
    chat_interface=chat_interface,
)

runner.run();
```

Type `stop` to end the chat loop.

Try it with:

```text
Create a browser-based todo app in this project. First fetch coding-agent-v2/vanilla-todo-reference/README.md from alexeygrigorev/workshops, save it under references/, read the instructions there, and then implement the app here using vanilla JavaScript, HTML, and localStorage.
```

At this point, we still have the same coding agent as before, but now it can load skills.


## Part 4: PydanticAI

The last step is to run the same agent with PydanticAI.

For this part, install PydanticAI:

```bash
uv add pydantic-ai
```

The important point is that we keep the same tools and the same prompt. We only change the orchestration layer.

```python
from pydantic_ai import Agent
from toyaikit.tools import get_instance_methods
from toyaikit.chat import IPythonChatInterface
from toyaikit.chat.runners import PydanticAIRunner
```

Collect the same tools:

```python
coding_agent_tools_list = (
    get_instance_methods(agent_tools)
    + get_instance_methods(skills_tool)
)
```

Define the agent:

```python
pydantic_model = 'openai:gpt-5.4-mini'

coding_agent = Agent(
    pydantic_model,
    instructions=AGENT_WITH_SKILLS_INSTRUCTIONS,
    tools=coding_agent_tools_list
)
```

And run it:

```python
chat_interface = IPythonChatInterface()

runner = PydanticAIRunner(
    chat_interface=chat_interface,
    agent=coding_agent
)

await runner.run()
```

Type `stop` to end the chat loop.

This is the same coding agent, now running with PydanticAI instead of the earlier `toyaikit` OpenAI runner.


## Summary

`coding-agent-v2` should be presented as the updated `coding-agent` workshop with skills capabilities:

1. tool calls intro
2. coding agent
3. skills
4. PydanticAI

This README contains the code needed to follow along in one place, while still reusing a few larger files where that is more practical.
