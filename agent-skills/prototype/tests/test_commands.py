"""
Test the command system.

Commands are prompt templates that agents can use.

Run with: uv run pytest tests/test_commands.py -v
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.commands import CommandLoader, CommandInfo, execute_command
from src.main import create_agent


def test_command_discovery():
    """Test that commands are discovered from filesystem."""
    loader = CommandLoader()
    commands = loader.list()

    # Should have at least the review and test commands
    assert len(commands) >= 2
    command_names = [c.name for c in commands]
    assert "review" in command_names
    assert "test" in command_names


def test_nonexistent_command_returns_none():
    """Test that requesting a nonexistent command returns None."""
    loader = CommandLoader()
    cmd = loader.get("this-command-does-not-exist")

    assert cmd is None


def test_command_attributes():
    """Test that commands have all expected attributes."""
    cmd = CommandInfo(
        name="test",
        description="Test command",
        template="Test template",
    )

    assert cmd.name == "test"
    assert cmd.description == "Test command"
    assert cmd.template == "Test template"


def test_execute_command_returns_prompt():
    """Test that execute_command returns a processed prompt."""
    prompt = execute_command("review", "src/agent.py")

    assert prompt is not None
    assert "src/agent.py" in prompt
    # $1 was replaced with the argument
    assert "$1" not in prompt


def test_nonexistent_command_execution():
    """Test executing a nonexistent command returns None."""
    prompt = execute_command("nonexistent", "")

    assert prompt is None


def test_run_review_command_full_flow():
    """Test full command flow: execute + agent chat."""
    agent = create_agent(
        project_dir=Path(__file__).parent.parent,
        provider="openai",
        model="gpt-4o",
    )

    # Execute command to get prompt
    prompt = execute_command("review", "src/agent.py")
    assert prompt is not None

    # Feed prompt to agent
    response = agent.chat(prompt)

    assert response
    assert isinstance(response, str)
    assert len(response) > 50

    # Response should mention code review concepts
    response_lower = response.lower()
    assert any(word in response_lower for word in ["code", "quality", "improv", "suggest", "consider"])

    print(f"\nResponse preview: {response[:200]}...")
