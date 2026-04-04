from typing import Dict, List, Set

# Canonical list of Gemini tools
GEMINI_TOOLS: Set[str] = {
    'list_directory',
    'read_file',
    'read_many_files',
    'write_file',
    'glob',
    'grep_search',
    'replace',
    'run_shell_command',
    'web_fetch',
    'google_web_search',
    'save_memory',
    'write_todos',
    'activate_skill',
    'ask_user',
    'enter_plan_mode',
    'exit_plan_mode',
    'get_internal_docs',
}

# Mapping from Claude tool names (and common aliases) to Gemini tool names
CLAUDE_TO_GEMINI_TOOL_MAP: Dict[str, str] = {
    # File System
    'read': 'read_file',
    'read_file': 'read_file',
    'read_many_files': 'read_many_files',
    'write': 'write_file',
    'write_file': 'write_file',
    'edit': 'replace',
    'replace': 'replace',
    'ls': 'list_directory',
    'list_directory': 'list_directory',
    'glob': 'glob',
    'grep': 'grep_search',
    'search': 'grep_search',
    'search_file_content': 'grep_search',
    
    # Shell
    'bash': 'run_shell_command',
    'run_shell_command': 'run_shell_command',
    'sh': 'run_shell_command',
    'shell': 'run_shell_command',
    'cmd': 'run_shell_command',
    
    # Web
    'webfetch': 'web_fetch',
    'web_fetch': 'web_fetch',
    'google_search': 'google_web_search',
    'google_web_search': 'google_web_search',
    'search_web': 'google_web_search',
    
    # Task/Memory/Interaction
    'task': 'write_todos',
    'todo': 'write_todos',
    'memory': 'save_memory',
    'remember': 'save_memory',
    'ask': 'ask_user',
    'ask_user': 'ask_user',
    'question': 'ask_user',
    
    # Coordination
    'activate_skill': 'activate_skill',
    'skill': 'activate_skill'
}

def map_tool(tool_name: str) -> str:
    """Normalize a tool name to its Gemini equivalent, or return None if unknown."""
    norm = tool_name.lower().strip()
    return CLAUDE_TO_GEMINI_TOOL_MAP.get(norm)
