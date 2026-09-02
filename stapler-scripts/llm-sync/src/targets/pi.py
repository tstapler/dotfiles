import yaml
from pathlib import Path
from typing import List, Optional
from core import Agent, Skill, Command, SyncTarget, SyncSource, IGNORED_NAMES
from rich.console import Console

console = Console()

# Pi coding agent (https://pi.dev) config reference:
# https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md
# https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/prompt-templates.md
#
# Pi has no sub-agent or native MCP concept by design (see its README's Philosophy
# section), so agents don't sync here -- only skills and commands.
#
# Pi's skills already follow the same Agent Skills standard as Claude's SKILL.md
# (in fact Pi's own docs suggest pointing `settings.json`'s `skills` array straight
# at `~/.claude/skills`), and its prompt templates use the same $ARGUMENTS/$1/$2
# substitution Claude commands do. So neither needs format conversion here -- only
# flattening of namespaced names, since Pi's skill `name` field forbids "/" and
# prompt-template discovery in prompts/ is non-recursive.


def _flatten(name: str) -> str:
    return name.replace("/", "-")


class PiTarget(SyncTarget, SyncSource):
    def __init__(self, agent_dir: Optional[Path] = None):
        base = agent_dir or Path.home() / ".pi" / "agent"
        self.skills_dir = base / "skills"
        self.prompts_dir = base / "prompts"

    def load_skills(self) -> List[Skill]:
        skills = []
        if self.skills_dir.exists():
            for skill_file in self.skills_dir.glob("**/SKILL.md"):
                if skill_file.parent.name in IGNORED_NAMES:
                    continue
                skill = self._load_md_item(skill_file, self.skills_dir, Skill)
                if skill:
                    # Skill name is the directory path (namespacing preserved),
                    # same as the Gemini/Antigravity targets.
                    skill.name = str(
                        skill_file.parent.relative_to(self.skills_dir)
                    ).replace("\\", "/")
                    skills.append(skill)
        return skills

    def load_commands(self) -> List[Command]:
        commands = []
        if self.prompts_dir.exists():
            # Non-recursive: matches Pi's own prompt-template discovery.
            for cmd_file in self.prompts_dir.glob("*.md"):
                if cmd_file.stem in IGNORED_NAMES:
                    continue
                cmd = self._load_md_item(cmd_file, self.prompts_dir, Command)
                if cmd:
                    commands.append(cmd)
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
                    description = metadata.get("description") or ""

                    return cls(
                        name=name,
                        description=description,
                        content=item_content,
                        metadata=metadata,
                        source_file=str(item_file),
                    )
        except Exception as e:
            console.print(f"[red]Error reading Pi item {item_file}: {e}[/red]")
        return None

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
                "name": _flatten(skill.name),
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
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0

        for cmd in commands:
            cmd_path = self.prompts_dir / f"{_flatten(cmd.name)}.md"

            if cmd_path.exists() and not force:
                continue

            frontmatter = {"description": cmd.description}
            if "argument-hint" in cmd.metadata:
                frontmatter["argument-hint"] = cmd.metadata["argument-hint"]

            fm_yaml = yaml.dump(frontmatter, sort_keys=False, allow_unicode=True)
            full_content = f"---\n{fm_yaml}---\n\n{cmd.content}"

            if dry_run:
                console.print(f"[blue]Would write {cmd_path}[/blue]")
            else:
                with open(cmd_path, "w", encoding="utf-8") as f:
                    f.write(full_content)
                saved_count += 1

        return saved_count
