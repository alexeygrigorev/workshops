"""
OpenCode Skills Prototype

A simplified skill and command system.
"""

from .skills import SkillInfo, SkillLoader, SkillToolResult
from .skill_tool import SkillToolsWrapper
from .commands import CommandInfo, CommandLoader, execute_command
from .agent import RealAgent, TOAI_SYSTEM_PROMPT

__all__ = [
    # Skills
    "SkillInfo",
    "SkillLoader",
    "SkillToolResult",
    # Skill Tool
    "SkillToolsWrapper",
    # Commands
    "CommandInfo",
    "CommandLoader",
    "execute_command",
    # Agents
    "RealAgent",
    "TOAI_SYSTEM_PROMPT",
]
