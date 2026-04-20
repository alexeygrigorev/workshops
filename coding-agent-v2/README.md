# Coding Agent v2

In this workshop, we are going to implement a coding agent that has skills.

Plan:

1. Start with a short introduction to tool calling
2. Build the coding agent itself
3. Add skills and commands
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
uv add jupyter
```

Start Jupyter:

```bash
uv run jupyter notebook
```

### OpenAI openai_client setup

For the API examples in the next part, install the OpenAI SDK:

```bash
uv add openai
```

We will use these two variables throughout the OpenAI SDK sections of the workshop:

```python
from openai import OpenAI

openai_client = OpenAI()
model = 'gpt-4o-mini'
```

### Optional: Groq with the OpenAI SDK

If you want to use Groq instead, keep the same variable names and switch the openai_client and model:

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

Question:

- `Explain what do we have in this folder.`

### Without Tools

First, let's ask the model a question without any tools:

```python
system_prompt = "You are a helpful coding assistant."
user_prompt = "Explain what do we have in this folder."

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

Prepare the request.

First, prepare the prompt and the messages:

```python
system_prompt = "You are a helpful coding assistant. Use the project-inspection tools when you need to understand the codebase."

chat_messages = [
    {"role": "developer", "content": system_prompt},
    {"role": "user", "content": "Explain what do we have in this folder."}
]
```

Send the request with the tool available.

Now call the model and tell it that `see_file_tree` is available:

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

Start by rebuilding the message history and adding the model's tool call:

```python
messages = [
    {"role": "developer", "content": system_prompt},
    {"role": "user", "content": "Explain what do we have in this folder."}
]

messages.extend(response.output)
```

Now append the tool result as `function_call_output`:

```python
messages.append({
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
    input=messages,
    tools=[see_file_tree_description]
)
```

And now we can read the final text answer:

```python
print(response.output_text)
```

This already gives the model access to the project tree, but it still cannot inspect file contents.

### Adding the Second Tool

If we want the model to go beyond the directory tree and inspect actual files, we need another tool.

Define `read_file`.

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

### Using Both Tools

Now the model can first inspect the tree and then read important files such as `pyproject.toml` or `README.md`.

Send the request with both tools.

```python
chat_messages = [
    {"role": "developer", "content": system_prompt},
    {"role": "user", "content": "Explain what do we have in this folder."}
]
```

```python
response = openai_client.responses.create(
    model=model,
    input=chat_messages,
    tools=[see_file_tree_description, read_file_description]
)
```

Inspect the returned items.

```python
response.output
```

At this stage, the model may decide to:

- call `see_file_tree`
- call `read_file`
- call `see_file_tree` first and `read_file` after that

Let's first handle one tool call manually.

### One Tool Call Round-Trip

If the LLM decided to invoke one of our functions, we need to execute it and send the result back.

Remember, LLMs are stateless. They do not remember previous requests, so we have to maintain the conversation history ourselves.

First, add the LLM's response to our messages:

```python
import json

messages = [
    {"role": "developer", "content": system_prompt},
    {"role": "user", "content": "Explain what do we have in this folder."}
]

messages.extend(response.output)
```

Then execute the function and append the result:

```python
call = response.output[0]
args = json.loads(call.arguments)

if call.name == 'see_file_tree':
    result = see_file_tree(**args)
elif call.name == 'read_file':
    result = read_file(**args)
else:
    result = {"error": f"Unknown tool: {call.name}"}

result_json = json.dumps(result, indent=2)

messages.append({
    "type": "function_call_output",
    "call_id": call.call_id,
    "output": result_json,
})
```

Now invoke the model again with the tool result:

```python
response = openai_client.responses.create(
    model=model,
    input=messages,
    tools=[see_file_tree_description, read_file_description]
)

print(response.output_text)
```

This handles one tool call. But what if the model needs to call multiple tools? After seeing the result of one tool call, it may decide to call another tool, or even the same tool again with different parameters.

### Tool-Calling Loop

This is why we need a loop. We keep calling the API until there are no more tool calls.

