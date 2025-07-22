# tools.py
"""
Tool functions and their descriptions for the coding agent.
"""

import os
import subprocess

# Tool: Read file
def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

read_file_tool = {
    "type": "function",
    "name": "read_file",
    "description": "Read the contents of a file at the given path.",
    "parameters": {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Path to the file to read."
            }
        },
        "required": ["filepath"],
        "additionalProperties": False
    }
}

# Tool: Write file
def write_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

write_file_tool = {
    "type": "function",
    "name": "write_file",
    "description": "Write content to a file at the given path, overwriting if it exists.",
    "parameters": {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Path to the file to write."
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

# Tool: See file tree
def see_file_tree(root_dir='.'): 
    tree = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for name in dirnames + filenames:
            rel_path = os.path.relpath(os.path.join(dirpath, name), root_dir)
            tree.append(rel_path)
    return tree

see_file_tree_tool = {
    "type": "function",
    "name": "see_file_tree",
    "description": "List all files and directories under the given root directory.",
    "parameters": {
        "type": "object",
        "properties": {
            "root_dir": {
                "type": "string",
                "description": "Root directory to list the file tree from.",
                "default": "."
            }
        },
        "required": [],
        "additionalProperties": False
    }
}

# Tool: Execute bash command
def execute_bash_command(command, cwd=None):
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.stdout, result.stderr, result.returncode

execute_bash_command_tool = {
    "type": "function",
    "name": "execute_bash_command",
    "description": "Execute a bash command in the shell and return its output, error, and exit code.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute."
            },
            "cwd": {
                "type": "string",
                "description": "The working directory to run the command in.",
                "default": None
            }
        },
        "required": ["command"],
        "additionalProperties": False
    }
}

# Tool: Search in files (simple grep)
def search_in_files(pattern, root_dir='.'): 
    matches = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        if pattern in line:
                            matches.append((filepath, i, line.strip()))
            except Exception:
                continue
    return matches

search_in_files_tool = {
    "type": "function",
    "name": "search_in_files",
    "description": "Search for a pattern in all files under the given root directory.",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Pattern to search for in files."
            },
            "root_dir": {
                "type": "string",
                "description": "Root directory to search from.",
                "default": "."
            }
        },
        "required": ["pattern"],
        "additionalProperties": False
    }
} 