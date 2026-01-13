"""
Command loader and execution system.
"""

import re
import shlex
import frontmatter
from pathlib import Path


class CommandInfo:
    """Information about a command."""

    def __init__(self, name: str, description: str, template: str):
        self.name = name
        self.description = description
        self.template = template


class CommandLoader:
    """Command discovery and loading from commands/ directory."""

    def __init__(self, commands_dir: Path | str = None):
        """Initialize the command loader.

        Args:
            commands_dir: Directory containing command .md files
        """
        if commands_dir is None:
            commands_dir = Path("commands")
        self.commands_dir = Path(commands_dir)

    def get(self, name: str):
        """Get a command by name.

        Args:
            name: Command name to retrieve

        Returns:
            CommandInfo if found, None otherwise
        """
        command_file = self.commands_dir / f"{name}.md"
        if not command_file.exists():
            return None

        try:
            with open(command_file, "r", encoding="utf-8") as f:
                parsed = frontmatter.load(f)

            return CommandInfo(
                name=name,
                description=parsed.get("description", ""),
                template=parsed.content,
            )
        except Exception:
            return None

    def list(self):
        """List all available commands.

        Returns sorted list by name.
        """
        commands = []

        if not self.commands_dir.exists():
            return commands

        for md_file in sorted(self.commands_dir.glob("*.md")):
            name = md_file.stem
            command = self.get(name)
            if command:
                commands.append(command)

        return commands


def execute_command(name: str, arguments: str = "") -> str | None:
    """Execute a command and return the processed prompt.

    Args:
        name: Command name
        arguments: Command arguments

    Returns:
        Processed prompt string, or None if command not found
    """
    loader = CommandLoader()
    command = loader.get(name)

    if not command:
        return None

    return _process_template(command.template, arguments)


def _process_template(template: str, arguments: str) -> str:
    """Process command template with argument substitution.

    Args:
        template: The template string
        arguments: Command arguments

    Returns:
        Processed template
    """
    # Parse arguments
    try:
        args = shlex.split(arguments) if arguments else []
    except ValueError:
        args = arguments.split() if arguments else []

    # Replace $1, $2, etc. with positional arguments
    placeholder_regex = re.compile(r'\$(\d+)')
    placeholders = placeholder_regex.findall(template)
    last = int(placeholders[-1]) if placeholders else 0

    def replace_placeholder(match):
        index = int(match.group(1)) - 1
        if index >= len(args):
            return ""
        if match.group(1) == str(last):
            # Last placeholder gets remaining args
            return " ".join(args[index:])
        return args[index]

    template = placeholder_regex.sub(replace_placeholder, template)

    # Replace $ARGUMENTS with all arguments
    template = template.replace("$ARGUMENTS", arguments)

    return template
