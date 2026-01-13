# OpenCode Skills - Python Prototype

A Python implementation of OpenCode's skill system with a real AI agent using toyaikit.

**Reference:** https://github.com/anomalyco/opencode | https://opencode.ai/docs/skills/

---

## Quick Start

### 1. Install Dependencies

```bash
cd /c/Users/alexe/tmp/open-code/prototype
uv sync
```

### 2. Set Up API Keys

Edit `.env` with your API keys:

```bash
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 3. Run the Agent

**Interactive CLI with Skills:**
```bash
python -m src.main
```

**Interactive AI Chat (Real Agent):**
```bash
python -m src.main //chat
```

### 4. Available Commands

| Command | Description |
|---------|-------------|
| `/list` | List all available skills |
| `/show <name>` | Show skill details |
| `/commands` | List all commands |
| `/chat` | Start AI agent chat |
| `/agent <name>` | Simulate agent loading a skill |
| `/prompt [build\|toai]` | Show agent system prompt |

---

## What are Skills?

**Skills** are reusable behavior packages for AI agents. They are defined as markdown files (`SKILL.md`) with YAML frontmatter that describe:

1. **Metadata** (frontmatter) - name, description, license
2. **Instructions** (content) - detailed behavior and usage patterns

Agents discover available skills and load them on-demand via the native `skill` tool.

> **Reference:** [OpenCode Skills Documentation](https://opencode.ai/docs/skills/)

### SKILL.md Format

```markdown
---
name: git-release
description: Create consistent releases and changelogs
license: MIT
metadata:
  audience: maintainers
---

# Git Release Skill

## What I do
- Draft release notes from merged PRs
- Propose a version bump

## When to use me
Use this when preparing a tagged release...
```

### Required Frontmatter Fields

| Field | Description | Validation |
|-------|-------------|------------|
| `name` | Skill identifier | 1-64 chars, lowercase alphanumeric with hyphens |
| `description` | Brief description for agent selection | 1-1024 characters |

### Optional Frontmatter Fields

| Field | Description |
|-------|-------------|
| `license` | License information |
| `compatibility` | Compatibility info (e.g., "opencode") |
| `metadata` | Additional string-to-string key-value pairs |
| `disable` | Set to `true` to hide the skill |

> **Reference:** https://opencode.ai/docs/skills/#write-frontmatter

---

## Skill Discovery

### Locations

OpenCode searches for skills in these locations:

| Location | Pattern |
|----------|---------|
| Project OpenCode | `.opencode/skill/<name>/SKILL.md` |
| Project Claude | `.claude/skills/<name>/SKILL.md` |
| Global OpenCode | `~/.config/opencode/skill/<name>/SKILL.md` |
| Global Claude | `~/.claude/skills/<name>/SKILL.md` |

### Discovery Rules

1. **Project-local discovery**: Walks up from current directory to git worktree root
2. **Priority order**: Later sources override earlier ones
3. **Name validation**: Directory name must match `name` field
4. **Duplicate detection**: Warns when multiple skills have the same name

> **Reference:** https://opencode.ai/docs/skills/#place-files

### Implementation

**OpenCode Reference:** `packages/opencode/src/skill/skill.ts:38-64`

```typescript
// Glob patterns for skill discovery
const OPENCODE_SKILL_GLOB = new Bun.Glob("{skill,skills}/**/SKILL.md")
const CLAUDE_SKILL_GLOB = new Bun.Glob("skills/**/SKILL.md")

// Scan directories and parse SKILL.md files
for await (const mdFile of skillGlob.scan(root)) {
  const parsed = ConfigMarkdown.parse(mdFile)
  const skill = Skill.parse(parsed.data)
  skills[skill.name] = skill
}
```

**Python Implementation:** `src/skills.py:88-150`

```python
def _scan_skill_directory(self, directory: Path, source_type: str) -> dict[str, SkillInfo]:
    """Scan a directory for skill definitions."""
    for skill_md in directory.rglob("SKILL.md"):
        parsed = parse(skill_md)
        is_valid, errors = validate_skill_frontmatter(parsed.data)
        if is_valid:
            skills[parsed.data["name"]] = SkillInfo(...)
