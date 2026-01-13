"""
Test the agent with commands integration.

These are integration tests that call the LLM.

Run with: uv run pytest tests/test_agent_with_commands.py -v -s
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import create_agent


@pytest.fixture
def agent():
    """Create an agent for testing."""
    return create_agent(
        project_dir=Path(__file__).parent.parent,
        provider="openai",
        model="gpt-4o-mini",
    )


def test_review_command_reviews_code(agent):
    """Test that /review command provides code review."""
    response = agent.chat("/review src/agent.py")

    assert response
    assert isinstance(response, str)
    assert len(response) > 100

    # Response should contain code review insights
    response_lower = response.lower()
    assert any(word in response_lower for word in [
        "code", "quality", "improv", "suggest", "consider",
        "review", "clean", "readab", "best practice"
    ])


def test_test_command_suggests_testing(agent):
    """Test that /test command suggests testing approach."""
    response = agent.chat("/test src/skills.py")

    assert response
    assert isinstance(response, str)

    # Response should mention testing concepts
    response_lower = response.lower()
    assert any(word in response_lower for word in [
        "test", "pytest", "assert", "case", "spec"
    ])


def test_command_with_multiple_arguments(agent):
    """Test command with multiple positional arguments."""
    response = agent.chat("/review src/agent.py src/tools.py")

    assert response
    assert isinstance(response, str)


def test_command_no_arguments(agent):
    """Test command with no arguments."""
    response = agent.chat("/test")

    assert response
    assert isinstance(response, str)


def test_nonexistent_command_returns_error(agent):
    """Test that nonexistent command returns error message."""
    response = agent.chat("/does_not_exist some args")

    assert "Command not found" in response
