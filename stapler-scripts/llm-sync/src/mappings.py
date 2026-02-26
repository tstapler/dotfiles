from typing import Dict, List, Set

# Canonical list of Gemini tools
GEMINI_TOOLS: Set[str] = {
    'list_directory',
    'read_file',
    'write_file',
    'glob',
    'search_file_content',
    'replace',
    'run_shell_command',
    'web_fetch',
    'google_web_search',
    'save_memory',
    'write_todos',
    'delegate_to_agent',
    'activate_skill'
}

# Mapping from Claude tool names (and common aliases) to Gemini tool names
CLAUDE_TO_GEMINI_TOOL_MAP: Dict[str, str] = {
    # File System
    'read': 'read_file',
    'read_file': 'read_file',
    'write': 'write_file',
    'write_file': 'write_file',
    'edit': 'replace',
    'replace': 'replace',
    'ls': 'list_directory',
    'list_directory': 'list_directory',
    'glob': 'glob',
    'grep': 'search_file_content',
    'search': 'search_file_content',

    # Shell
    'bash': 'run_shell_command',
    'run_shell_command': 'run_shell_command',
    'sh': 'run_shell_command',

    # Web
    'webfetch': 'web_fetch',
    'web_fetch': 'web_fetch',
    'google_search': 'google_web_search',
    'google_web_search': 'google_web_search',

    # Task/Memory
    'task': 'write_todos',
    'todo': 'write_todos',
    'memory': 'save_memory',
    'remember': 'save_memory'
}

def map_tool(tool_name: str) -> str:
    """Normalize a tool name to its Gemini equivalent, or return None if unknown."""
    norm = tool_name.lower().strip()
    return CLAUDE_TO_GEMINI_TOOL_MAP.get(norm)
