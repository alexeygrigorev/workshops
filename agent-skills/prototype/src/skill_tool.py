"""
Skill tool implementation.

This module implements the native `skill` tool that agents use to load skills.
"""

from .skills import SkillLoader


class SkillToolsWrapper:
    """Wrapper class for the skill tool that toyaikit can discover.

    This class provides a `skill` method that toyaikit will register as a tool.
    """

    def __init__(self, loader: SkillLoader):
        self._loader = loader

    def skill(self, name: str) -> dict:
        """Load a skill to get specialized instructions.

        Args:
            name: Exact skill name to load

        Returns:
            Dictionary with skill information
        """
        result = self._loader.load(name)
        return {
            "name": result.name,
            "description": result.description,
            "content": result.content,
        }
