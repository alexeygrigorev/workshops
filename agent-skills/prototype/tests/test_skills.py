"""
Test the skills system components.

These are unit/deterministic tests that don't call the LLM.

Run with: uv run pytest tests/test_skills.py -v
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.skills import SkillLoader, SkillToolResult


def test_skill_discovery():
    """Test that skills are discovered from filesystem."""
    loader = SkillLoader()
    skills = loader.list()

    assert len(skills) >= 4, f"Should find at least 4 example skills, found {len(skills)}"

    skill_names = [s.name for s in skills]
    assert "hello" in skill_names, "Should have hello skill"
    assert "joke" in skill_names, "Should have joke skill"
    assert "counter" in skill_names, "Should have counter skill"
    assert "deploy_app" in skill_names, "Should have deploy_app skill"


def test_skill_list_shows_all_skills():
    """Test that skill loader discovers all available skills."""
    loader = SkillLoader()
    skills = loader.list()

    skill_names = [s.name for s in skills]

    # Check for core example skills
    assert "hello" in skill_names
    assert "joke" in skill_names
    assert "counter" in skill_names
    assert "deploy_app" in skill_names

    # Each skill should have required metadata
    for skill in skills:
        assert skill.name, f"Skill should have a name: {skill}"
        assert skill.description, f"Skill {skill.name} should have a description"
        assert skill.content, f"Skill {skill.name} should have content"


def test_skill_metadata_extraction():
    """Test that skill metadata is correctly extracted from frontmatter."""
    loader = SkillLoader()

    # Test hello skill
    hello = loader.get("hello")
    assert hello is not None
    assert hello.name == "hello"
    assert hello.description
    assert "hello" in hello.description.lower() or "greet" in hello.description.lower()

    # Test deploy_app skill
    deploy = loader.get("deploy_app")
    assert deploy is not None
    assert deploy.name == "deploy_app"
    assert "deploy" in deploy.description.lower()


def test_multifile_skill_content():
    """Test that multifile skill content includes references to other files."""
    loader = SkillLoader()
    deploy_app = loader.get("deploy_app")

    # The skill content should reference other files using @ syntax
    assert "@scripts/status.sh" in deploy_app.content
    assert "@scripts/deploy.sh" in deploy_app.content
    assert "@templates/verification.md" in deploy_app.content


def test_skill_content_has_file_references():
    """Test that multifile skills contain @ file references."""
    loader = SkillLoader()
    deploy = loader.get("deploy_app")

    assert deploy is not None
    content = deploy.content

    # Should contain references to files using @ syntax
    assert "@scripts/" in content
    assert "@templates/" in content


def test_nonexistent_skill_returns_none():
    """Test that requesting a nonexistent skill returns None."""
    loader = SkillLoader()
    skill = loader.get("this-skill-does-not-exist")

    assert skill is None


def test_skill_tool_description():
    """Test that skill loader includes skill list in description."""
    loader = SkillLoader()
    description = loader.description

    assert "skill" in description.lower()
    assert "hello" in description
    assert "joke" in description
    assert "counter" in description


def test_skill_tool_direct_call():
    """Test that skill can be loaded directly."""
    loader = SkillLoader()

    # Test loading hello skill directly
    result = loader.load("hello")

    assert result.name == "hello"
    assert result.description
    assert result.content
    assert "hello" in result.name


def test_multifile_skill_tool_loading():
    """Test that multifile skill can be loaded."""
    loader = SkillLoader()
    result = loader.load("deploy_app")

    assert result.name == "deploy_app"
    assert result.content
    # File references are in the content
    assert "scripts" in result.content.lower() or "templates" in result.content.lower()


def test_hello_skill_content():
    """Test that hello skill can be loaded directly."""
    loader = SkillLoader()
    result = loader.load("hello")

    assert result.name == "hello"
    assert result.description
    assert result.content
    # The skill content should contain greeting instructions
    content_lower = result.content.lower()
    assert any(word in content_lower for word in ["hello", "hi", "greet", "welcome"])


def test_joke_skill_content():
    """Test that joke skill can be loaded directly."""
    loader = SkillLoader()
    result = loader.load("joke")

    assert result.name == "joke"
    assert result.description
    assert result.content
    # The skill content should contain joke instructions
    content_lower = result.content.lower()
    assert any(word in content_lower for word in ["joke", "funny", "humor", "laugh"])
