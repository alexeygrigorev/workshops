"""
Helper functions for readable assertions in tests.
"""


def get_tool_calls(result):
    """Extract tool names from the result.

    Returns a list of tool names that were called.
    """
    if not result:
        return []

    tool_calls = []

    for msg in result.all_messages:
        msg_dict = msg.model_dump() if hasattr(msg, 'model_dump') else msg
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc is None:
                    continue
                func = tc.function if hasattr(tc, 'function') else tc.get('function', {})
                name = func.name if hasattr(func, 'name') else func.get('name', 'unknown')
                tool_calls.append(name)
        elif isinstance(msg_dict, dict) and msg_dict.get('tool_calls'):
            for tc in msg_dict['tool_calls']:
                if tc is None:
                    continue
                func = tc.get('function', {}) if isinstance(tc, dict) else {}
                if func:
                    tool_calls.append(func.get('name', 'unknown'))

    return tool_calls


def get_tool_calls_with_args(result):
    """Extract tool calls with their arguments from the result.

    Returns a list of dicts with 'name' and 'args' keys.
    """
    if not result:
        return []

    calls = []

    for msg in result.all_messages:
        msg_dict = msg.model_dump() if hasattr(msg, 'model_dump') else msg

        # Handle tool_calls attribute
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc is None:
                    continue
                func = tc.function if hasattr(tc, 'function') else tc.get('function', {})
                name = func.name if hasattr(func, 'name') else func.get('name', 'unknown')
                args_str = func.arguments if hasattr(func, 'arguments') else func.get('arguments', '{}')

                import json
                try:
                    args_dict = json.loads(args_str)
                    args_formatted = json.dumps(args_dict)
                except:
                    args_formatted = args_str

                calls.append({'name': name, 'args': args_formatted})

        # Handle dict format
        elif isinstance(msg_dict, dict) and msg_dict.get('tool_calls'):
            for tc in msg_dict['tool_calls']:
                if tc is None:
                    continue
                if isinstance(tc, dict):
                    func = tc.get('function', {})
                    name = func.get('name', 'unknown')
                    args_str = func.get('arguments', '{}')
                    calls.append({'name': name, 'args': args_str})

    return calls


def assert_skill_called(calls, skill_name):
    """Assert that a specific skill was called.

    Args:
        calls: List of tool calls with args
        skill_name: Expected skill name (uses underscores, e.g., 'coding_standards')

    Raises:
        AssertionError: If skill was not called
    """
    skill_calls = [c for c in calls if c['name'] == 'skill']
    assert len(skill_calls) >= 1, f"Expected skill tool to be called, got: {[c['name'] for c in calls]}"

    skill_args = skill_calls[0]['args']
    # Check for quoted version (double or single quotes)
    if f'"{skill_name}"' in skill_args or f"'{skill_name}'" in skill_args:
        return

    raise AssertionError(
        f"Expected skill '{skill_name}' to be called, got skill args: {skill_args}"
    )


def assert_tool_called(calls, tool_name):
    """Assert that a specific tool was called.

    Args:
        calls: List of tool calls with args
        tool_name: Name of the tool (e.g., 'read_file', 'bash_command')

    Returns:
        The tool call dict

    Raises:
        AssertionError: If tool was not called
    """
    for call in calls:
        if call['name'] == tool_name:
            return call

    raise AssertionError(
        f"Expected tool '{tool_name}' to be called, got: {[c['name'] for c in calls]}"
    )


def assert_read_file_called(calls, file_pattern):
    """Assert that read_file was called for a specific file.

    Args:
        calls: List of tool calls with args
        file_pattern: Pattern to match in file path (e.g., 'function_template')

    Raises:
        AssertionError: If read_file was not called or file doesn't match
    """
    call = assert_tool_called(calls, 'read_file')
    assert file_pattern.lower() in call['args'].lower(), \
        f"Expected read_file for '{file_pattern}', got args: {call['args']}"


def assert_bash_command_called(calls, command_pattern):
    """Assert that bash_command was called with a specific command.

    Args:
        calls: List of tool calls with args
        command_pattern: Pattern to match in command (e.g., 'check_standards')

    Raises:
        AssertionError: If bash_command was not called or command doesn't match
    """
    call = assert_tool_called(calls, 'bash_command')
    assert command_pattern.lower() in call['args'].lower(), \
        f"Expected bash_command with '{command_pattern}', got args: {call['args']}"


def print_tool_calls(result):
    """Print tool calls from the result."""
    tool_calls = get_tool_calls(result)
    print(f"\n  Tool calls made: {tool_calls if tool_calls else '(none)'}")
