#!/usr/bin/env python3
"""
sync-claude-to-opencode.py

A tool to sync Claude Code agents to OpenCode format with automatic format translation.
Agents will inherit OpenCode's default model configuration.

Usage:
    python sync-claude-to-opencode.py [--dry-run] [--force]

Options:
    --dry-run    Show what would be done without making changes
    --force      Overwrite existing opencode agents without prompting
"""

import os
import sys
import argparse
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

class ClaudeToOpenCodeConverter:
    """Converts Claude Code agents to OpenCode agent format."""

    def __init__(self):
        self.claude_agents_dir = Path.home() / ".claude" / "agents"
        self.opencode_agents_dir = Path.home() / ".config" / "opencode" / "agent"
        self.opencode_agents_dir.mkdir(parents=True, exist_ok=True)

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

                    # Fix common YAML issues in Claude agents
                    frontmatter = self._fix_yaml_issues(frontmatter)

                    # Parse YAML frontmatter
                    try:
                        metadata = yaml.safe_load(frontmatter)
                        metadata['_content'] = agent_content
                        return metadata
                    except yaml.YAMLError as e:
                        print(f"Error parsing YAML in {agent_file}: {e}")
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

    def _fix_yaml_issues(self, frontmatter: str) -> str:
        """Fix common YAML issues found in Claude agents."""
        # Fix tools: * which is invalid YAML (interpreted as alias)
        frontmatter = frontmatter.replace('tools: *', 'tools: all')

        # Handle multi-line tools that might be problematic
        return frontmatter

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

    def generate_opencode_markdown(self, agent_data: Dict[str, Any]) -> str:
        """Generate OpenCode markdown format from agent data."""
        frontmatter = {}

        # Copy relevant fields
        for key in ['description', 'mode', 'model', 'temperature', 'tools']:
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

    def sync_agents(self, dry_run: bool = False, force: bool = False):
        """Sync all Claude Code agents to OpenCode format."""
        if not self.claude_agents_dir.exists():
            print(f"Claude agents directory not found: {self.claude_agents_dir}")
            return

        print(f"Scanning Claude agents in: {self.claude_agents_dir}")
        print(f"Target OpenCode agents directory: {self.opencode_agents_dir}")

        agent_files = list(self.claude_agents_dir.glob("*.md"))
        if not agent_files:
            print("No Claude agent files found.")
            return

        print(f"Found {len(agent_files)} Claude agent files")

        synced_count = 0
        skipped_count = 0

        for agent_file in agent_files:
            if agent_file.name in ['CLAUDE.md', 'AGENTS.md']:  # Skip metadata files
                continue

            print(f"\nProcessing: {agent_file.name}")

            # Load Claude agent
            claude_metadata = self.load_claude_agent(agent_file)
            if not claude_metadata:
                print(f"  ❌ Failed to load Claude agent: {agent_file.name}")
                continue

            agent_name = claude_metadata.get('name', agent_file.stem)
            opencode_file = self.opencode_agents_dir / f"{agent_name}.md"

            # Check if target exists
            if opencode_file.exists() and not force:
                response = input(f"  ⚠️  OpenCode agent '{agent_name}.md' already exists. Overwrite? (y/N): ")
                if response.lower() != 'y':
                    print(f"  ⏭️  Skipping: {agent_name}")
                    skipped_count += 1
                    continue

            # Convert to OpenCode format
            opencode_data = self.convert_agent(claude_metadata)
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
                    with open(opencode_file, 'w', encoding='utf-8') as f:
                        f.write(opencode_content)
                    print(f"  ✅ Created: {opencode_file}")
                    synced_count += 1
                except Exception as e:
                    print(f"  ❌ Failed to write {opencode_file}: {e}")

        print(f"\n{'🎭 Dry run completed' if dry_run else '✨ Sync completed'}")
        print(f"📊 Synced: {synced_count} agents")
        print(f"⏭️  Skipped: {skipped_count} agents")

def main():
    parser = argparse.ArgumentParser(description="Sync Claude Code agents to OpenCode format")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be done without making changes")
    parser.add_argument('--force', action='store_true', help="Overwrite existing OpenCode agents without prompting")

    args = parser.parse_args()

    converter = ClaudeToOpenCodeConverter()
    converter.sync_agents(dry_run=args.dry_run, force=args.force)

if __name__ == '__main__':
    main()