```python
messages = [
    {"role": "developer", "content": system_prompt},
    {"role": "user", "content": "Explain what do we have in this folder."}
]

while True:
    response = openai_client.responses.create(
        model=model,
        input=messages,
        tools=[see_file_tree_description, read_file_description]
    )

    has_tool_calls = False

    for entry in response.output:
        messages.append(entry)

        if entry.type == 'function_call':
            args = json.loads(entry.arguments)

            if entry.name == 'see_file_tree':
                result = see_file_tree(**args)
            elif entry.name == 'read_file':
                result = read_file(**args)
            else:
                result = {"error": f"Unknown tool: {entry.name}"}

            result_json = json.dumps(result, indent=2)

            messages.append({
                "type": "function_call_output",
                "call_id": entry.call_id,
                "output": result_json,
            })
            has_tool_calls = True

        elif entry.type == 'message':
            print(entry.content[0].text)

    if not has_tool_calls:
        break
```

This is the tool-calling loop. Every agent framework implements this internally.

## Part 2: Coding Agent

Now we build the same coding agent as in [coding-agent](../coding-agent/).

For this part, install `toyaikit`:

```bash
uv add toyaikit
```

First, get the Django template:

```bash
git clone https://github.com/alexeygrigorev/django_template.git
```

The large tool file already exists in this repo, so we reuse it instead of rewriting it:

- [`../coding-agent/tools.py`](../coding-agent/tools.py)

Download a local copy:

```bash
wget https://raw.githubusercontent.com/alexeygrigorev/workshops/refs/heads/main/coding-agent/tools.py
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

    shutil.copytree('django_template', project_name)
    print(f"Django template copied to '{project_name}' directory.")
    return project_name
```

Use it:

```python
project_name = input("Enter the new Django project name: ").strip()
start(project_name)
```

In Part 1 we used standalone functions. That is fine for a small example, but for a coding agent we need multiple tools that all work relative to the same project directory.

So instead of passing around many independent functions, we will group them into a class.

The idea looks like this:

```python
from pathlib import Path


class AgentTools:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
```

This gives us one place to store shared state such as the project root, and all tool methods can use it.

For this workshop, we will not re-implement the whole class in the notebook. We already have it here:

- [tools.py](/home/alexey/git/workshops/coding-agent/tools.py:1)

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

Now initialize the class:

```python
import tools
from pathlib import Path

project_path = Path(project_name)
agent_tools = tools.AgentTools(project_path)
```

At this point, `agent_tools` is one object that contains all the methods we want to expose to the agent.

Start with the same simple coding-agent prompt:

```python
DEVELOPER_PROMPT = """
You are a coding agent. Your task is to modify the provided
Django project template according to user instructions.
"""
```

### Using a Framework

