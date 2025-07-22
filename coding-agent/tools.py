# tools.py
"""
Tool functions and their descriptions for the coding agent.
"""

from pathlib import Path
import os
import subprocess

class AgentTools:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def read_file(self, filepath):
        abs_path = self.project_dir / filepath
        with open(abs_path, 'r', encoding='utf-8') as f:
            return f.read()

    read_file_tool = {
        "type": "function",
        "name": "read_file",
        "description": "Read the contents of a file at the given path, relative to the project directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the file to read, relative to the project directory."
                }
            },
            "required": ["filepath"],
            "additionalProperties": False
        }
    }

    def write_file(self, filepath, content):
        abs_path = self.project_dir / filepath
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)

    write_file_tool = {
        "type": "function",
        "name": "write_file",
        "description": "Write content to a file at the given path, relative to the project directory, overwriting if it exists.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the file to write, relative to the project directory."
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file."
                }
            },
            "required": ["filepath", "content"],
            "additionalProperties": False
        }
    }

    def see_file_tree(self, root_dir="."):
        abs_root = self.project_dir / root_dir
        tree = []
        for dirpath, dirnames, filenames in os.walk(abs_root):
            for name in dirnames + filenames:
                rel_path = os.path.relpath(os.path.join(dirpath, name), self.project_dir)
                tree.append(rel_path)
        return tree

    see_file_tree_tool = {
        "type": "function",
        "name": "see_file_tree",
        "description": "List all files and directories under the given root directory, relative to the project directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "root_dir": {
                    "type": "string",
                    "description": "Root directory to list the file tree from, relative to the project directory.",
                    "default": "."
                }
            },
            "required": [],
            "additionalProperties": False
        }
    }

    def execute_bash_command(self, command, cwd=None):
        # Block running the Django development server
        if 'runserver' in command:
            return (
                '',
                'Error: Running the Django development server (runserver) is not allowed through this tool.',
                1
            )
        abs_cwd = (self.project_dir / cwd) if cwd else self.project_dir
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=abs_cwd)
        return result.stdout, result.stderr, result.returncode

    execute_bash_command_tool = {
        "type": "function",
        "name": "execute_bash_command",
        "description": "Execute a bash command in the shell and return its output, error, and exit code. Runs relative to the project directory by default.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute."
                },
                "cwd": {
                    "type": "string",
                    "description": "The working directory to run the command in, relative to the project directory.",
                    "default": None
                }
            },
            "required": ["command"],
            "additionalProperties": False
        }
    }

    def search_in_files(self, pattern, root_dir="."):
        abs_root = self.project_dir / root_dir
        matches = []
        for dirpath, _, filenames in os.walk(abs_root):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for i, line in enumerate(f, 1):
                            if pattern in line:
                                rel_path = os.path.relpath(filepath, self.project_dir)
                                matches.append((rel_path, i, line.strip()))
                except Exception:
                    continue
        return matches

    search_in_files_tool = {
        "type": "function",
        "name": "search_in_files",
        "description": "Search for a pattern in all files under the given root directory, relative to the project directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Pattern to search for in files."
                },
                "root_dir": {
                    "type": "string",
                    "description": "Root directory to search from, relative to the project directory.",
                    "default": "."
                }
            },
            "required": ["pattern"],
            "additionalProperties": False
        }
    } 