```

---

## The Skill Tool

Agents access skills through the native `skill` tool. The tool:

1. **Lists available skills** in its description
2. **Loads skill content** when called with a name
3. **Checks permissions** before loading

### Tool Schema

```python
{
    "name": "skill",
    "description": "Load a skill by name to access specialized instructions...",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of the skill to load"}
        },
        "required": ["name"]
    }
}
```

### Tool Description

When an agent receives the tool, it sees a list of available skills:

```
<available_skills>
  <skill>
    <name>git-release</name>
    <description>Create consistent releases and changelogs</description>
  </skill>
  <skill>
    <name>pr-review</name>
    <description>Review pull requests for code quality</description>
  </skill>
</available_skills>
```

> **Reference:** `packages/opencode/src/tool/skill.ts:29-36`

### Loading a Skill

```python
result = skill_tool("git-release")
# Returns:
# SkillToolResult(
#     name="git-release",
#     description="Create consistent releases...",
#     content="## What I do...",
#     license="MIT",
#     permission_action=PermissionAction.ALLOW
# )
```

> **Reference:** `packages/opencode/src/tool/skill.ts:54-74`

---

## Commands vs Skills

OpenCode has two mechanisms for reusable behavior:

### Skills

**Skills are loaded BY agents.**

- Agents decide when to use them (automatic inference)
- Loaded via the `skill` tool
- Full behavior packages with detailed instructions
- Located in: `.opencode/skill/<name>/SKILL.md`

```
User: "I need to create a release"
       ↓
Agent: (infers git-release skill is needed)
       ↓
Agent: skill({name: "git-release"})
       ↓
Tool: Returns skill content
       ↓
Agent: Has skill instructions in context
```

### Commands

**Commands are shortcuts FOR agents.**

- User invokes them directly (e.g., `/init`)
- Predefined prompt templates
- Quick access to common tasks
- Located in: `.opencode/command/<name>.md`

```
User: /init
       ↓
System: Executes predefined prompt template
       ↓
Agent: Receives the rendered prompt
```

### Comparison

| Aspect | Skills | Commands |
|--------|--------|----------|
| **Who invokes** | Agent (automatically) | User (manually) |
| **How invoked** | `skill({name: "..."})` | `/command-name` |
| **Detection** | Agent infers from user request | System parses for `/` prefix |
| **Content** | Full behavior instructions | Prompt template |
| **Location** | `.opencode/skill/<name>/SKILL.md` | `.opencode/command/<name>.md` |
| **Discovery** | Listed in tool description | Listed as slash commands |
| **Use case** | Specialized capabilities | Quick shortcuts |

### How This Works in Practice

**When you type `/init`:**
```
User input: "/init"
                ↓
System detects leading "/" → It's a command!
                ↓
System executes the /init command
                ↓
Agent receives: "Analyze this project and create/update AGENTS.md..."
                ↓
Agent never saw "/init"
```

**When you type "I need to create a release":**
```
User input: "I need to create a release"
                ↓
No leading "/" → Send to agent
                ↓
Agent reads message, checks available skills
                ↓
Agent matches "release" to git-release skill
                ↓
Agent calls: skill({name: "git-release"})
                ↓
Agent receives skill content
```

### Example Commands

OpenCode includes built-in commands:

```
/init    - Create/update AGENTS.md for the project
/review  - Review changes for quality and best practices
```

Custom commands can be created as markdown files:

```markdown
---
description: Run tests with coverage
---

Run the test suite with coverage report.
Focus on failing tests and suggest fixes.
```

### See Available Commands

```bash
python -m src.main //commands      # List all commands
python -m src.main //command init  # Show command details
```

---

## How Agents Use Skills

### Automatic Skill Inference

**Agents AUTOMATICALLY decide when to use skills** - you don't need to explicitly ask for them.

When you send a request, the agent:
1. Reads your message
2. Looks at available skill descriptions
3. **Decides on its own** which skill would help
4. Calls `skill({name: "..."})` automatically

### Examples

| ❌ Don't say this | ✅ Say this instead | Agent Infers |
|------------------|---------------------|--------------|
| "Use the git-release skill" | "I need to create a release" | `git-release` |
| "Load the pr-review skill" | "Can you review this PR?" | `pr-review` |
| "Use skill changelog" | "What's changed recently?" | `changelog` |

### Flow Diagram

```
User: "I need to create a release"
       ↓
