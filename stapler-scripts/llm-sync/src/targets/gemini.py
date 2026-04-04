import yaml
import tomllib
from pathlib import Path
from typing import List, Optional, Dict, Any
from core import Agent, Skill, Command, SyncTarget, SyncSource, IGNORED_NAMES
from mappings import GEMINI_TOOLS
from rich.console import Console

console = Console()

# Gemini CLI Configuration Reference:
# https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md
# Gemini uses .gemini/agents/*.md, .gemini/skills/*/SKILL.md, .gemini/commands/*.toml


class GeminiTarget(SyncTarget, SyncSource):
    def __init__(
        self,
        agents_dir: Optional[Path] = None,
        skills_dir: Optional[Path] = None,
        commands_dir: Optional[Path] = None,
    ):
        self.agents_dir = agents_dir or Path.home() / ".gemini" / "agents"
        self.skills_dir = skills_dir or Path.home() / ".gemini" / "skills"
        self.commands_dir = commands_dir or Path.home() / ".gemini" / "commands"

    def load_agents(self) -> List[Agent]:
        agents = []
        if self.agents_dir.exists():
            for agent_file in self.agents_dir.glob("**/*.md"):
                if agent_file.stem in IGNORED_NAMES:
                    continue
                agent = self._load_md_item(agent_file, self.agents_dir, Agent)
                if agent:
                    agents.append(agent)
        return agents

    def load_skills(self) -> List[Skill]:
        skills = []
        if self.skills_dir.exists():
            for skill_file in self.skills_dir.glob("**/SKILL.md"):
                if skill_file.parent.name in IGNORED_NAMES:
                    continue
                skill = self._load_md_item(skill_file, self.skills_dir, Skill)
                if skill:
                    # Skill name is directory name
                    skill.name = str(
                        skill_file.parent.relative_to(self.skills_dir)
                    ).replace("\\", "/")
                    skills.append(skill)
        return skills

    def load_commands(self) -> List[Command]:
        commands = []
        if self.commands_dir.exists():
            for cmd_file in self.commands_dir.glob("**/*.toml"):
                if cmd_file.stem in IGNORED_NAMES:
                    continue
                try:
                    with open(cmd_file, "rb") as f:
                        data = tomllib.load(f)

                    rel_path = cmd_file.relative_to(self.commands_dir)
                    name = str(rel_path.with_suffix("")).replace("\\", "/")

                    commands.append(
                        Command(
                            name=name,
                            description=data.get("description", ""),
                            content=data.get("prompt", ""),
                            metadata=data,
                            source_file=str(cmd_file),
                        )
                    )
                except Exception as e:
                    console.print(
                        f"[red]Error reading Gemini command {cmd_file}: {e}[/red]"
                    )
        return commands

    def _load_md_item(self, item_file: Path, base_dir: Path, cls):
        try:
            with open(item_file, "r", encoding="utf-8") as f:
                content = f.read()

            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = parts[1].strip()
                    item_content = parts[2].strip()
                    metadata = yaml.safe_load(frontmatter) or {}

                    rel_path = item_file.relative_to(base_dir)
                    default_name = str(rel_path.with_suffix("")).replace("\\", "/")

                    name = metadata.get("name") or default_name
                    description = metadata.get("description", "")

                    # Convert tools list to dict
                    tools_list = metadata.get("tools", [])
                    tools = {t: True for t in tools_list}

                    params = {
                        "name": name,
                        "description": description,
                        "content": item_content,
                        "metadata": metadata,
                        "source_file": str(item_file),
                    }
                    if hasattr(cls, "tools"):
                        params["tools"] = tools

                    return cls(**params)
        except Exception as e:
            console.print(f"[red]Error reading Gemini item {item_file}: {e}[/red]")
        return None

    def save_agents(
        self, agents: List[Agent], dry_run: bool = False, force: bool = False
    ) -> int:
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0

        for agent in agents:
            agent_file = self.agents_dir / f"{agent.name}.md"

            if agent_file.exists() and not force:
                continue

            frontmatter = {
                "name": agent.name,
                "description": agent.description,
            }

            # If tools are restricted (not all tools), we could specify them.
            # But the user suggested not specifying them at all to rely on inheritance.
            # We'll skip tools for now.
            # enabled_tools = [
            #     t for t, enabled in agent.tools.items() if enabled and t in GEMINI_TOOLS
            # ]
            # if enabled_tools:
            #     frontmatter["tools"] = enabled_tools

            for key in ["temperature", "max_turns", "timeout_mins"]:
                if key in agent.metadata:
                    frontmatter[key] = agent.metadata[key]

            # Filter model names - only allow known Gemini models
            model = agent.metadata.get("model")
            if model and isinstance(model, str):
                model_lower = model.lower()
                if "gemini" in model_lower:
                    frontmatter["model"] = model
                # If it's a Claude model name, we omit it so it defaults to the session model
            
            fm_yaml = yaml.dump(frontmatter, sort_keys=False)
            full_content = f"---\n{fm_yaml}---\n\n{agent.content}"

            if dry_run:
                console.print(f"[blue]Would write {agent_file}[/blue]")
            else:
                agent_file.parent.mkdir(parents=True, exist_ok=True)
                with open(agent_file, "w", encoding="utf-8") as f:
                    f.write(full_content)
                saved_count += 1

        return saved_count

    def save_skills(
        self, skills: List[Skill], dry_run: bool = False, force: bool = False
    ) -> int:
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0

        for skill in skills:
            skill_dir = self.skills_dir / skill.name
            skill_file = skill_dir / "SKILL.md"

            if skill_file.exists() and not force:
                continue

            frontmatter = {
                "name": skill.name,
                "description": skill.description,
            }

            fm_yaml = yaml.dump(frontmatter, sort_keys=False)
            full_content = f"---\n{fm_yaml}---\n\n{skill.content}"

            if dry_run:
                console.print(f"[blue]Would write {skill_file}[/blue]")
            else:
                skill_dir.mkdir(parents=True, exist_ok=True)
                with open(skill_file, "w", encoding="utf-8") as f:
                    f.write(full_content)
                saved_count += 1

        return saved_count

    def save_commands(
        self, commands: List[Command], dry_run: bool = False, force: bool = False
    ) -> int:
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0

        for cmd in commands:
            cmd_path = self.commands_dir / f"{cmd.name}.toml"

            if cmd_path.exists() and not force:
                continue

            content = cmd.content.replace("$ARGUMENTS", "{{args}}")
            desc_safe = (
                cmd.description.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", " ")
            )

            if "'''" not in content:
                toml_content = (
                    f"description = \"{desc_safe}\"\n\nprompt = '''\n{content}\n'''\n"
                )
            else:
                content_safe = content.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
                toml_content = f'description = "{desc_safe}"\n\nprompt = """\n{content_safe}\n"""\n'

            if dry_run:
                console.print(f"[blue]Would write {cmd_path}[/blue]")
            else:
                cmd_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cmd_path, "w", encoding="utf-8") as f:
                    f.write(toml_content)
                saved_count += 1

        return saved_count
