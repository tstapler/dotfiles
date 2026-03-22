import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from core import Agent, Skill, Command, SyncSource, SyncTarget, IGNORED_NAMES
from mappings import map_tool, GEMINI_TOOLS
from rich.console import Console

console = Console()

class ClaudeSource(SyncSource, SyncTarget):
    def __init__(self, agents_dir: Optional[Path] = None, skills_dir: Optional[Path] = None, commands_dir: Optional[Path] = None):
        local_claude = Path.cwd() / ".claude"
        self.agents_dir = agents_dir or (local_claude / "agents" if (local_claude / "agents").exists() else Path.home() / ".claude" / "agents")
        self.skills_dir = skills_dir or (local_claude / "skills" if (local_claude / "skills").exists() else Path.home() / ".claude" / "skills")
        self.commands_dir = commands_dir or (local_claude / "commands" if (local_claude / "commands").exists() else Path.home() / ".claude" / "commands")
        if local_claude.exists():
            console.print(f"[dim]Using local project-specific .claude directory: {local_claude}[/dim]")

    def load_agents(self) -> List[Agent]:
        agents = []
        if self.agents_dir.exists():
            for agent_file in self.agents_dir.glob("**/*.md"):
                if agent_file.stem in IGNORED_NAMES:
                    continue
                agent = self._load_agent(agent_file, self.agents_dir)
                if agent:
                    agents.append(agent)
        return agents

    def load_skills(self) -> List[Skill]:
        skills = []
        if self.skills_dir.exists():
            for skill_file in self.skills_dir.glob("**/*.md"):
                if skill_file.stem in IGNORED_NAMES:
                    continue
                agent = self._load_agent(skill_file, self.skills_dir)
                if agent:
                    skills.append(Skill(
                        name=agent.name,
                        description=agent.description,
                        content=agent.content,
                        tools=agent.tools,
                        metadata=agent.metadata,
                        source_file=agent.source_file
                    ))
        return skills

    def load_commands(self) -> List[Command]:
        commands = []
        if self.commands_dir.exists():
            for cmd_file in self.commands_dir.glob("**/*.md"):
                if cmd_file.stem in IGNORED_NAMES:
                    continue
                try:
                    with open(cmd_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    rel_path = cmd_file.relative_to(self.commands_dir)
                    name = str(rel_path.with_suffix('')).replace('\\', '/')

                    description = ""
                    cmd_content = content
                    metadata = {}

                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            frontmatter = parts[1].strip()
                            cmd_content = parts[2].strip()
                            try:
                                metadata = yaml.safe_load(frontmatter)
                                if metadata:
                                    description = metadata.get('description', '')
                                    if 'name' in metadata:
                                        name = metadata['name']
                            except yaml.YAMLError:
                                pass

                    commands.append(Command(
                        name=name,
                        description=description,
                        content=cmd_content,
                        metadata=metadata,
                        source_file=str(cmd_file)
                    ))
                except Exception as e:
                    console.print(f"[red]Error reading command {cmd_file}: {e}[/red]")
        return commands

    def _load_agent(self, agent_file: Path, base_dir: Path) -> Optional[Agent]:
        try:
            with open(agent_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = parts[1].strip()
                    agent_content = parts[2].strip()

                    try:
                        metadata = yaml.safe_load(frontmatter)
                    except yaml.YAMLError:
                        metadata = self._parse_frontmatter_manually(frontmatter)

                    if not metadata:
                        return None

                    rel_path = agent_file.relative_to(base_dir)
                    default_name = str(rel_path.with_suffix('')).replace('\\', '/')

                    name = metadata.get('name') or default_name
                    description = metadata.get('description', '')

                    claude_tools = metadata.get('tools', [])
                    tools = self._convert_tools(claude_tools)

                    return Agent(
                        name=name,
                        description=description,
                        content=agent_content,
                        tools=tools,
                        metadata=metadata,
                        source_file=str(agent_file)
                    )
        except Exception as e:
            console.print(f"[red]Error reading {agent_file}: {e}[/red]")
        return None

    def _parse_frontmatter_manually(self, frontmatter: str) -> Optional[Dict[str, Any]]:
        metadata = {}
        for line in frontmatter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if value:
                    metadata[key] = value
        return metadata

    def _convert_tools(self, claude_tools: Any) -> Dict[str, bool]:
        result = {}
        def process_tool(t_name):
            t_name = t_name.lower().strip()
            if t_name in ['*', 'all']:
                for tool in GEMINI_TOOLS:
                    result[tool] = True
                return

            gemini_tool = map_tool(t_name)
            if gemini_tool:
                result[gemini_tool] = True
            else:
                result[t_name] = True

        if isinstance(claude_tools, str):
            if ',' in claude_tools:
                for t in claude_tools.split(','):
                    process_tool(t)
            else:
                process_tool(claude_tools)
        elif isinstance(claude_tools, list):
            for t in claude_tools:
                process_tool(str(t))
        return result

    def save_agents(self, agents: List[Agent], dry_run: bool = False, force: bool = False) -> int:
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0
        for agent in agents:
            agent_file = self.agents_dir / f"{agent.name}.md"
            if agent_file.exists() and not force:
                continue

            metadata = agent.metadata.copy()
            metadata['name'] = agent.name
            metadata['description'] = agent.description
            metadata['tools'] = [t for t, enabled in agent.tools.items() if enabled]

            fm_yaml = yaml.dump(metadata, sort_keys=False, allow_unicode=True)
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
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0
        for skill in skills:
            skill_file = self.skills_dir / f"{skill.name}.md"
            if skill_file.exists() and not force:
                continue

            metadata = skill.metadata.copy()
            metadata['name'] = skill.name
            metadata['description'] = skill.description

            fm_yaml = yaml.dump(metadata, sort_keys=False, allow_unicode=True)
            content = f"---\n{fm_yaml}---\n\n{skill.content}"

            if dry_run:
                console.print(f"[blue]Would write {skill_file}[/blue]")
            else:
                skill_file.parent.mkdir(parents=True, exist_ok=True)
                with open(skill_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                saved_count += 1
        return saved_count

    def save_commands(self, commands: List[Command], dry_run: bool = False, force: bool = False) -> int:
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0
        for cmd in commands:
            cmd_file = self.commands_dir / f"{cmd.name}.md"
            if cmd_file.exists() and not force:
                continue

            content = cmd.content.replace("{{args}}", "$ARGUMENTS")

            metadata = cmd.metadata.copy()
            metadata['description'] = cmd.description

            fm_yaml = yaml.dump(metadata, sort_keys=False, allow_unicode=True)
            full_content = f"---\n{fm_yaml}---\n\n{content}"

            if dry_run:
                console.print(f"[blue]Would write {cmd_file}[/blue]")
            else:
                cmd_file.parent.mkdir(parents=True, exist_ok=True)
                with open(cmd_file, 'w', encoding='utf-8') as f:
                    f.write(full_content)
                saved_count += 1
        return saved_count
