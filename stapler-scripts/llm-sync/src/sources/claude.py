import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from core import Agent, Skill, Command, SyncSource
from mappings import map_tool, GEMINI_TOOLS
from rich.console import Console

console = Console()

class ClaudeSource(SyncSource):
    def __init__(self, agents_dir: Optional[Path] = None, skills_dir: Optional[Path] = None, commands_dir: Optional[Path] = None):
        self.agents_dir = agents_dir or Path.home() / ".claude" / "agents"
        self.skills_dir = skills_dir or Path.home() / ".claude" / "skills"
        self.commands_dir = commands_dir or Path.home() / ".claude" / "commands"

    def load_agents(self) -> List[Agent]:
        agents = []
        if self.agents_dir.exists():
            for agent_file in self.agents_dir.glob("**/*.md"):
                agent = self._load_agent(agent_file)
                if agent:
                    agents.append(agent)
        return agents

    def load_skills(self) -> List[Skill]:
        skills = []
        if self.skills_dir.exists():
            # Claude "skills" (legacy/plugin based) are often just md files too
            for skill_file in self.skills_dir.glob("**/*.md"):
                # We reuse _load_agent logic but wrap as Skill
                # Or parsing might be simpler if they don't have frontmatter
                # Let's assume similar format for now
                agent = self._load_agent(skill_file)
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
                try:
                    with open(cmd_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Assume commands are simple markdown or frontmatter+markdown
                    # If they have frontmatter, we parse it.
                    name = cmd_file.stem
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
                                    # Name in frontmatter overrides filename
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

    def _load_agent(self, agent_file: Path) -> Optional[Agent]:
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
                        
                    name = metadata.get('name') or agent_file.stem
                    description = metadata.get('description', '')
                    
                    # Convert tools
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
        # Simple manual parser for when YAML fails (often due to unquoted strings or 'tools: *')
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
        """Convert Claude tool definitions to Gemini tool map using shared mappings."""
        result = {}
        
        # Helper to process a single tool string
        def process_tool(t_name):
            t_name = t_name.lower().strip()
            
            # Handle wildcards
            if t_name in ['*', 'all']:
                for tool in GEMINI_TOOLS:
                    result[tool] = True
                return

            # Handle specific tools
            gemini_tool = map_tool(t_name)
            if gemini_tool:
                result[gemini_tool] = True
            else:
                # Keep unknown tools but mark as False (or handle differently if needed)
                # For now, we only enable mapped tools.
                pass
        
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