Agent: (sees available skills and their descriptions)
       ↓
Agent: matches "release" → "git-release: Create consistent releases..."
       ↓
Agent: skill({name: "git-release"})  ← Automatic decision
       ↓
Tool: Returns skill content
       ↓
Agent: Has skill instructions in context, helps you
```

### Skill Content Injection

When the skill tool executes, it returns formatted content:

```markdown
## Skill: git-release

**Base directory**: .opencode/skill/git-release

# Git Release Skill

## What I do
- Draft release notes from merged PRs
- Propose a version bump

## When to use me
Use this when preparing a tagged release...
```

This formatted content is added to the conversation as a **tool result**. The LLM then sees this skill content in its context and uses the instructions to respond to your request.

### See It In Action

```bash
python -m src.main //agent git-release
```

This demonstrates:
- User says: "I need to create a release and draft changelog"
- Agent automatically infers: Use `git-release` skill
- Skill content is injected into conversation
- LLM sees the skill instructions

---

## How Skills Are Communicated to Agents

### Via Tool Description (NOT System Prompt)

**Key Point:** Skills are NOT listed in the system prompt. They are communicated through the **skill tool's description**.

When the agent initializes, it receives a tool list where the skill tool's description includes all available skills:

```python
# What the LLM sees in its tools list:

### skill
Load a skill by name to access specialized instructions and capabilities.
Skills are reusable behavior packages defined in SKILL.md files.

<available_skills>
  <skill>
    <name>git-release</name>
    <description>Create consistent releases and changelogs</description>
  </skill>
  <skill>
    <name>pr-review</name>
    <description>Review pull requests for code quality</description>
  </skill>
  <skill>
    <name>changelog</name>
    <description>Generate and maintain project changelogs</description>
  </skill>
</available_skills>

Parameters:
  name (string, required): Name of the skill to load
```

### Implementation

**OpenCode Reference:** `packages/opencode/src/tool/skill.ts:22-37`

```typescript
const description =
  skills.length === 0
    ? "Load a skill to get detailed instructions. No skills are currently available."
    : [
        "Load a skill to get detailed instructions for a specific task.",
        "Skills provide specialized knowledge and step-by-step guidance.",
        "Use this when a task matches an available skill's description.",
        "<available_skills>",
        ...skills.flatMap((skill) => [
          `  <skill>`,
          `    <name>${skill.name}</name>`,
          `    <description>${skill.description}</description>`,
          `  </skill>`,
        ]),
        "</available_skills>",
      ].join(" ")
```

**Python Implementation:** `src/skill_tool.py:108-125` and `src/skills.py:240-270`

The `to_tool_description()` method formats skills into the XML structure that gets embedded in the tool description.

### Why This Design?

1. **Separation of concerns:** System prompt contains behavior rules, tool descriptions contain capabilities
2. **Dynamic updates:** Skill list can change without modifying the system prompt
3. **LLM-friendly:** The XML format is clear and parseable by the LLM
4. **Automatic inference:** LLM reads tool descriptions and automatically decides which skill matches the user's request

---

## Command Execution and Chaining

### How OpenCode Handles Command Execution

OpenCode does **NOT** have a "command tool" like the skill tool. Instead, it uses:

1. **Task Tool** - For slash commands and complex workflows
2. **Batch Tool** - For parallel tool execution
3. **Bash chaining** - For sequential shell commands

### Task Tool Pattern

Slash commands like `/kid` or `/parent` are executed via the **Task tool**:

> **Reference:** `packages/opencode/src/tool/task.txt:9`

```
When instructed to execute custom slash commands, use the Task tool
with the slash command invocation as the entire prompt.

