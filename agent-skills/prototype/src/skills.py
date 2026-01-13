"""
Skill discovery and loading system.
"""

import frontmatter
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SkillToolResult:
    """Result from the skill tool."""
    name: str
    description: str
    content: str


class SkillInfo:
    """Information about a skill."""

    def __init__(self, name: str, description: str, content: str = ""):
        self.name = name
        self.description = description
        self.content = content


class SkillLoader:
    """Skill discovery and loading from skills/ directory."""

    def __init__(self, skills_dir: Path | str = None):
        """Initialize the skill loader.

        Args:
            skills_dir: Directory containing skill subdirectories with SKILL.md files
        """
        if skills_dir is None:
            skills_dir = Path("skills")
        self.skills_dir = Path(skills_dir)

    def get(self, name: str):
        """Get a skill by name.

        Args:
            name: Skill name to retrieve

        Returns:
            SkillInfo if found, None otherwise
        """
        skill_file = self.skills_dir / name / "SKILL.md"
        if not skill_file.exists():
            return None

        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                parsed = frontmatter.load(f)

            return SkillInfo(
                name=parsed.get("name", name),
                description=parsed.get("description", ""),
                content=parsed.content,
            )
        except Exception:
            return None

    def list(self):
        """List all available skills.

        Returns sorted list by name.
        """
        skills = []

        if not self.skills_dir.exists():
            return skills

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            skill = self.get(skill_dir.name)
            if skill:
                skills.append(skill)

        return skills

    def load(self, name: str) -> SkillToolResult:
        """Load a skill with resolved file references.

        Args:
            name: Skill name to load

        Returns:
            SkillToolResult with resolved content

        Raises:
            ValueError: If skill is not found
        """
        skill = self.get(name)
        if skill is None:
            raise ValueError(f"Skill not found: {name}")

        # Resolve @filename references to full paths
        base_dir = self.skills_dir / name
        content = self._resolve_file_references(skill.content, base_dir)

        return SkillToolResult(
            name=skill.name,
            description=skill.description,
            content=content,
        )

    def _resolve_file_references(self, content: str, base_dir: Path) -> str:
        """Resolve @filename references to full paths in skill content.

        Args:
            content: The skill content with @filename references
            base_dir: The base directory of the skill

        Returns:
            Content with @ references replaced by full paths
        """
        def replace_ref(match):
            filename = match.group(1)
            full_path = base_dir / filename
            if full_path.exists():
                return str(full_path)
            return match.group(0)  # Keep original if file doesn't exist

        # Match @filename or @path/filename
        return re.sub(r'@([^\s,)]+)', replace_ref, content)

    @property
    def description(self) -> str:
        """Description of available skills."""
        skills = self.list()
        skills_listing = "\n".join(
            f"  - {s.name}: {s.description}"
            for s in skills
        )

        base_desc = (
            "Load a skill to get specialized instructions for handling user requests.\n"
            "CRITICAL: Before responding to ANY user request, check if a skill matches their intent. "
            "If a skill's purpose matches the user's request, you MUST call this tool.\n\n"
            "IMPORTANT: The 'name' parameter must match EXACTLY one of the skill names listed below. "
            "Copy the skill name exactly as shown (including underscores).\n\n"
            "Available skills:\n"
        )

        return base_desc + skills_listing
