# start_agent.py
"""
Coding Agent Starter Script

This script initializes a coding agent that can modify the Django project using a provided template.

Developer Prompt:
You are a coding agent. Your job is to modify the Django project according to user instructions, using the provided template as a reference. You can read, write, and search files, view the file tree, and execute bash commands. Always ensure changes are consistent with Django best practices and the project’s structure.
"""

from chat_assistant import Tools, ChatInterface, ChatAssistant
import tools
from openai import OpenAI

# Developer prompt
DEVELOPER_PROMPT = (
    "You are a coding agent. Your job is to modify the Django project according to user instructions, "
    "using the provided template as a reference. You can read, write, and search files, view the file tree, "
    "and execute bash commands. Always ensure changes are consistent with Django best practices and the project’s structure."
)

if __name__ == "__main__":
    tools_obj = Tools()
    tools_obj.add_tool(tools.read_file, tools.read_file_tool)
    tools_obj.add_tool(tools.write_file, tools.write_file_tool)
    tools_obj.add_tool(tools.see_file_tree, tools.see_file_tree_tool)
    tools_obj.add_tool(tools.execute_bash_command, tools.execute_bash_command_tool)
    tools_obj.add_tool(tools.search_in_files, tools.search_in_files_tool)

    chat_interface = ChatInterface()
    client = OpenAI()
    chat_assistant = ChatAssistant(tools_obj, DEVELOPER_PROMPT, chat_interface, client)

    print("Coding Agent Initialized.")
    print("Developer Prompt:\n", DEVELOPER_PROMPT)
    print("\nAvailable tools: read_file, write_file, see_file_tree, execute_bash_command, search_in_files")
    # Ready for further extension (CLI, web interface, ChatAssistant integration, etc.) 