Example: Task(description="Check the file", prompt="/check-file path/to/file.py")
```

This means:
- Agent calls `Task(prompt="/command-name [args]")`
- Task tool creates a new session with a specialized agent
- The agent executes the command's template
- Results are returned to the original agent

### Sequential vs Parallel Execution

| Pattern | Mechanism | Use Case |
|---------|-----------|----------|
| **Sequential tasks** | Agent makes multiple tool calls in order | Multi-step workflows |
| **Parallel tools** | Batch Tool (up to 10 concurrent) | Independent operations |
| **Sequential bash** | `cmd1 && cmd2 && cmd3` | Dependent shell commands |
| **Iterative** | Agent loops based on results | "Keep iterating until..." |

> **Reference:** `packages/opencode/src/tool/bash.txt:39`
> "If commands depend on each other and must run sequentially, use a single Bash call with '&&' to chain them together."

### Key Point: Agents Don't Know About Commands!

**Commands are user-facing, NOT agent-facing.**

| Aspect | Skills | Commands |
|--------|--------|----------|
| **Who invokes** | **Agent** (autonomously) | **User** (via `/` prefix) |
| **Agent awareness** | Sees skill list in tool description | **None** - commands pre-executed |
| **Parameter format** | Tool parameters JSON | Template placeholders |
| **Execution flow** | Agent decides → calls skill tool | System intercepts → renders template → sends to agent |

### Command Execution Flow

```
User types: /review my-feature
              ↓
System detects leading "/" → It's a command!
              ↓
System looks up the command definition
              ↓
System substitutes arguments into template
              ↓
Agent receives rendered prompt (NEVER saw "/review")
              ↓
Agent responds to the rendered prompt
```

**The agent NEVER sees the command syntax** - only the rendered result!

### Command Template Parameters

Commands use placeholder substitution in their templates:

| Placeholder | Description | Example Input | Result |
|-------------|-------------|---------------|--------|
| `$1`, `$2`, `$3` | Positional arguments | `$1 is $2` with `foo bar` | `foo is bar` |
| `$ARGUMENTS` | All arguments | `$ARGUMENTS` with `a b c` | `a b c` |
| `$WORKTREE` | Project directory | `$WORKTREE` | `/path/to/project` |

> **Reference:** `packages/opencode/src/session/prompt.ts:1354-1389`

### Example Command with Parameters

**Command file:** `.opencode/command/test.md`

```markdown
---
description: Run tests with coverage
---

