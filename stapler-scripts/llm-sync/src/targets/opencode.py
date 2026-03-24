import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from core import Agent, Skill, Command, SyncTarget, SyncSource, IGNORED_NAMES
from mappings import map_tool
from rich.console import Console

console = Console()

class OpenCodeTarget(SyncTarget, SyncSource):
    def __init__(self, agents_dir: Optional[Path] = None, commands_dir: Optional[Path] = None):
        self.agents_dir = agents_dir or Path.home() / ".config" / "opencode" / "agents"
        self.commands_dir = commands_dir or Path.home() / ".config" / "opencode" / "commands"

    def load_agents(self) -> List[Agent]:
        agents = []
        if self.agents_dir.exists():
            for agent_file in self.agents_dir.glob("**/*.md"):
                if agent_file.stem in IGNORED_NAMES:
                    continue
                
                rel_path = agent_file.relative_to(self.agents_dir)
                is_in_skills_dir = 'skills/' in str(rel_path).replace('\\', '/')
                if is_in_skills_dir:
                    continue

                agent = self._load_md_item(agent_file, self.agents_dir, Agent)
                if agent:
                    # Don't load if it's explicitly a skill (legacy)
                    if agent.metadata.get('mode') == 'skill':
                        continue
                    agents.append(agent)
        return agents

    def load_skills(self) -> List[Skill]:
        skills = []
        if self.agents_dir.exists():
            for agent_file in self.agents_dir.glob("**/*.md"):
                if agent_file.stem in IGNORED_NAMES:
                    continue
                
                # In OpenCode, skills are just agents in a skills/ subdirectory
                # (or legacy mode: skill)
                rel_path = agent_file.relative_to(self.agents_dir)
                is_in_skills_dir = 'skills/' in str(rel_path).replace('\\', '/')
                
                skill = self._load_md_item(agent_file, self.agents_dir, Skill)
                if skill and (is_in_skills_dir or skill.metadata.get('mode') == 'skill'):
                    # Remove skills/ prefix from name if present
                    if skill.name.startswith('skills/'):
                        skill.name = skill.name[7:]
                    skills.append(skill)
        return skills

    def load_commands(self) -> List[Command]:
        commands = []
        if self.commands_dir.exists():
            for cmd_file in self.commands_dir.glob("**/*.md"):
                if cmd_file.stem in IGNORED_NAMES:
                    continue
                cmd = self._load_md_item(cmd_file, self.commands_dir, Command)
                if cmd:
                    commands.append(cmd)
        return commands

    def _load_md_item(self, item_file: Path, base_dir: Path, cls):
        try:
            with open(item_file, 'r', encoding='utf-8') as f:
                content = f.read()

            rel_path = item_file.relative_to(base_dir)
            name = str(rel_path.with_suffix('')).replace('\\', '/')
            description = ""
            item_content = content
            metadata = {}

            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = parts[1].strip()
                    item_content = parts[2].strip()
                    try:
                        metadata = yaml.safe_load(frontmatter) or {}
                    except yaml.YAMLError:
                        metadata = {}
                    
                    name = metadata.get('name') or name
                    description = metadata.get('description', '')

            # Convert tools dict/list if present
            tools = {}
            if 'tools' in metadata:
                raw_tools = metadata['tools']
                if isinstance(raw_tools, dict):
                    tools = {t: enabled for t, enabled in raw_tools.items()}
                elif isinstance(raw_tools, list):
                    tools = {t: True for t in raw_tools}

            params = {
                'name': name,
                'description': description,
                'content': item_content,
                'metadata': metadata,
                'source_file': str(item_file)
            }
            if hasattr(cls, 'tools'):
                params['tools'] = tools

            return cls(**params)
        except Exception as e:
            console.print(f"[red]Error reading OpenCode item {item_file}: {e}[/red]")
        return None

    def save_agents(self, agents: List[Agent], dry_run: bool = False, force: bool = False) -> int:
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0
        
        for agent in agents:
            agent_file = self.agents_dir / f"{agent.name}.md"
            
            if agent_file.exists() and not force:
                continue
                
            opencode_tools = {t: True for t, enabled in agent.tools.items() if enabled}

            # Defaults
            frontmatter = {
                'description': agent.description,
                'mode': 'subagent',
                'temperature': 0.1,
                'tools': opencode_tools
            }
            
            # Metadata overrides
            for key in ['mode', 'model', 'temperature', 'max_steps', 'permission', 'color']:
                if key in agent.metadata:
                    val = agent.metadata[key]
                    # Opencode doesn't support mode: skill
                    if key == 'mode' and val == 'skill':
                        val = 'subagent'
                    frontmatter[key] = val

            fm_yaml = yaml.dump(frontmatter, sort_keys=False, allow_unicode=True)
            content = f"---\n{fm_yaml}---\n\n{agent.content}"
            
            if dry_run:
                console.print(f"[blue]Would write {agent_file}[/blue]")
            else:
                agent_file.parent.mkdir(parents=True, exist_ok=True)
                with open(agent_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                saved_count += 1
                
        return saved_count

    def save_skills(self, skills: List[Skill], dry_run: bool = False, force: bool = False) -> int:
        agents = []
        for s in skills:
            # Opencode doesn't support mode: skill, so we use subagent 
            # and put it in a skills/ subdirectory
            metadata = s.metadata.copy()
            metadata['mode'] = 'subagent'
            name = s.name if s.name.startswith('skills/') else f"skills/{s.name}"
            agents.append(Agent(
                name=name, 
                description=s.description, 
                content=s.content, 
                tools=s.tools, 
                metadata=metadata
            ))
        return self.save_agents(agents, dry_run=dry_run, force=force)

    def save_commands(self, commands: List[Command], dry_run: bool = False, force: bool = False) -> int:
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0
        
        for cmd in commands:
            cmd_path = self.commands_dir / f"{cmd.name}.md"
            
            if cmd_path.exists() and not force:
                continue
            
            content = cmd.content.replace("{{args}}", "$ARGUMENTS")
            
            frontmatter = {
                'description': cmd.description
            }
            
            fm_yaml = yaml.dump(frontmatter, sort_keys=False, allow_unicode=True)
            full_content = f"---\n{fm_yaml}---\n\n{content}"
            
            if dry_run:
                console.print(f"[blue]Would write {cmd_path}[/blue]")
            else:
                cmd_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cmd_path, 'w', encoding='utf-8') as f:
                    f.write(full_content)
                saved_count += 1
                
        return saved_count
