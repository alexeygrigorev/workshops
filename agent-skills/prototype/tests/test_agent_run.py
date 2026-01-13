"""
Test the real agent with skills.

This demonstrates the agent using tools including skills.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import create_agent
from src.skills import SkillLoader
from utils import get_tool_calls, print_tool_calls


def test_agent_uses_hello_skill():
    """Test the agent autonomously discovers and uses the hello skill."""
    print("\n" + "=" * 60)
    print("  Agent Test: Hello Skill Discovery")
    print("=" * 60)

    loader = SkillLoader()
    print("\nAvailable skills:")
    for skill in loader.list():
        print(f"  - {skill.name}: {skill.description}")

    agent = create_agent(
        project_dir=Path(__file__).parent.parent,
        provider="openai",
        model="gpt-4o-mini",
    )

    print(f"\nAgent: {agent.agent_name}")
    print(f"Provider: {agent.provider}")
    print(f"Model: {agent.model}")

    # Test: Ask for a greeting - agent should autonomously discover the hello skill
    print("\n" + "-" * 60)
    print("TEST: Ask agent to greet you")
    print("Expected: Agent should discover and use the hello skill")
    print("-" * 60)

    user_message = "Greet me warmly"
    print(f"\nUser: {user_message}")

    response = agent.chat(user_message)
    print(f"\nAgent: {response[:200]}...")

    # Check tool calls
    result = agent.get_last_result()
    print_tool_calls(result)

    # Assert response exists and contains a greeting
    assert response, "Agent should respond"
    assert isinstance(response, str), "Response should be a string"
    # Should contain greeting words
    assert any(word in response.lower() for word in ["hello", "hi", "hey", "greetings", "welcome"])


def test_agent_uses_joke_skill():
    """Test the agent autonomously discovers and uses the joke skill."""
    print("\n" + "=" * 60)
    print("  Agent Test: Joke Skill Discovery")
    print("=" * 60)

    agent = create_agent(
        project_dir=Path(__file__).parent.parent,
        provider="openai",
        model="gpt-4o-mini",
    )

    # Test: Ask for a joke - agent should autonomously discover the joke skill
    print("\n" + "-" * 60)
    print("TEST: Ask agent for a programming joke")
    print("Expected: Agent should discover and use the joke skill")
    print("-" * 60)

    user_message = "Tell me a funny programming joke"
    print(f"\nUser: {user_message}")

    response = agent.chat(user_message)
    print(f"\nAgent: {response[:200]}...")

    # Check tool calls
    result = agent.get_last_result()
    print_tool_calls(result)

    # Assert response exists and is substantial (a joke)
    assert response, "Agent should respond"
    assert isinstance(response, str), "Response should be a string"
    assert len(response) > 50, "Joke response should be substantial"


def test_agent_file_operations():
    """Test the agent with file operations."""
    print("\n" + "=" * 60)
    print("  Agent Test: File Operations")
    print("=" * 60)

    agent = create_agent(
        project_dir=Path(__file__).parent.parent,
        provider="openai",
        model="gpt-4o-mini",
    )

    # Test: Ask to list files - agent should autonomously discover glob_files tool
    print("\n" + "-" * 60)
    print("TEST: Ask to list Python files")
    print("Expected: Agent should discover and use glob_files tool")
    print("-" * 60)

    user_message = "List all Python files in the src directory"
    print(f"\nUser: {user_message}")

    response = agent.chat(user_message)
    print(f"\nAgent: {response[:200]}...")

    # Check tool calls
    result = agent.get_last_result()
    print_tool_calls(result)

    # Assert response exists
    assert response, "Agent should respond"
    assert isinstance(response, str), "Response should be a string"

    # Assert glob_files tool was called
    tool_calls = get_tool_calls(result)
    assert "glob_files" in tool_calls, f"Expected glob_files tool to be called, got: {tool_calls}"