Run the test suite for $1 with coverage report.
Focus on failing tests: $ARGUMENTS
```

**User types:** `/test authentication`

**Agent receives:** (agent never saw `/test`!)
```
Run the test suite for authentication with coverage report.
Focus on failing tests: authentication
```

### Command Parameter Implementation

**OpenCode Reference:** `packages/opencode/src/session/prompt.ts:1369-1389`

```typescript
// Parse arguments
const raw = input.arguments.match(argsRegex) ?? []
const args = raw.map((arg) => arg.replace(/^["']|["']$/g, ""))

// Replace positional placeholders ($1, $2, etc.)
const withArgs = templateCommand.replaceAll(/\$(\d+)/g, (_, index) => {
  const position = Number(index)
  const argIndex = position - 1
  if (argIndex >= args.length) return ""
  return args[argIndex]
})

// Replace $ARGUMENTS
let template = withArgs.replaceAll("$ARGUMENTS", input.arguments)
```

### How Users Discover Commands

Commands are listed via HTTP API for the TUI (NOT for agents):

**OpenCode Reference:** `packages/opencode/src/server/server.ts`

```typescript
.get("/command", async (c) => {
  const commands = await Command.list()
  return c.json(commands)  // For UI display only!
})
```

Users see commands in:
- TUI command dialog (`ctrl+p`)
- Autocomplete suggestions
- Command help output

### Implementation for Python Prototype

```python
# Commands are NOT exposed as tools to agents
# They are user-facing shortcuts that render templates

class CommandLoader:
    def execute(self, name: str, args: str) -> str:
        """Execute a command and return rendered template."""
        cmd = self.get(name)
        if not cmd:
            raise ValueError(f"Unknown command: {name}")

        # Substitute arguments
        template = cmd.template
        template = template.replace("$ARGUMENTS", args)

        # Positional substitution ($1, $2, etc.)
        parts = args.split()
        for i, arg in enumerate(parts, 1):
            template = template.replace(f"${i}", arg)

        return template  # This gets sent to agent, not the command syntax

# CLI usage (user-facing, not agent)
if user_input.startswith("/"):
    command_name, args = parse_command(user_input)
    rendered = command_loader.execute(command_name, args)
    send_to_agent(rendered)  # Agent never saw the "/" syntax!
```

---

## Permission System

Skills support pattern-based permissions to control which agents can access them.

### Permission Actions

| Action | Behavior |
|--------|----------|
| `allow` | Skill loads immediately |
| `deny` | Skill hidden from agent, access rejected |
| `ask` | User prompted for approval before loading |

### Configuration

```json
{
  "permission": {
    "skill": {
      "pr-review": "allow",
      "internal-*": "deny",
      "experimental-*": "ask",
      "*": "allow"
    }
  }
}
```

### Pattern Matching

- `*` - Matches everything
- `internal-*` - Matches `internal-docs`, `internal-tools`, etc.
- `exact-name` - Matches only that specific skill

Rules are evaluated in order; first match wins.

> **Reference:** https://opencode.ai/docs/skills/#configure-permissions

### Implementation

**OpenCode Reference:** `packages/opencode/src/permission/index.ts:55-57`

```typescript
// Permission checking
const permission = Permission.check("skill", skillName, agent)
if (permission === "deny") throw new Error("Access denied")
```

**Python Implementation:** `src/permission.py:55-82`

```python
class PermissionConfig:
    def check(self, name: str) -> PermissionAction:
        for rule in self.rules:
            if rule.matches(name):
                return rule.action
        return self.default_action
```

---

## Project Structure

```
prototype/
├── README.md              # This file
├── src/
│   ├── __init__.py       # Package exports
│   ├── main.py           # CLI with REPL
│   ├── skills.py         # Skill discovery and loading
│   ├── skill_tool.py     # Skill tool implementation
│   ├── permission.py     # Permission system
│   └── frontmatter.py    # YAML frontmatter parser
└── examples/
    └── skills/
        ├── git-release/SKILL.md
        ├── pr-review/SKILL.md
        └── changelog/SKILL.md
```

---

## Usage

### Interactive CLI

```bash
cd C:/Users/alexe/tmp/open-code/prototype
python -m src.main
```

```
╔═══════════════════════════════════════════════════════════════════╗
║                     OpenCode Skills Prototype                    ║
╚═══════════════════════════════════════════════════════════════════╝

> /list
  Found 3 skill(s):
  [custom]            changelog                  Generate and maintain project changelogs
  [custom]            git-release                Create consistent releases and changelogs
  [custom]            pr-review                  Review pull requests for code quality

> /show git-release --content
  Name: git-release
  Description: Create consistent releases and changelogs
  License: MIT
  Source: custom
  Content:
  # Git Release Skill
  ...

> /load git-release
  Description: Create consistent releases and changelogs
  Permission: allow
  Content:
  # Git Release Skill
  ...

> /agent git-release
  [AGENT SIMULATION - Skill Injection Demo]
  User said: "I need to create a release and draft changelog"
  Agent AUTOMATICALLY inferred to use: git-release
  ...
```

### Python API

```python
from src import SkillLoader, SkillTool

# List skills
loader = SkillLoader()
skills = loader.list()
for skill in skills:
    print(f"{skill.name}: {skill.description}")

# Use the skill tool
tool = SkillTool(loader=loader)
result = tool("git-release")
print(result.content)
```

---

## Creating Skills

### Step 1: Create Directory

```bash
mkdir -p .opencode/skill/my-skill
```

### Step 2: Create SKILL.md

```markdown
---
name: my-skill
description: A brief description for agents
---

# My Skill

## What I do
Describe what this skill does...

## When to use me
Describe when agents should use this skill...
```

### Step 3: Verify

```bash
python -m src.main /list
python -m src.main /show my-skill
```

---

## Key Implementation Files

| File | Purpose | Reference |
|------|---------|-----------|
| `src/skills.py` | Skill discovery and loading | `packages/opencode/src/skill/skill.ts` |
| `src/skill_tool.py` | Skill tool for agent invocation | `packages/opencode/src/tool/skill.ts` |
| `src/commands.py` | Command discovery and loading | `packages/opencode/src/command/index.ts` |
| `src/permission.py` | Pattern-based permissions | `packages/opencode/src/permission/index.ts` |
| `src/frontmatter.py` | YAML frontmatter parser | `packages/opencode/src/config/markdown.ts` |
| `src/main.py` | CLI with REPL and agent simulation | - |

---

## References

- **OpenCode Repository:** https://github.com/anomalyco/opencode
- **Skills Documentation:** https://opencode.ai/docs/skills/
- **AgentSkills Standard:** https://agentskills.io
