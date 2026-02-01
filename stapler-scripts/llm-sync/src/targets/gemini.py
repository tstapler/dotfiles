import yaml
from pathlib import Path
from typing import List, Optional
from core import Agent, Skill, Command, SyncTarget
from mappings import GEMINI_TOOLS
from rich.console import Console

console = Console()

class GeminiTarget(SyncTarget):
    def __init__(self, agents_dir: Optional[Path] = None, skills_dir: Optional[Path] = None, commands_dir: Optional[Path] = None):
        self.agents_dir = agents_dir or Path.home() / ".gemini" / "agents"
        self.skills_dir = skills_dir or Path.home() / ".gemini" / "skills"
        self.commands_dir = commands_dir or Path.home() / ".gemini" / "commands"

    def save_agents(self, agents: List[Agent], dry_run: bool = False, force: bool = False) -> int:
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0
        
        for agent in agents:
            # Gemini sub-agents are .md files with YAML frontmatter
            agent_file = self.agents_dir / f"{agent.name}.md"
            
            if agent_file.exists() and not force:
                console.print(f"[yellow]Skipping agent {agent.name} (exists). Use --force to overwrite.[/yellow]")
                continue
                
            # Construct YAML frontmatter
            enabled_tools = [t for t, enabled in agent.tools.items() if enabled and t in GEMINI_TOOLS]
            
            frontmatter = {
                'name': agent.name,
                'description': agent.description,
            }
            
            if enabled_tools:
                frontmatter['tools'] = enabled_tools
                
            for key in ['model', 'temperature', 'max_turns', 'timeout_mins']:
                if key in agent.metadata:
                    frontmatter[key] = agent.metadata[key]
            
            fm_yaml = yaml.dump(frontmatter, sort_keys=False)
            
            full_content = f"---\n{fm_yaml}---\n\n{agent.content}"
            
            if dry_run:
                console.print(f"[blue]Would write {agent_file}[/blue]")
            else:
                with open(agent_file, 'w', encoding='utf-8') as f:
                    f.write(full_content)
                console.print(f"[green]Saved agent {agent.name}[/green]")
                saved_count += 1
                
        return saved_count

    def save_skills(self, skills: List[Skill], dry_run: bool = False, force: bool = False) -> int:
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0
        
        for skill in skills:
            # Legacy Gemini skills are directories with a SKILL.md file
            skill_dir = self.skills_dir / skill.name
            skill_file = skill_dir / "SKILL.md"
            
            if skill_file.exists() and not force:
                console.print(f"[yellow]Skipping skill {skill.name} (exists). Use --force to overwrite.[/yellow]")
                continue
                
            frontmatter = {
                'name': skill.name,
                'description': skill.description,
            }
            
            fm_yaml = yaml.dump(frontmatter, sort_keys=False)
            full_content = f"---\n{fm_yaml}---\n\n{skill.content}"
            
            if dry_run:
                console.print(f"[blue]Would write {skill_file}[/blue]")
            else:
                skill_dir.mkdir(exist_ok=True)
                with open(skill_file, 'w', encoding='utf-8') as f:
                    f.write(full_content)
                console.print(f"[green]Saved skill {skill.name}[/green]")
                saved_count += 1
                
        return saved_count

    def save_commands(self, commands: List[Command], dry_run: bool = False, force: bool = False) -> int:
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0
        
        for cmd in commands:
            # Gemini commands are TOML files
            # Handle namespacing (e.g. "git/commit" -> git/commit.toml)
            cmd_path = self.commands_dir / f"{cmd.name}.toml"
            
            if cmd_path.exists() and not force:
                console.print(f"[yellow]Skipping command {cmd.name} (exists). Use --force to overwrite.[/yellow]")
                continue
            
            # Convert content placeholders
            # OpenCode uses $ARGUMENTS, Gemini uses {{args}}
            content = cmd.content.replace("$ARGUMENTS", "{{args}}")
            
            # Construct TOML content
            # We manually construct to ensure format is clean, or use a library if complex
            # For simple key-values, f-strings are fine and avoid extra deps
            
            # Escape backslashes, quotes, and newlines in description
            desc_safe = cmd.description.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
            
            # Construct TOML content
            # Prefer literal multi-line strings (''') to avoid escaping issues
            if "'''" not in content:
                toml_content = f'description = "{desc_safe}"\n\nprompt = \'\'\'\n{content}\n\'\'\'\n'
            else:
                # Fallback to basic multi-line strings (""") if literal quotes present
                # Must escape backslashes and triple quotes
                content_safe = content.replace('\\', '\\\\').replace('"""', '\\"\\"\\"')
                toml_content = f'description = "{desc_safe}"\n\nprompt = """\n{content_safe}\n"""\n'
            
            if dry_run:
                console.print(f"[blue]Would write {cmd_path}[/blue]")
            else:
                cmd_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cmd_path, 'w', encoding='utf-8') as f:
                    f.write(toml_content)
                console.print(f"[green]Saved command {cmd.name}[/green]")
                saved_count += 1
                
        return saved_count
