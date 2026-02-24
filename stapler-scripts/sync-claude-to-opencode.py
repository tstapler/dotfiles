#!/usr/bin/env python3
"""
sync-claude-to-opencode.py

A tool to sync Claude Code agents and commands to OpenCode format with automatic format translation.
Agents and commands will inherit OpenCode's default model configuration.

Usage:
    python sync-claude-to-opencode.py [--dry-run] [--force]

Options:
    --dry-run    Show what would be done without making changes
    --force      Overwrite existing opencode agents/commands without prompting
"""
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "pyyaml",
# ]
# ///

import os
import sys
import argparse
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

class ClaudeToOpenCodeConverter:
    """Converts Claude Code agents/commands to OpenCode agent/command format."""

    def __init__(self):
        # Support both global agents and project-specific commands
        self.claude_agents_dir = Path.home() / ".claude" / "agents"
        self.claude_commands_dir = Path.home() / "Documents" / "personal-wiki" / ".claude" / "commands"
        self.opencode_agents_dir = Path.home() / ".config" / "opencode" / "agent"
        self.opencode_commands_dir = Path.home() / "Documents" / "personal-wiki" / ".opencode" / "commands"
        self.opencode_agents_dir.mkdir(parents=True, exist_ok=True)
        self.opencode_commands_dir.mkdir(parents=True, exist_ok=True)

    def load_claude_agent(self, agent_file: Path) -> Optional[Dict[str, Any]]:
        """Load and parse a Claude Code agent file."""
        try:
            with open(agent_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split frontmatter from content
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = parts[1].strip()
                    agent_content = parts[2].strip()

                    # Try to parse with YAML first
                    try:
                        metadata = yaml.safe_load(frontmatter)
                        metadata['_content'] = agent_content
                        return metadata
                    except yaml.YAMLError:
                        # If YAML parsing fails, try manual parsing
                        metadata = self._parse_frontmatter_manually(frontmatter)
                        if metadata:
                            metadata['_content'] = agent_content
                            return metadata
                        else:
                            print(f"Error parsing YAML in {agent_file}: YAML parsing failed and manual parsing failed")
                            return None
                else:
                    print(f"Invalid frontmatter format in {agent_file}")
                    return None
            else:
                print(f"No frontmatter found in {agent_file}")
                return None

        except Exception as e:
            print(f"Error reading {agent_file}: {e}")
            return None

    def _parse_frontmatter_manually(self, frontmatter: str) -> Optional[Dict[str, Any]]:
        """Manually parse frontmatter when YAML parsing fails."""
        lines = frontmatter.split('\n')
        metadata = {}
        current_key = None
        current_value_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for key: value pattern
            if ':' in line and not line.startswith(' '):
                # Save previous key-value pair
                if current_key:
                    value = '\n'.join(current_value_lines).strip()
                    if current_key == 'tools':
                        # Special handling for tools
                        metadata[current_key] = self._parse_tools_value(value)
                    else:
                        metadata[current_key] = value

                # Start new key-value pair
                parts = line.split(':', 1)
                current_key = parts[0].strip()
                value_start = parts[1].strip() if len(parts) > 1 else ''
                current_value_lines = [value_start]
            elif current_key and line.startswith(' '):
                # Continuation of multi-line value
                current_value_lines.append(line)
            elif line.strip() == '':
                # Empty line - could be separator
                pass
            else:
                # Unexpected line, might be malformed
                pass

            i += 1

        # Save the last key-value pair
        if current_key:
            value = '\n'.join(current_value_lines).strip()
            if current_key == 'tools':
                metadata[current_key] = self._parse_tools_value(value)
            else:
                metadata[current_key] = value

        return metadata if metadata else None

    def _parse_tools_value(self, tools_str: str) -> Any:
        """Parse tools value which might be a string, list, or special syntax."""
        tools_str = tools_str.strip()
        if tools_str == '*' or tools_str == 'all':
            return 'all'
        elif ',' in tools_str:
            return [t.strip() for t in tools_str.split(',')]
        elif tools_str:
            return tools_str
        else:
            return []

    def _fix_yaml_issues(self, frontmatter: str) -> str:
        """Fix common YAML issues found in Claude agents."""
        # Fix tools: * which is invalid YAML (interpreted as alias)
        frontmatter = frontmatter.replace('tools: *', 'tools: all')

        # Handle complex multi-line descriptions with examples and colons
        # The Claude agents have descriptions followed by "Examples:" sections that break YAML
        # We need to extract only the actual description text

        lines = frontmatter.split('\n')
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            if line.strip().startswith('description:'):
                # Start of description field
                desc_parts = []
                desc_start = line.split(':', 1)[1].strip()

                if desc_start:
                    desc_parts.append(desc_start)

                i += 1
                # Collect description lines until we hit a line that looks like a new top-level key
                # or "Examples:" which indicates the end of the description
                while i < len(lines):
                    next_line = lines[i]
                    next_line_stripped = next_line.strip()

                    # Stop if we hit "Examples:" or another top-level key (word: not indented)
                    if next_line_stripped.startswith('Examples:') or \
                       (next_line_stripped and not next_line.startswith(' ') and ':' in next_line_stripped and not next_line_stripped.startswith('-')):
                        break

                    desc_parts.append(next_line)
                    i += 1

                # Join the description and properly format it for YAML
                description = '\n'.join(desc_parts).strip()
                if description:
                    # Use literal block for multi-line descriptions
                    fixed_lines.append('description: |')
                    for desc_line in description.split('\n'):
                        fixed_lines.append(f'  {desc_line}')
                else:
                    fixed_lines.append('description: ""')

                # Don't increment i here as we've already consumed the lines
                continue

            else:
                fixed_lines.append(line)
                i += 1

        return '\n'.join(fixed_lines)

    def convert_tools_format(self, claude_tools: Any) -> Dict[str, bool]:
        """Convert Claude Code tools format to OpenCode tools format."""
        opencode_tools = {}

        # Claude tool name to OpenCode tool name mapping
        tool_mapping = {
            'bash': 'bash',
            'read': 'read',
            'write': 'write',
            'edit': 'edit',
            'glob': 'glob',
            'grep': 'grep',
            'webfetch': 'webfetch',
            'task': 'task',
            'todowrite': 'todowrite',
            'todoread': 'todoread',
            # Case variations
            'Bash': 'bash',
            'Read': 'read',
            'Write': 'write',
            'Edit': 'edit',
            'Glob': 'glob',
            'Grep': 'grep',
            'WebFetch': 'webfetch',
            'Task': 'task',
            'TodoWrite': 'todowrite',
            'TodoRead': 'todoread',
        }

        # Default all known tools to False
        default_tools = {v: False for v in tool_mapping.values()}

        if claude_tools == '*' or claude_tools == 'all':
            # Enable all known tools
            opencode_tools = {k: True for k in default_tools.keys()}
        elif isinstance(claude_tools, str):
            # Parse comma-separated string
            tool_names = [t.strip() for t in claude_tools.split(',')]
            for tool in tool_names:
                tool = tool.strip()
                if tool == '*' or tool == 'all':
                    opencode_tools = {k: True for k in default_tools.keys()}
                    break
                elif tool in tool_mapping:
                    mapped_tool = tool_mapping[tool]
                    opencode_tools[mapped_tool] = True
                else:
                    # Skip unknown tools quietly for MCP tools and other extensions
                    pass
        elif isinstance(claude_tools, list):
            # Handle array format
            for tool in claude_tools:
                tool = str(tool).strip()
                if tool == '*' or tool == 'all':
                    opencode_tools = {k: True for k in default_tools.keys()}
                    break
                elif tool in tool_mapping:
                    mapped_tool = tool_mapping[tool]
                    opencode_tools[mapped_tool] = True
                else:
                    # Skip unknown tools quietly
                    pass

        # Merge with defaults
        result = default_tools.copy()
        result.update(opencode_tools)
        return result



    def convert_agent(self, claude_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Claude Code agent metadata to OpenCode format."""
        opencode_agent = {}

        # Required fields
        opencode_agent['description'] = claude_metadata.get('description', 'Converted from Claude Code agent')

        # Optional fields with defaults
        opencode_agent['mode'] = 'subagent'  # Most Claude agents are specialized
        # Skip model field to use OpenCode's default model configuration
        opencode_agent['temperature'] = 0.1  # Low temperature for consistency

        # Convert tools
        claude_tools = claude_metadata.get('tools', [])
        opencode_agent['tools'] = self.convert_tools_format(claude_tools)

        # Add content
        opencode_agent['_content'] = claude_metadata.get('_content', '')

        return opencode_agent

    def convert_command(self, claude_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Claude Code command metadata to OpenCode format."""
        opencode_command = {}

        # Required fields - map title to description
        title = claude_metadata.get('title', '')
        description = claude_metadata.get('description', '')
        if title:
            opencode_command['description'] = f"{title}: {description}" if description else title
        else:
            opencode_command['description'] = description or 'Converted from Claude Code command'

        # Optional fields with defaults
        opencode_command['mode'] = 'command'  # This is a command, not an agent
        # Skip model field to use OpenCode's default model configuration
        opencode_command['temperature'] = 0.1  # Low temperature for consistency

        # Convert tools
        claude_tools = claude_metadata.get('tools', [])
        opencode_command['tools'] = self.convert_tools_format(claude_tools)

        # Add arguments if present
        arguments = claude_metadata.get('arguments', [])
        if arguments:
            opencode_command['arguments'] = arguments

        # Add content
        opencode_command['_content'] = claude_metadata.get('_content', '')

        return opencode_command

    def generate_opencode_markdown(self, agent_data: Dict[str, Any]) -> str:
        """Generate OpenCode markdown format from agent data."""
        frontmatter = {}

        # Copy relevant fields
        for key in ['description', 'mode', 'model', 'temperature', 'tools', 'arguments']:
            if key in agent_data:
                frontmatter[key] = agent_data[key]

        # Generate YAML frontmatter
        frontmatter_yaml = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)

        # Combine with content
        content = agent_data.get('_content', '')
        if content:
            return f"---\n{frontmatter_yaml}---\n\n{content}"
        else:
            return f"---\n{frontmatter_yaml}---"

    def sync_all(self, dry_run: bool = False, force: bool = False):
        """Sync all Claude Code agents and commands to OpenCode format."""
        total_synced = 0
        total_skipped = 0

        # Sync agents
        agents_synced, agents_skipped = self._sync_items(
            self.claude_agents_dir, self.opencode_agents_dir,
            "agents", self.convert_agent, dry_run, force
        )
        total_synced += agents_synced
        total_skipped += agents_skipped

        # Sync commands
        commands_synced, commands_skipped = self._sync_items(
            self.claude_commands_dir, self.opencode_commands_dir,
            "commands", self.convert_command, dry_run, force
        )
        total_synced += commands_synced
        total_skipped += commands_skipped

        print(f"\n{'🎭 Dry run completed' if dry_run else '✨ Sync completed'}")
        print(f"📊 Total synced: {total_synced}")
        print(f"⏭️  Total skipped: {total_skipped}")

    def _sync_items(self, source_dir: Path, target_dir: Path, item_type: str,
                   converter_func, dry_run: bool = False, force: bool = False):
        """Generic method to sync items (agents or commands)."""
        if not source_dir.exists():
            print(f"Claude {item_type} directory not found: {source_dir}")
            return 0, 0

        print(f"\nScanning Claude {item_type} in: {source_dir}")
        print(f"Target OpenCode {item_type} directory: {target_dir}")

        item_files = list(source_dir.glob("**/*.md"))
        if not item_files:
            print(f"No Claude {item_type} files found.")
            return 0, 0

        print(f"Found {len(item_files)} Claude {item_type} files")

        synced_count = 0
        skipped_count = 0

        for item_file in item_files:
            print(f"\nProcessing: {item_file.name}")

            # Load Claude item
            claude_metadata = self.load_claude_agent(item_file)  # Reusing the same loader
            if not claude_metadata:
                print(f"  ❌ Failed to load Claude {item_type[:-1]}: {item_file.name}")
                continue

            # For agents, use name from metadata or filename
            # For commands, preserve the directory structure and use original filename
            if item_type == "commands":
                # Preserve relative path structure
                relative_path = item_file.relative_to(source_dir)
                opencode_file = target_dir / relative_path
                item_name = str(relative_path)  # For display purposes
            else:
                # For agents, use name from metadata or filename
                item_name = claude_metadata.get('name') or item_file.stem
                opencode_file = target_dir / f"{item_name}.md"

            # Check if target exists
            if opencode_file.exists() and not force:
                response = input(f"  ⚠️  OpenCode {item_type[:-1]} '{item_name}.md' already exists. Overwrite? (y/N): ")
                if response.lower() != 'y':
                    print(f"  ⏭️  Skipping: {item_name}")
                    skipped_count += 1
                    continue

            # Convert to OpenCode format
            opencode_data = converter_func(claude_metadata)
            opencode_content = self.generate_opencode_markdown(opencode_data)

            if dry_run:
                print(f"  📝 Would create: {opencode_file}")
                print("  📋 Content preview:")
                lines = opencode_content.split('\n')[:10]
                for line in lines:
                    print(f"     {line}")
                if len(opencode_content.split('\n')) > 10:
                    print("     ...")
            else:
                try:
                    # Ensure parent directories exist
                    opencode_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(opencode_file, 'w', encoding='utf-8') as f:
                        f.write(opencode_content)
                    print(f"  ✅ Created: {opencode_file}")
                    synced_count += 1
                except Exception as e:
                    print(f"  ❌ Failed to write {opencode_file}: {e}")

        return synced_count, skipped_count

def main():
    parser = argparse.ArgumentParser(description="Sync Claude Code agents and commands to OpenCode format")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be done without making changes")
    parser.add_argument('--force', action='store_true', help="Overwrite existing OpenCode agents without prompting")

    args = parser.parse_args()

    converter = ClaudeToOpenCodeConverter()
    converter.sync_all(dry_run=args.dry_run, force=args.force)

if __name__ == '__main__':
    main()