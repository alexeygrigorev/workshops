"""
Tool implementations for the OpenCode agent.

These tools provide file system and shell access to the agent.
"""

import glob as glob_module
import os
import re
import subprocess
from pathlib import Path


# Directories to skip when scanning
SKIP_DIRS = {
    ".venv",
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".coverage",
    "node_modules",
    ".DS_Store",
    "venv",
    "env",
    ".tox",
    "dist",
    "build",
}


class AgentTools:
    """Collection of tools for the agent to use.

    Reference: packages/opencode/src/tool/registry.ts
    """

    def __init__(self, project_dir: Path | str = Path.cwd()):
        """Initialize tools with a project directory.

        Args:
            project_dir: Root directory for file operations
        """
        self.project_dir = Path(project_dir).resolve()

    # ========================================================================
    # File: Read
    # Reference: packages/opencode/src/tool/read.ts
    # ========================================================================

    def read_file(self, filepath: str, offset: int = 0, limit: int = 0) -> str:
        """Read and return the contents of a file.

        Reference: packages/opencode/src/tool/read.ts

        Args:
            filepath: Path to the file (relative or absolute)
            offset: Line number to start reading from (0-based, 0 = start)
            limit: Maximum number of lines to read (0 = all)

        Returns:
            File contents
        """
        path = self._resolve_path(filepath)

        try:
            with open(path, "r", encoding="utf-8") as f:
                if offset == 0 and limit == 0:
                    return f.read()
                lines = f.readlines()
                if limit > 0:
                    return "".join(lines[offset:offset + limit])
                return "".join(lines[offset:])
        except UnicodeDecodeError:
            # Try binary mode with error handling
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

    # ========================================================================
    # File: Write
    # Reference: packages/opencode/src/tool/write.ts
    # ========================================================================

    def write_file(self, filepath: str, content: str) -> str:
        """Write content to a file, creating directories as needed.

        Reference: packages/opencode/src/tool/write.ts

        Args:
            filepath: Path to the file
            content: Content to write

        Returns:
            Success message
        """
        path = self._resolve_path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Written to {filepath}"

    # ========================================================================
    # File: Edit
    # Reference: packages/opencode/src/tool/edit.ts
    # ========================================================================

    def edit_file(
        self,
        filepath: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> str:
        """Make a targeted edit to a file.

        Reference: packages/opencode/src/tool/edit.ts

        Args:
            filepath: Path to the file
            old_string: String to replace
            new_string: Replacement string
            replace_all: Replace all occurrences

        Returns:
            Success message
        """
        content = self.read_file(filepath)

        if replace_all:
            new_content = content.replace(old_string, new_string)
            count = content.count(old_string)
        else:
            # Only replace first occurrence (must be unique)
            if content.count(old_string) > 1:
                return f"Error: '{old_string}' appears {content.count(old_string)} times. Use replace_all=True or make old_string more unique."
            new_content = content.replace(old_string, new_string, 1)
            count = 1

        self.write_file(filepath, new_content)
        return f"Replaced {count} occurrence(s) in {filepath}"

    # ========================================================================
    # File: Glob
    # Reference: packages/opencode/src/tool/glob.ts
    # ========================================================================

    def glob_files(self, pattern: str, path: str = ".") -> list[str]:
        """Find files matching a pattern.

        Reference: packages/opencode/src/tool/glob.ts

        Args:
            pattern: Glob pattern (e.g., "**/*.py", "*.md")
            path: Root directory for search

        Returns:
            List of matching file paths
        """
        search_path = self._resolve_path(path)
        full_pattern = str(search_path / pattern)
        matches = glob_module.glob(full_pattern, recursive=True)

        # Return relative paths
        return [
            str(Path(m).relative_to(self.project_dir))
            for m in matches
            if Path(m).is_file()
        ]

    # ========================================================================
    # File: Grep
    # Reference: packages/opencode/src/tool/grep.ts
    # ========================================================================

    def grep_files(
        self,
        pattern: str,
        path: str = ".",
        glob_pattern: str = "**/*",
        case_insensitive: bool = False,
    ) -> list[dict]:
        """Search for a pattern in files.

        Reference: packages/opencode/src/tool/grep.ts

        Args:
            pattern: Regex pattern to search for
            path: Root directory for search
            glob_pattern: File pattern to match
            case_insensitive: Case-insensitive search

        Returns:
            List of matches with file, line, content
        """
        flags = re.IGNORECASE if case_insensitive else 0
        regex = re.compile(pattern, flags)
        matches = []

        search_path = self._resolve_path(path)

        for filepath in search_path.rglob(glob_pattern):
            # Skip directories and skipped dirs
            if (
                not filepath.is_file()
                or any(skip in filepath.parts for skip in SKIP_DIRS)
            ):
                continue

            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            rel_path = filepath.relative_to(self.project_dir)
                            matches.append({
                                "file": str(rel_path),
                                "line": line_num,
                                "content": line.strip(),
                            })
            except (UnicodeDecodeError, PermissionError):
                continue

        return matches

    # ========================================================================
    # System: Bash
    # Reference: packages/opencode/src/tool/bash.ts
    # ========================================================================

    def bash_command(
        self,
        command: str,
        cwd: str | None = None,
        timeout: int = 30,
    ) -> dict:
        """Execute a bash command.

        Reference: packages/opencode/src/tool/bash.txt

        Args:
            command: Shell command to execute
            cwd: Working directory (relative to project_dir)
            timeout: Timeout in seconds

        Returns:
            Dict with stdout, stderr, returncode
        """
        work_dir = self._resolve_path(cwd) if cwd else self.project_dir

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=work_dir,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "returncode": -1,
            }

    # ========================================================================
    # Utility methods
    # ========================================================================

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to project_dir."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.project_dir / p
