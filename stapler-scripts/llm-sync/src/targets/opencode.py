import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from core import Agent, Skill, Command, SyncTarget
from mappings import map_tool
from rich.console import Console

console = Console()

class OpenCodeTarget(SyncTarget):
    def __init__(self, agents_dir: Optional[Path] = None, commands_dir: Optional[Path] = None):
        self.agents_dir = agents_dir or Path.home() / ".config" / "opencode" / "agents"
        self.commands_dir = commands_dir or Path.home() / ".config" / "opencode" / "commands"

    def save_agents(self, agents: List[Agent], dry_run: bool = False, force: bool = False) -> int:
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0

        for agent in agents:
            # OpenCode agents are single .md files
            agent_file = self.agents_dir / f"{agent.name}.md"

            if agent_file.exists() and not force:
                console.print(f"[yellow]Skipping agent {agent.name} (exists). Use --force to overwrite.[/yellow]")
                continue

            opencode_tools = {t: True for t, enabled in agent.tools.items() if enabled}

            frontmatter = {
                'description': agent.description,
                'mode': 'subagent',
                'temperature': 0.1,
                'tools': opencode_tools
            }

            for key in ['model', 'temperature', 'max_steps', 'permission', 'color', 'arguments']:
                if key in agent.metadata:
                    frontmatter[key] = agent.metadata[key]

            fm_yaml = yaml.dump(frontmatter, sort_keys=False, allow_unicode=True)
            content = f"---\n{fm_yaml}---\n\n{agent.content}"

            if dry_run:
                console.print(f"[blue]Would write {agent_file}[/blue]")
            else:
                with open(agent_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                console.print(f"[green]Saved agent {agent.name} to OpenCode[/green]")
                saved_count += 1

        return saved_count

    def save_skills(self, skills: List[Skill], dry_run: bool = False, force: bool = False) -> int:
        # OpenCode doesn't have a distinct "Skill" concept like legacy Gemini,
        # so we map them to agents but maybe with different metadata or mode.
        agents = [Agent(name=s.name, description=s.description, content=s.content, tools=s.tools, metadata=s.metadata) for s in skills]
        return self.save_agents(agents, dry_run=dry_run, force=force)

    def save_commands(self, commands: List[Command], dry_run: bool = False, force: bool = False) -> int:
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0

        for cmd in commands:
            # OpenCode commands are .md files
            cmd_path = self.commands_dir / f"{cmd.name}.md"

            if cmd_path.exists() and not force:
                console.print(f"[yellow]Skipping command {cmd.name} (exists). Use --force to overwrite.[/yellow]")
                continue

            # Convert content placeholders
            # Gemini uses {{args}}, OpenCode uses $ARGUMENTS
            content = cmd.content.replace("{{args}}", "$ARGUMENTS")

            frontmatter = {
                'description': cmd.description
            }

            if 'arguments' in cmd.metadata:
                frontmatter['arguments'] = cmd.metadata['arguments']

            fm_yaml = yaml.dump(frontmatter, sort_keys=False, allow_unicode=True)

            full_content = f"---\n{fm_yaml}---\n\n{content}"

            if dry_run:
                console.print(f"[blue]Would write {cmd_path}[/blue]")
            else:
                cmd_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cmd_path, 'w', encoding='utf-8') as f:
                    f.write(full_content)
                console.print(f"[green]Saved command {cmd.name} to OpenCode[/green]")
                saved_count += 1

        return saved_count
