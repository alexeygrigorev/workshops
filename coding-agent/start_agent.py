# start_agent.py
"""
Coding Agent Starter Script

This script initializes a coding agent that can modify the Django project using a provided template.

Developer Prompt:
You are a coding agent. Your job is to modify the Django project according to user instructions, using the provided template as a reference. You can read, write, and search files, view the file tree, and execute bash commands. Always ensure changes are consistent with Django best practices and the project’s structure.
"""

import os
import shutil
from pathlib import Path
from chat_assistant import Tools, ChatInterface, ChatAssistant
import tools
from openai import OpenAI

# Developer prompt
DEVELOPER_PROMPT = """
You are a coding agent. Your task is to modify the provided Django project template
according to user instructions. You don't tell the user what to do; you do it yourself using the 
available tools. First, think about the sequence of steps you will do, and then 
execute the sequence.
Always ensure changes are consistent with Django best practices and the project’s structure.

## Project Overview

The project is a Django 5.2.4 web application scaffolded with standard best practices. It uses:
- Python 3.8+
- Django 5.2.4 (as specified in pyproject.toml)
- uv for Python environment and dependency management
- SQLite as the default database (see settings.py)
- Standard Django apps and a custom app called myapp
- HTML templates for rendering views

## File Tree

django_template/
├── .python-version
├── README.md
├── manage.py
├── pyproject.toml
├── uv.lock
├── myapp/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   │   └── __init__.py
│   ├── models.py
│   ├── templates/
│   │   └── home.html
│   ├── tests.py
│   └── views.py
├── myproject/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── templates/
    └── base.html

## Content Description

- manage.py: Standard Django management script for running commands.
- README.md: Setup and run instructions, including use of uv for dependency management.
- pyproject.toml: Project metadata and dependencies (Django 5.2.4).
- uv.lock: Lock file for reproducible Python environments.
- .python-version: Specifies the Python version for the project.
- myapp/: Custom Django app with models, views, admin, tests, and a template (home.html).
  - migrations/: Contains migration files for database schema.
- myproject/: Django project configuration (settings, URLs, WSGI/ASGI entrypoints).
  - settings.py: Configures installed apps, middleware, database (SQLite), templates, etc.
- templates/: Project-level templates, including base.html.

## Technologies Used

- Python 3.8+
- Django 5.2.4
- uv (for dependency management)
- SQLite (default database)
- HTML (Django templates)
- Standard Django project and app structure

You have full access to modify, add, or remove files and code within this structure using your available tools.
"""

if __name__ == "__main__":
    project_name = input("Enter the new Django project name: ").strip()
    if not project_name:
        print("Project name cannot be empty.")
        exit(1)
    if os.path.exists(project_name):
        print(f"Directory '{project_name}' already exists. Please choose a different name or remove the existing directory.")
        exit(1)
    shutil.copytree('django_template', project_name)
    print(f"Django template copied to '{project_name}' directory.")

    project_path = Path(project_name)
    agent_tools = tools.AgentTools(project_path)

    tools_obj = Tools()
    tools_obj.add_tool(agent_tools.read_file, agent_tools.read_file_tool)
    tools_obj.add_tool(agent_tools.write_file, agent_tools.write_file_tool)
    tools_obj.add_tool(agent_tools.see_file_tree, agent_tools.see_file_tree_tool)
    tools_obj.add_tool(agent_tools.execute_bash_command, agent_tools.execute_bash_command_tool)
    tools_obj.add_tool(agent_tools.search_in_files, agent_tools.search_in_files_tool)

    chat_interface = ChatInterface()
    client = OpenAI()
    chat_assistant = ChatAssistant(tools_obj, DEVELOPER_PROMPT, chat_interface, client)

    print("Coding Agent Initialized.")
    print("Developer Prompt:\n", DEVELOPER_PROMPT)
    print("\nAvailable tools: read_file, write_file, see_file_tree, execute_bash_command, search_in_files")
    # Ready for further extension (CLI, web interface, ChatAssistant integration, etc.) 