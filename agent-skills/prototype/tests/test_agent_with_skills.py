"""
Test the real agent with skills.

These tests verify that the agent autonomously discovers and uses skills.
These ARE integration tests that call the LLM.

Run with: uv run pytest tests/test_agent_with_skills.py -v -s
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import create_agent
from utils import (
    get_tool_calls_with_args,
    assert_skill_called,
    assert_tool_called,
    assert_read_file_called,
    assert_bash_command_called,
)


@pytest.fixture
def agent_with_tools():
    """Create an agent with tools for testing."""
    return create_agent(
        project_dir=Path(__file__).parent.parent,
        provider="openai",
        model="gpt-4o-mini",
    )


# Tests

def test_agent_uses_read_file_tool(agent_with_tools):
    """Test that agent uses read_file tool when asked to read a file."""
    agent = agent_with_tools

    response = agent.chat("Read the README.md file and tell me what this project is about")
    assert response

    result = agent.get_last_result()
    calls = get_tool_calls_with_args(result)
    assert_tool_called(calls, 'read_file')


def test_agent_with_multifile_skill(agent_with_tools):
    """Test agent autonomously uses deploy_app skill."""
    agent = agent_with_tools

    response = agent.chat("I need to deploy my application. What steps should I follow?")
    assert response

    result = agent.get_last_result()
    calls = get_tool_calls_with_args(result)
    assert_skill_called(calls, 'deploy_app')


def test_agent_reads_skill_extra_files(agent_with_tools):
    """Test agent autonomously reads extra files referenced by a skill."""
    agent = agent_with_tools

    response = agent.chat("Show me the function template I should use for this project")
    assert response

    result = agent.get_last_result()
    calls = get_tool_calls_with_args(result)

    assert_skill_called(calls, 'coding_standards')
    assert_read_file_called(calls, 'function_template')


def test_agent_invokes_skill_script(agent_with_tools):
    """Test agent autonomously invokes scripts from skill's scripts folder."""
    agent = agent_with_tools

    response = agent.chat("Check if my code follows the project coding standards")
    assert response

    result = agent.get_last_result()
    calls = get_tool_calls_with_args(result)

    assert_skill_called(calls, 'coding_standards')
    assert_bash_command_called(calls, 'check_standards')


def test_multiple_skill_calls_in_conversation(agent_with_tools):
    """Test agent autonomously discovers and uses skills in conversation."""
    agent = agent_with_tools

    # First request about coding standards - agent loads skill AND reads template
    response1 = agent.chat("I need to write some code. What standards should I follow?")
    assert response1

    result1 = agent.get_last_result()
    calls1 = get_tool_calls_with_args(result1)
    assert_skill_called(calls1, 'coding_standards')
    assert_read_file_called(calls1, 'function_template')  # Template read in same message!

    # Second request - agent responds from context, no tool calls needed
    response2 = agent.chat("Show me the function template")
    assert response2
    # Agent already read the template, so no tool call here


def test_multifile_skill_template_discovery(agent_with_tools):
    """Test agent autonomously reads template files from multi-file skills."""
    agent = agent_with_tools

    response = agent.chat("I need to write a new function. Show me the template I should use.")
    assert response
    assert isinstance(response, str)

    result = agent.get_last_result()
    calls = get_tool_calls_with_args(result)

    assert_skill_called(calls, 'coding_standards')
    assert_read_file_called(calls, 'function_template')

    # Response should mention template content (type hints, docstrings)
    response_lower = response.lower()
    assert 'type' in response_lower or 'hint' in response_lower or 'docstring' in response_lower


def test_multifile_skill_script_invocation(agent_with_tools):
    """Test agent autonomously invokes scripts from skill's scripts folder."""
    agent = agent_with_tools

    response = agent.chat("Check if my code follows the project coding standards")
    assert response
    assert isinstance(response, str)

    result = agent.get_last_result()
    calls = get_tool_calls_with_args(result)

    assert_skill_called(calls, 'coding_standards')
    assert_bash_command_called(calls, 'check_standards')


def test_multifile_skill_complete_workflow(agent_with_tools):
    """Test complete workflow: load skill, read template, run script."""
    agent = agent_with_tools

    # Step 1: Ask about coding standards - loads skill AND reads template
    response1 = agent.chat("What are the coding standards for function naming?")
    assert response1

    result1 = agent.get_last_result()
    calls1 = get_tool_calls_with_args(result1)
    assert_skill_called(calls1, 'coding_standards')
    assert_read_file_called(calls1, 'function_template')  # Template read in step 1!

    # Step 2: Ask to see function template - already read, responds from context
    response2 = agent.chat("Show me the function template.")
    assert response2
    # No tool call expected - agent already has the template info

    # Step 3: Ask to run standards check - should run the script
    response3 = agent.chat("Now run the standards check script.")
    assert response3

    result3 = agent.get_last_result()
    calls3 = get_tool_calls_with_args(result3)
    assert_bash_command_called(calls3, 'check_standards')
