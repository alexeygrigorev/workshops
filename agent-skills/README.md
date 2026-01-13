# Coding Agent with Skills and Commands

This workshop builds on the [Create a Coding Agent](../coding-agent/) workshop.

We extend the agent we built there: we turn it into a general-purpose coding agent and add skills and commands:

1. Skills - Modular capabilities that agents load autonomously
2. Commands - User-facing shortcuts for common tasks

If you used Claude Code, you might have come across them already. 

For this workshop, I analyzed the source code of [Open Code](https://github.com/anomalyco/opencode) (Claude Code open-source alternative).

I will tell you how they are implemented there, and we together will implement them in Python.


## Prerequisites

- Python 3.10+
- Jupyter
- OpenAI API key (or Anthropic/Groq/Z.ai as alternatives)

GitHub Codespaces is recommended (see the [coding-agent workshop](../coding-agent/)), but any environment with Jupyter works.

This workshop assumes you're familiar with agents and tool use. For a refresher, see these workshops:

- [agents-mcp/](../agents-mcp/) - Introduction to agents and MCP
- [coding-agent/](../coding-agent/) - Building your first coding agent

We will do a quick recap, but if you feel lost during this session,I recommend checking the pre-requisite workshops first and then come back here.


## Skills and Commands

* Skills are modular behavior packages that agents can load on-demand
* Commands are user-facing shortcuts for common tasks


### Demo

In this demo we will create a skill for getting files from GitHub. We will use it to get two commands:

- [/kid](https://raw.githubusercontent.com/alexeygrigorev/claude-code-kid-parent/refs/heads/main/.claude/commands/kid.md)
- [/parent](https://raw.githubusercontent.com/alexeygrigorev/claude-code-kid-parent/refs/heads/main/.claude/commands/parent.md)

from the [claude-code-kid-parent](https://github.com/alexeygrigorev/claude-code-kid-parent) repo.

I'll use Claude Code to show you how skills and commands work. You don't need to follow along, I just want to show you how it works.

The skill is here: [gh-fetch-skill.md](gh-fetch-skill.md).

We will craete another folder - `demo`:

```bash
mkdir demo
cd demo

wget https://raw.githubusercontent.com/alexeygrigorev/workshops/refs/heads/main/agent-skills/gh-fetch-skill.md

mkdir -p .claude/skills/gh-fetch
mv gh-fetch-skill.md .claude/skills/gh-fetch/SKILL.md
```

Start claude code:

```bash
claude
```

Ask Claude to download the commands 

```
get files kid and parent commands from
https://github.com/alexeygrigorev/claude-code-kid-parent
save them to .claude/commands/
```

restart claude and continue it:


```
claude -c
```

Now run `/kid` and then `/parent`. The kid will come up with a crazy project idea and the parent will implement it in HTML+JS.


### Skills

What happens when we want to use skills?

Here's the flow from our demo:

- User: "get files kid and parent commands from alexeygrigorev/claude-code-kid-parent"
- Agent: Sees "gh-fetch: Fetch and save files from GitHub repos" in available skills
- Agent: Calls `skill({name: "gh-fetch"})`
- Agent: Receives skill instructions with gh commands
- Agent: Fetches and saves the files

The agent automatically decides which skill to use. Users don't say "use the gh-fetch skill" - they just say what they want.

### Commands

Commands are user-facing shortcuts. From our demo:

- User: `/kid`
- System detects leading `/`
- System looks up the kid.md command
- Agent receives rendered prompt with kid instructions
- Agent acts as a kid asking for a crazy coding project

The agent never sees the `/kid` syntax - only the rendered prompt.


## Environment Preparation

Create a separate folder:

```bash
mkdir code
cd code
```

Initialize the project and install all the dependencies:

```bash
pip install uv
uv init
uv add jupyter openai toyaikit python-frontmatter
```

Add your OpenAI key in `.env`:

```
OPENAI_API_KEY='your-key'
```

Make sure `.env` is in `.gitignore`:

```bash
echo .env >> .gitignore
```

I use `dirdotenv` to get access to the env variables from `.env` and `.envrc` to my terminal:

```bash
pip install dirdotenv
echo 'eval "$(dirdotenv hook bash)"' >> ~/.bashrc
```

Start the notebook:

```bash
uv run jupyter notebook
```

## Quick Recap

### What is an Agent?

By now you've seen agents in previous workshops ([agents-mcp/](../agents-mcp/) and [coding-agent/](../coding-agent/)). Let's briefly recap the core concepts.

An agent consists of four components:

* Model - The LLM, the "brain" that reasons and decides
* System prompt - Instructions that define the agent's behavior and role
* Tools - Functions the agent can call to interact with the world
* Memory - Message history that provides context from previous turns

How it works:

* User gives input
* Agent sees: input + system prompt + available tools + memory
* Agent decides: respond OR call a tool
* If tool call: execute, add result to memory, loop
* When done: send final response

The agent autonomously decides which tools to use and in what order - no hard-coded sequences.

Example:

```
User: "Fix the bug in calculator.py"

LLM: I'll read the file first.
→ Tool: read_file("calculator.py")

LLM: Found the issue. I'll fix it.
→ Tool: write_file("calculator.py", fixed_code)

LLM: Let me verify the fix works.
→ Tool: execute_bash("pytest")

LLM: "Fixed! Added a check for division by zero."
```

### The Coding Agent Tools

In the [coding-agent](../coding-agent/) workshop, we built a coding agent with five core tools:

```python
class AgentTools:
    def read_file(self, filepath: str) -> str
        """Read the contents of a file."""

    def write_file(self, filepath: str, content: str) -> None
        """Write content to a file."""

    def see_file_tree(self, root_dir: str = ".") -> list[str]
        """List all files in a directory."""

    def execute_bash_command(self, command: str, cwd: str = None) -> tuple[str, str, int]
        """Run a shell command."""

    def search_in_files(self, pattern: str, root_dir: str = ".") -> list[tuple[str, int, str]]
        """Search for text in files."""
```

Source: [coding-agent/tools.py](../coding-agent/tools.py)

With these tools, the agent can:
- Read existing code
- Make changes by writing files
- Run commands to test
- Search for relevant code

These tools are generic, and will work with any coding agent. We will use these tools in this project too, so let's download them:

```bash
wget https://raw.githubusercontent.com/alexeygrigorev/workshops/refs/heads/main/coding-agent/tools.py
```

## General-Purpose Agent

Let's start implementing the agent. We'll use [`toyaikit`](https://github.com/alexeygrigorev/toyaikit) - a small library for orchestrating agents with tools. It handles the tool calling loop so we don't have to. This library is useful for workshops, because we can see all the interactions between the agent and the tools, but in practice you probably want to use a library like PydanticAI.  


For us the agent is:

* The model - we'll use OpenAI gpt-4o-mini
* The tools - we'll use the tools from the previous workshop
* The instructions (the system prompt) - we'll have to adjust it

### Tools

First, create a project folder where the agent will work:

```python
from pathlib import Path

project_path = Path('test-project')
project_path.mkdir(exist_ok=True)
```

Initialize the agent tools with the project path:

```python
import tools

agent_tools = tools.AgentTools(project_path)

# we can use it now:
agent_tools.see_file_tree()
```

Create a `Tools` object and add the agent tools to it:

```python
from toyaikit.tools import Tools

tools_obj = Tools()
tools_obj.add_tools(agent_tools)
```

Now `tools_obj.get_tools()` returns all the tools in the OpenAI responses format.


### Instructions

We set up the tools. Now let's set up the instructions..

The Django agent from the previous workshop has [a very detailed prompt](https://github.com/alexeygrigorev/workshops/blob/main/coding-agent/README.md#L384). But for a general-purpose agent, we need a general-purpose prompt.

Since I used [OpenCode](https://github.com/anomalyco/opencode) as the reference implementation of a coding agent, I thought we can take [theirs](https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/session/prompt/anthropic.txt). 

But it's fairly large, so let's simplify it:

```python
AGENT_INSTRUCTIONS = """You are a coding agent designed to help with software engineering tasks.

You help users with:
- Writing, editing, and refactoring code
- Debugging and fixing errors
- Explaining code and technical concepts
- Project setup and configuration
- Code reviews and best practices


Your task is to use the available tools to satisfy the requests from the user.

When user asks to implement something, or create something, create and modiry the files
using the provided tools. Use your best judgement when deciding how to name files and folders.

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

### Agent

Now we set up the rest of the Agent. Start with the OpenAI client:

```python
from openai import OpenAI
from toyaikit.llm import OpenAIClient

llm_client = OpenAIClient(client=OpenAI())
```

Create the chat interface for Jupyter and the runner (our agent):

```python
from toyaikit.chat import IPythonChatInterface
from toyaikit.chat.runners import OpenAIResponsesRunner

chat_interface = IPythonChatInterface()

runner = OpenAIResponsesRunner(
    tools=tools_obj,
    developer_prompt=AGENT_INSTRUCTIONS,
    llm_client=llm_client,
    chat_interface=chat_interface,
)
```

Run the agent:

```python
result = runner.run()
```

Prompt:

```
create a python script for calculating the sum of all the numbers passed as input

...

let's run it
```

To see the cost of these requests, run 

```python
result.cost
```

## Implementing Skills

Now we want to add skills to this agent.

We'll create a simple skill `hello`:

```markdown
---
name: hello
description: Skill for ALL greeting requests
---

# Hello Skill

This skill provides the greeting format you must follow.

## How to greet

Always greet the user with:
- A warm welcome
- Their name if mentioned
- A friendly emoji

## Example greetings

- "Hello! Welcome! How can I help you today? 👋"
- "Hi there! Great to see you! 😊"
```

In the [`skills`](skills/) folder we have a few other examples:

TODO: bullet point list + deescription + /SKILL.md
[text](skills/coding_standards) [text](skills/counter) [text](skills/deploy_app) [text](skills/hello) [text](skills/joke)


### Skills Loader

We need to iterate over the folders in the skills director and load the skills.

Let's start with definining a data class for the skills:

```python
from dataclasses import dataclass

@dataclass
class Skill:
    name: str
    description: str
    content: str
```

Reading a skill:


```python
import frontmatter

skills_dir = Path('../skills/')

def load_skill(name: str) -> Skill | None:
    skill_file = skills_dir / name / "SKILL.md"
    if not skill_file.exists():
        return None
    
    parsed = frontmatter.load(skill_file)
    
    return Skill(
        name=parsed.metadata.get("name", name),
        description=parsed.metadata.get("description", ""),
        content=parsed.content,
    )
```

Listing all the skills:

```python
def list_skills() -> list[Skill]:
    """List all available skills."""
    skills = []

    if not skills_dir.exists():
        return skills

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill = load_skill(skill_dir.name)
        if skill:
            skills.append(skill)

    return skills
```

Now let's put everything together in a class `SkillLoader`:


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

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            skill = self.load_skill(skill_dir.name)
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

Use it:

```python
skill_loader = SkillLoader(skills_dir)
skill_loader.load_skill('hello')
skill_loader.get_description()
```

### The Skill Tool

Now we need to make this available as a tool for the agent. 

But we also need to let the agent know which skills are available. We will do this by modifying the instructions:


```python
SKILL_INJECTION_PROMPT = f'''
You have the following skills available which you can load with the skills tool:

{skill_loader.get_description()}
'''.strip()

AGENT_WITH_SKILLS_INSTRUCTIONS = AGENT_INSTRUCTIONS + '\n\n' + SKILL_INJECTION_PROMPT
```

Note: OpenCode does it differently. It doesn't modify the system prompt, 
and instead the list of skills is injected as the tool description. 
In my experiments this approach didn't work, so I decided to add this to
the instructions directly.

Now let's create the tool (TODO implement):

```python
class SkillsTool:

    def __init__(self, skill_loader):
        ...

    def skill(...):
        # todo add detailed description - check in prototype
        ...
```

```python
skill_tool = ...
tools_obj.add_tools(skill_tool)
```

The agent now has access to the `skill()` method. When the agent needs specialized instructions, it can call `skill({name: "skill_name"})` to load them.



## Implementing Commands

### COMMAND.md Format

Commands are markdown files with YAML frontmatter:

```markdown
---
description: Review code for quality
---

Review the code at $1 for:
1. Code quality and readability
2. Potential bugs
3. Performance issues
4. Best practices violations

Focus on: $ARGUMENTS
```

### Placeholders

Commands support these placeholders:

- `$1`, `$2`, `$3` - Positional arguments
- `$ARGUMENTS` - All arguments

### Directory Structure

```
commands/
├── test.md
├── review.md
└── explain.md
```

### Creating the Commands Module

Create `src/commands.py` with the command discovery and execution code:

```python
# src/commands.py
"""Command discovery and execution system."""

import frontmatter
import re
import shlex
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommandInfo:
    """Information about a command."""
    name: str
    description: str
    template: str


class CommandLoader:
    """Discovers and loads commands from a directory."""

    def __init__(self, commands_dir: Path | str = None):
        """Initialize the command loader."""
        if commands_dir is None:
            commands_dir = Path("commands")
        self.commands_dir = Path(commands_dir)

    def get(self, name: str) -> CommandInfo | None:
        """Get a command by name."""
        command_file = self.commands_dir / f"{name}.md"
        if not command_file.exists():
            return None

        with open(command_file, "r", encoding="utf-8") as f:
            content = f.read()

        parsed = frontmatter.loads(content)
        metadata = dict(parsed.metadata)
        body = parsed.content

        return CommandInfo(
            name=name,
            description=metadata.get("description", ""),
            template=body,
        )

    def list(self) -> list[CommandInfo]:
        """List all available commands."""
        commands = []

        if not self.commands_dir.exists():
            return commands

        for md_file in sorted(self.commands_dir.glob("*.md")):
            name = md_file.stem
            command = self.get(name)
            if command:
                commands.append(command)

        return commands


def process_template(template: str, arguments: str) -> str:
    """Process command template with argument substitution."""
    args = shlex.split(arguments) if arguments else []

    # Find all positional placeholders ($1, $2, etc.)
    placeholder_regex = re.compile(r'\$(\d+)')
    placeholders = placeholder_regex.findall(template)
    last = int(placeholders[-1]) if placeholders else 0

    def replace_placeholder(match):
        index = int(match.group(1)) - 1
        if index >= len(args):
            return ""
        # Last placeholder gets all remaining args
        if match.group(1) == str(last) and len(args) > index + 1:
            return " ".join(args[index:])
        return args[index]

    # Replace positional placeholders
    template = placeholder_regex.sub(replace_placeholder, template)

    # Replace $ARGUMENTS with all arguments
    template = template.replace("$ARGUMENTS", arguments)

    return template


def execute_command(name: str, arguments: str = "", loader: CommandLoader | None = None) -> str | None:
    """Execute a command and return the processed prompt."""
    if loader is None:
        loader = CommandLoader()

    command = loader.get(name)
    if not command:
        return None

    return process_template(command.template, arguments)


def is_command(input_str: str) -> bool:
    """Check if input string is a command invocation."""
    return input_str.strip().startswith("/")


def parse_command(input_str: str) -> tuple[str, str]:
    """Parse a command string into name and arguments."""
    parts = input_str.strip().split(" ", 1)
    command_name = parts[0][1:]  # Remove leading /
    arguments = parts[1] if len(parts) > 1 else ""
    return command_name, arguments
```

### The Command Loader

```python
from src import CommandLoader, execute_command

loader = CommandLoader()

# List commands
for cmd in loader.list():
    print(f"/{cmd.name}: {cmd.description}")
```

Output:
```
/test: Run tests and show results
/review: Review code for quality
/explain: Explain what code does
```

### Command Execution

```python
# Process /review main.py security
result = execute_command("review", "main.py security")

print(result)
```

Output:
```
Review the code at main.py for:
1. Code quality and readability
2. Potential bugs
3. Performance issues
4. Best practices violations

Focus on: security
```

The agent receives this rendered prompt and never saw `/review`.


## Putting It All Together

### Complete Agent

```python
from src import CodingAgent

agent = CodingAgent(
    project_dir=".",
    skills_dir="skills/",
    commands_dir="commands/",
)
```

### Processing User Input

```python
# Commands are intercepted first
processed = agent.process_input("/review main.py")
# Agent receives the rendered review prompt

processed = agent.process_input("I need tests")
# Agent receives the original text, then can load test-writer skill
```

### Connecting to an LLM

```python
from openai import OpenAI
from toyaikit.tools import Tools
from toyaikit.chat import IPythonChatInterface
from toyaikit.llm import OpenAIChatCompletionsClient
from toyaikit.chat.runners import OpenAIChatCompletionsRunner
from src import CodingAgent, GENERAL_CODING_PROMPT

# Create agent
agent = CodingAgent(project_dir=".")

# Set up tools (includes skill tool)
tools_obj = Tools()
tools_obj.add_tools(agent.tools)
tools_obj.add_tools(agent.skill_tools)

# Set up LLM
llm_client = OpenAIChatCompletionsClient(
    model='gpt-4o-mini',
    client=OpenAI(),
)

# Create runner
chat_interface = IPythonChatInterface()
runner = OpenAIChatCompletionsRunner(
    tools=tools_obj,
    developer_prompt=GENERAL_CODING_PROMPT,
    llm_client=llm_client,
)

# Define wrapper that handles commands
def run_with_commands(user_input: str):
    processed = agent.process_input(user_input)
    return runner.loop(prompt=processed)

# Run!
# run_with_commands("I need tests for calculator.py")
# run_with_commands("/review main.py")
```

### CLI Interface

```bash
cd workshop
python -m src.main
```

Available commands:
- `/list` - List all available skills
- `/show <name>` - Show skill details
- `/commands` - List all commands
- `/quit` - Exit


## Skills vs Commands

| Aspect | Skills | Commands |
|--------|--------|----------|
| Who invokes | Agent (autonomous) | User (manual) |
| Syntax | `skill({name: "..."})` | `/command args` |
| Agent sees | Yes, in tool description | No, pre-processed |
| Content | Full instructions | Prompt template |
| Use case | Specialized capabilities | Quick shortcuts |

Remember:
- Skills: Agent decides automatically based on user request
  - User says: "I need tests" → Agent loads test-writer skill

- Commands: User invokes directly for quick access
  - User says: "/review main.py" → Agent receives review prompt


## Running the Workshop

```bash
cd workshop
uv run jupyter notebook
```

Open the notebooks in order:
1. `01-recap.ipynb` - Quick recap of the coding agent
2. `02-general-agent.ipynb` - Remove Django dependency
3. `03-skills.ipynb` - Introduce skills
4. `04-commands.ipynb` - Introduce commands
5. `05-complete-agent.ipynb` - Full integration


## Project Structure

```
workshop/
├── README.md
├── notebooks/
│   ├── 01-recap.ipynb
│   ├── 02-general-agent.ipynb
│   ├── 03-skills.ipynb
│   ├── 04-commands.ipynb
│   └── 05-complete-agent.ipynb
├── src/
│   ├── __init__.py
│   ├── agent.py
│   ├── tools.py
│   ├── skills.py
│   ├── commands.py
│   └── main.py
├── skills/
│   ├── hello/SKILL.md
│   ├── joke/SKILL.md
│   ├── counter/SKILL.md
│   ├── coding_standards/SKILL.md
│   └── deploy_app/SKILL.md
└── commands/
    ├── test.md
    ├── review.md
    └── explain.md
```


## References

- OpenCode: https://github.com/anomalyco/opencode
- Skills Documentation: https://opencode.ai/docs/skills/
- AgentSkills Spec: https://agentskills.io
- Original coding-agent: ../coding-agent/
- ToyAIKit: https://github.com/alexeygrigorev/toyaikit
