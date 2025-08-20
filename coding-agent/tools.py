"""
Tool functions and their descriptions for the coding agent.
"""

from pathlib import Path
import os
import subprocess


class AgentTools:
    # Directories to skip when building file tree
    SKIP_DIRS = {
        ".venv",
        "__pycache__",
        ".git",
        ".pytest_cache",
        ".mypy_cache",
        ".coverage",
        "node_modules",
        ".DS_Store",
    }

    def __init__(self, project_dir: Path):
        """
        Initialize AgentTools with the given project directory.

        Parameters:
            project_dir (Path): The root directory of the project.
        """
        self.project_dir = project_dir

    def read_file(self, filepath: str) -> None:
        """
        Read and return the contents of a file at the given relative filepath.

        Parameters:
            filepath (str): Path to the file, relative to the project directory.
        Returns:
            str: Contents of the file.
        """
        abs_path = self.project_dir / filepath
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, filepath: str, content: str) -> None:
        """
        Write the given content to a file at the given relative filepath, creating directories as needed.

        Parameters:
            filepath (str): Path to the file, relative to the project directory.
            content (str): Content to write to the file.
        Returns:
            None
        """
        abs_path = self.project_dir / filepath
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)

    def see_file_tree(self, root_dir: str = ".") -> list[str]:
        """
        Return a list of all files and directories under the given root directory,
        relative to the project directory.

        Parameters:
            root_dir (str): Root directory to list from, relative to the project directory.
                           Defaults to ".".
        Returns:
            list[str]: List of relative paths for all files and directories.
        """
        abs_root = self.project_dir / root_dir
        tree = []

        for dirpath, dirnames, filenames in os.walk(abs_root):
            # Remove blacklisted directories from dirnames to prevent os.walk from entering them
            for skip_dir in list(dirnames):
                if skip_dir in self.SKIP_DIRS:
                    dirnames.remove(skip_dir)

            for name in dirnames + filenames:
                full_path = os.path.join(dirpath, name)
                rel_path = os.path.relpath(full_path, self.project_dir)
                tree.append(rel_path)

        return tree

    def execute_bash_command(
        self, command: str, cwd: str = None
    ) -> tuple[str, str, int]:
        """
        Execute a bash command in the shell and return its output, error, and exit code. Blocks running the Django development server (runserver).

        Parameters:
            command (str): The bash command to execute.
            cwd (str, optional): Working directory to run the command in, relative to the project directory. Defaults to None.
        Returns:
            tuple: (stdout (str), stderr (str), returncode (int))
        """
        # Block running the Django development server
        if "runserver" in command:
            return (
                "",
                "Error: Running the Django development server (runserver) is not allowed through this tool.",
                1,
            )

        abs_cwd = (self.project_dir / cwd) if cwd else self.project_dir

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=abs_cwd,
            timeout=15,
            encoding='utf-8',
            errors='replace',
        )

        return result.stdout, result.stderr, result.returncode

    def search_in_files(
        self, pattern: str, root_dir: str = "."
    ) -> list[tuple[str, int, str]]:
        """
        Search for a pattern in all files under the given root directory and return a list of matches as (relative path, line number, line content).

        Parameters:
            pattern (str): Pattern to search for in files.
            root_dir (str): Root directory to search from, relative to the project directory. Defaults to ".".
        Returns:
            list[tuple]: List of (relative path, line number, line content) for each match.
        """
        abs_root = self.project_dir / root_dir
        matches = []
        for dirpath, _, filenames in os.walk(abs_root):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for i, line in enumerate(f, 1):
                            if pattern in line:
                                rel_path = os.path.relpath(filepath, self.project_dir)
                                matches.append((rel_path, i, line.strip()))
                except Exception:
                    continue
        return matches
