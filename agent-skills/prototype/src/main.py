"""
Main agent setup and fixtures.
"""

from pathlib import Path

from dotenv import load_dotenv

from .agent import RealAgent
from .skills import SkillLoader
from .skill_tool import SkillToolsWrapper
from .tools import AgentTools

load_dotenv()


def create_agent(
    project_dir: Path | str = None,
    provider: str = "openai",
    model: str = "gpt-4o",
) -> RealAgent:
    """Create a configured agent with tools.

    Args:
        project_dir: Project directory
        provider: LLM provider (openai, zai, anthropic)
        model: Model name

    Returns:
        Configured RealAgent instance
    """
    assert project_dir is not None
    project_dir = Path(project_dir)

    loader = SkillLoader()
    skill_tool = SkillToolsWrapper(loader=loader)
    project_tools = AgentTools(project_dir)

    return RealAgent(
        agent_name="toai",
        project_tools=project_tools,
        skill_tool=skill_tool,
        provider=provider,
        model=model,
    )
