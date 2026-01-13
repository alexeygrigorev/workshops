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
uv add jupyter openai toyaikit frontmatter
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

These tools are generic. What makes an agent specialized is the prompt.

We will use these tools in this project too, so let's download them:

```bash
wget https://raw.githubusercontent.com/alexeygrigorev/workshops/refs/heads/main/coding-agent/tools.py
```

## General-Purpose Agent

The Django agent from the previous workshop has a detailed prompt with Django-specific instructions. See the full prompt in [coding-agent/README.md](https://github.com/alexeygrigorev/workshops/blob/main/coding-agent/README.md#L384).

For a general-purpose agent, we need a general-purpose prompt.

For this workshop, I used [OpenCode](https://github.com/anomalyco/opencode) as the reference implementation of a coding agent. Here's their prompt: [anthropic.txt](https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/session/prompt/anthropic.txt).

We will simplify it:

```python
GENERAL_CODING_PROMPT = """You are a coding agent designed to help with software engineering tasks.

You help users with:
- Writing, editing, and refactoring code
- Debugging and fixing errors
- Explaining code and technical concepts
- Project setup and configuration
- Code reviews and best practices

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
"""
```

This simplified version removes all framework-specific details, so the agent works on any codebase, not just Django.

## Implementing Skills

### SKILL.md Format

Each skill is a markdown file with YAML frontmatter. Here's an example from the `hello` skill:

```markdown
---
name: hello
description: MANDATORY for ALL greeting requests - you MUST load this skill before responding
---

# Hello Skill - REQUIRED FOR ALL GREETINGS

YOU MUST LOAD THIS SKILL BEFORE RESPONDING TO ANY GREETING REQUEST.

This skill provides the MANDATORY greeting format you must follow.

## How to greet

Always greet the user with:
- A warm welcome
- Their name if mentioned
- A friendly emoji

## Example greetings

- "Hello! Welcome! How can I help you today? 👋"
- "Hi there! Great to see you! 😊"
```

### Directory Structure

```
skills/
├── hello/
│   └── SKILL.md
├── joke/
│   └── SKILL.md
├── counter/
│   └── SKILL.md
├── coding_standards/
│   └── SKILL.md
└── deploy_app/
    └── SKILL.md
```

### The Skill Loader

The `SkillLoader` class discovers and loads skills:

```python
from src import SkillLoader

loader = SkillLoader()
skills = loader.list()

for skill in skills:
    print(f"{skill.name}: {skill.description}")
```

Output:
```
hello: MANDATORY for ALL greeting requests
joke: MANDATORY for ALL joke requests
counter: Counting and numbering functionality
coding_standards: Use when writing or reviewing code
deploy_app: Use for deployment guidance
```

### The Skill Tool

Agents access skills through a `skill()` tool:

```python
from src import SkillToolsWrapper

skill_tool = SkillToolsWrapper(loader)

# Agent calls this:
result = skill_tool.skill("hello")
# Returns: {name: "hello", description: "...", content: "..."}
```

### Tool Description Injection

The skill tool's description includes all available skills:

```python
print(skill_tool.tool_description())
```

Output:
```
Load a skill to get specialized instructions.

Available skills:
  - hello: MANDATORY for ALL greeting requests
  - joke: MANDATORY for ALL joke requests
  - counter: Counting and numbering functionality
  - coding_standards: Use when writing or reviewing code
  - deploy_app: Use for deployment guidance
```

This description is what the agent sees. When a user says "tell me a joke", the agent reads this description, matches "joke" to the joke skill, and calls `skill({name: "joke"})` automatically.


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