With [`toyaikit`](https://github.com/alexeygrigorev/toyaikit), we can pass the entire class instance instead of registering each tool one by one.

Now run the agent with `toyaikit`:

```python
from toyaikit.tools import Tools
from toyaikit.chat import IPythonChatInterface
from toyaikit.llm import OpenAIopenai_Client
from toyaikit.chat.runners import OpenAIResponsesRunner

tools_obj = Tools()
tools_obj.add_tools(agent_tools)

chat_interface = IPythonChatInterface()
llm_openai_client = OpenAIopenai_Client(openai_client=openai_client, model=model)

runner = OpenAIResponsesRunner(
    tools=tools_obj,
    developer_prompt=DEVELOPER_PROMPT,
    chat_interface=chat_interface,
    llm_openai_client=llm_openai_client
)

runner.run()
```

This is the same coding-agent foundation as before. We do not change the architecture here.


## Part 3: Skills

Now we extend the same coding agent with the skills capabilities from [agent-skills](../agent-skills/).

For loading `SKILL.md` and command files with frontmatter, install:

```bash
uv add python-frontmatter
```

We will keep the agent from Part 2 and add two things:

- skills
- commands

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

Initialize it and inject the available skills into the prompt:

```python
skill_loader = SkillLoader(Path("skills/"))
skills_tool = SkillsTool(skill_loader)

SKILL_INJECTION_PROMPT = f'''
You have the following skills available which you can load with the skills tool:

{skill_loader.get_description()}
'''.strip()

AGENT_WITH_SKILLS_INSTRUCTIONS = DEVELOPER_PROMPT + '\n\n' + SKILL_INJECTION_PROMPT
```

Add the tool:

```python
tools_obj.add_tools(skills_tool)
```

### Commands

Commands are user-facing shortcuts. We keep the same approach as in [agent-skills](../agent-skills/).

Create the commands folder and download the example commands:

```bash
mkdir commands
cd commands

wget https://raw.githubusercontent.com/alexeygrigorev/claude-code-kid-parent/refs/heads/main/.claude/commands/kid.md
wget https://raw.githubusercontent.com/alexeygrigorev/claude-code-kid-parent/refs/heads/main/.claude/commands/parent.md

cd ..
```

Create a data class for commands:

```python
@dataclass
class Command:
    name: str
    description: str
    template: str
```

And the loader:

```python
class CommandLoader:
    def __init__(self, commands_dir: Path | str = None):
        self.commands_dir = Path(commands_dir)

    def load_command(self, name: str) -> Command:
        command_file = self.commands_dir / f"{name}.md"
        if not command_file.exists():
            return None

        parsed = frontmatter.load(command_file, encoding="utf-8")
        metadata = dict(parsed.metadata)

        return Command(
            name=name,
            description=metadata.get("description", ""),
            template=parsed.content,
        )

    def list_commands(self) -> list[Command]:
        commands = []

        if not self.commands_dir.exists():
            return commands

        for md_file in sorted(self.commands_dir.glob("*.md")):
            name = md_file.stem
            command = self.load_command(name)
            commands.append(command)

        return commands
```

Wrap commands as a tool:

```python
def process_template(template: str, arguments: str) -> str:
    return template


class CommandsTool:
    def __init__(self, command_loader: CommandLoader):
        self.command_loader = command_loader

    def execute_command(self, name: str, arguments: str = "") -> str:
        """Execute a command by name and return the rendered prompt."""
        if name.startswith('/'):
            name = name.lstrip('/')

        command = self.command_loader.load_command(name)
        if not command:
            return f"Command not found: /{name}"

        return process_template(command.template, arguments)
```

Initialize and register:

```python
command_loader = CommandLoader(Path("commands/"))
commands_tool = CommandsTool(command_loader=command_loader)

tools_obj.add_tools(commands_tool)
```

Update the prompt so the agent knows the difference between skills and commands:

```python
SKILL_INJECTION_PROMPT = f'''
You have the following skills available which you can load with the skills tool:

{skill_loader.get_description()}

Don't confuse skills and commands:

- Skills are discovered automatically, without user explicitly asking for it
- Instructions to execute commands are given explicitly: "/test" -> "run the 'test' command"

When you see "/command", use the tools to execute the command "command"
'''.strip()

AGENT_WITH_SKILLS_INSTRUCTIONS = DEVELOPER_PROMPT + '\n\n' + SKILL_INJECTION_PROMPT
```

Run the updated agent:

```python
runner = OpenAIResponsesRunner(
    tools=tools_obj,
    developer_prompt=AGENT_WITH_SKILLS_INSTRUCTIONS,
    llm_openai_client=llm_openai_client,
    chat_interface=chat_interface,
)

runner.run()
```

At this point, we still have the same coding agent as before, but now it can load skills and execute commands.


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
    + get_instance_methods(commands_tool)
)
```

Define the agent:

```python
pydantic_model = 'openai:gpt-4o-mini'

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

This is the same coding agent, now running with PydanticAI instead of the earlier `toyaikit` OpenAI runner.


## Summary

`coding-agent-v2` should be presented as the updated `coding-agent` workshop with skills capabilities:

1. tool calls intro
2. coding agent
3. skills
4. PydanticAI

The stack stays the same as in the earlier workshops, the code stays close to the original versions, and the README contains the code needed to follow along without jumping between multiple workshop folders.
