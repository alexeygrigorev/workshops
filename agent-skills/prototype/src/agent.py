"""
Agent system for the OpenCode prototype.

This module provides the RealAgent class using toyaikit for orchestration.
"""

import os

import dotenv
from openai import OpenAI
from toyaikit.chat.runners import OpenAIChatCompletionsRunner
from toyaikit.llm import OpenAIChatCompletionsClient
from toyaikit.tools import Tools

from .commands import execute_command
from .skill_tool import SkillToolsWrapper
from .tools import AgentTools


# =============================================================================
# System Prompts
# =============================================================================

TOAI_SYSTEM_PROMPT = """You are Toai, an AI coding assistant designed to help with software engineering tasks.

You help users with:
- Writing, editing, and refactoring code
- Debugging and fixing errors
- Explaining code and technical concepts
- Project setup and configuration
- Code reviews and best practices

# Core Principles

1. **Be concise but thorough** - Get straight to the point, but don't skip important details
2. **Show your work** - Explain your reasoning for complex changes
3. **Ask questions** - When requirements are unclear, ask rather than assume
4. **Use tools effectively** - ALWAYS use available tools when relevant
5. **Code quality matters** - Write clean, maintainable code following best practices

# Working with Code

- **Prefer editing** over creating new files when possible
- **Read before writing** - Understand existing patterns before making changes
- **Test your changes** - Run builds/tests and fix any errors you introduce
- **Reference precisely** - When pointing to code, use `file_path:line_number` format

You're here to help users build better software efficiently. Start by understanding what they want to accomplish!"""


# =============================================================================
# Real Agent with Toyaikit
# =============================================================================

class RealAgent:
    """A real AI agent using toyaikit for orchestration.

    This agent uses toyaikit's OpenAIChatCompletionsRunner for:
    - Tool calling loop
    - Message handling
    - LLM interaction
    """

    # Provider configurations
    PROVIDERS = {
        "openai": {
            "api_key_env": "OPENAI_API_KEY",
            "model": "gpt-4o-mini",
        },
        "zai": {
            "api_key_env": "ZAI_API_KEY",
            "base_url": "https://api.z.ai/api/paas/v4/",
            "model": "glm-4.7",
        },
        "anthropic": {
            "api_key_env": "ANTHROPIC_API_KEY",
            "model": "claude-sonnet-4-20250514",
        },
    }

    def __init__(
        self,
        agent_name: str = "toai",
        system_prompt: str | None = None,
        project_tools: AgentTools | None = None,
        skill_tool: SkillToolsWrapper | None = None,
        model: str = "glm-4.7",
        provider: str = "zai",
    ):
        """Initialize a real agent.

        Args:
            agent_name: Name of the agent
            system_prompt: Custom system prompt (defaults to TOAI_SYSTEM_PROMPT)
            project_tools: AgentTools instance for file operations
            skill_tool: SkillToolsWrapper instance for skills
            model: Model name to use
            provider: LLM provider (openai, zai, anthropic)
        """
        # Load environment variables
        dotenv.load_dotenv()

        self.agent_name = agent_name
        self.project_tools = project_tools
        self.skill_tool = skill_tool
        self.model = model
        self.provider = provider

        # Build system prompt with skill names if skill_tool is provided
        self.system_prompt = self._build_prompt(system_prompt or TOAI_SYSTEM_PROMPT)

        # Set up LLM client based on provider
        config = self.PROVIDERS.get(provider, self.PROVIDERS["openai"])
        api_key = os.getenv(config["api_key_env"])

        if not api_key:
            raise ValueError(f"API key not found. Set {config['api_key_env']} env var.")

        client_kwargs = {"api_key": api_key}
        if "base_url" in config:
            client_kwargs["base_url"] = config["base_url"]

        self.llm_client = OpenAIChatCompletionsClient(
            model=model,
            client=OpenAI(**client_kwargs),
        )

        # Set up tools
        self.tools_obj = Tools()
        self.tools_obj.add_tools(self.project_tools)
        self.tools_obj.add_tools(self.skill_tool)

        # Create the runner
        self.runner = OpenAIChatCompletionsRunner(
            tools=self.tools_obj,
            developer_prompt=self.system_prompt,
            llm_client=self.llm_client,
        )

    def _build_prompt(self, base_prompt: str) -> str:
        """Build the system prompt with available skills."""
        if not self.skill_tool:
            return base_prompt

        skills = self.skill_tool._loader.list()
        if not skills:
            return base_prompt

        # Use the loader's description which has the skills list
        return base_prompt + "\n\n" + self.skill_tool._loader.description

    def chat(self, user_message: str) -> str:
        """Send a single message and get response.

        Args:
            user_message: The user's message (can be /command args)

        Returns:
            The assistant's response
        """
        # Handle /command syntax
        if user_message.startswith("/"):
            parts = user_message.split(" ", 1)
            command_name = parts[0][1:]  # Remove leading /
            arguments = parts[1] if len(parts) > 1 else ""

            prompt = execute_command(command_name, arguments)
            if prompt is None:
                return f"Command not found: /{command_name}"
            user_message = prompt

        result = self.runner.loop(prompt=user_message)
        self._last_result = result
        return result.last_message

    def get_last_result(self):
        """Get the full LoopResult from the last chat call.

        Returns:
            LoopResult with new_messages, all_messages, tokens, cost
        """
        return getattr(self, '_last_result', None)
