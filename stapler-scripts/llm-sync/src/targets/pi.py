import hashlib
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import List, Optional

import yaml
from rich.console import Console

from core import Agent, Skill, Command, SyncTarget, SyncSource, IGNORED_NAMES

console = Console()

# Pi coding agent config references:
# https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md
# https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/prompt-templates.md
#
# Pi has no sub-agent concept by design, so only skills and commands sync here.
# Skill output must conform to the Agent Skills frontmatter limits even when a
# Claude source uses legacy display names or permits longer descriptions.

_MAX_SKILL_NAME = 64
_MAX_SKILL_DESCRIPTION = 1024
_PI_SKILL_METADATA_FIELDS = {
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
    "disable-model-invocation",
}


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def _normalize_skill_name(name: str) -> str:
    """Convert a source name to a valid, stable Agent Skills identifier."""
    ascii_name = unicodedata.normalize("NFKD", str(name)).encode(
        "ascii", "ignore"
    ).decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    normalized = re.sub(r"-{2,}", "-", normalized)

    if not normalized:
        normalized = f"skill-{_short_hash(str(name))}"

    if len(normalized) > _MAX_SKILL_NAME:
        suffix = _short_hash(normalized)
        normalized = f"{normalized[: _MAX_SKILL_NAME - len(suffix) - 1].rstrip('-')}-{suffix}"

    return normalized


def _flatten(name: str) -> str:
    """Flatten a namespaced command name for Pi's non-recursive prompts dir."""
    return name.replace("/", "-")


def _description_for_pi(description: str) -> str:
    return str(description or "").strip()[:_MAX_SKILL_DESCRIPTION]


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
                    skill.name = str(
                        skill_file.parent.relative_to(self.skills_dir)
                    ).replace("\\", "/")
                    skills.append(skill)
        return skills

    def load_commands(self) -> List[Command]:
        commands = []
        if self.prompts_dir.exists():
            for cmd_file in self.prompts_dir.glob("*.md"):
                if cmd_file.stem in IGNORED_NAMES:
                    continue
                cmd = self._load_md_item(cmd_file, self.prompts_dir, Command)
                if cmd:
                    commands.append(cmd)
        return commands

    def _load_md_item(self, item_file: Path, base_dir: Path, cls):
        try:
            content = item_file.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    metadata = yaml.safe_load(parts[1].strip()) or {}
                    rel_path = item_file.relative_to(base_dir)
                    default_name = str(rel_path.with_suffix("")).replace("\\", "/")
                    return cls(
                        name=metadata.get("name") or default_name,
                        description=metadata.get("description") or "",
                        content=parts[2].strip(),
                        metadata=metadata,
                        source_file=str(item_file),
                    )
        except Exception as e:
            console.print(f"[red]Error reading Pi item {item_file}: {e}[/red]")
        return None

    def _pi_names(self, skills: List[Skill]) -> dict[int, str]:
        """Resolve normalized names and deterministically disambiguate collisions."""
        grouped = defaultdict(list)
        for skill in skills:
            grouped[_normalize_skill_name(skill.name)].append(skill)

        result = {}
        for base_name, group in grouped.items():
            if len(group) == 1:
                result[id(group[0])] = base_name
                continue

            for skill in group:
                identity = f"{skill.name}\0{skill.source_file or skill.content}"
                suffix = _short_hash(identity)
                prefix = base_name[: _MAX_SKILL_NAME - len(suffix) - 1].rstrip("-")
                result[id(skill)] = f"{prefix}-{suffix}"
        return result

    @staticmethod
    def _copy_bundled_resources(skill: Skill, skill_dir: Path) -> None:
        if not skill.source_file:
            return
        source_file = Path(skill.source_file)
        if source_file.name != "SKILL.md" or not source_file.parent.is_dir():
            return

        shutil.copytree(
            source_file.parent,
            skill_dir,
            dirs_exist_ok=True,
            symlinks=True,
            ignore=shutil.ignore_patterns("SKILL.md", "node_modules"),
        )

    def save_skills(
        self, skills: List[Skill], dry_run: bool = False, force: bool = False
    ) -> int:
        saved_count = 0
        valid_skills = []
        descriptions = {}

        for skill in skills:
            description = _description_for_pi(skill.description)
            if not description:
                console.print(
                    f"[yellow]Skipping Pi skill '{skill.name}': description is required[/yellow]"
                )
                continue
            valid_skills.append(skill)
            descriptions[id(skill)] = description

        pi_names = self._pi_names(valid_skills)
        for skill in valid_skills:
            pi_name = pi_names[id(skill)]
            skill_dir = self.skills_dir / pi_name
            skill_file = skill_dir / "SKILL.md"

            if skill_file.exists() and not force:
                continue

            frontmatter = {
                key: value
                for key, value in skill.metadata.items()
                if key in _PI_SKILL_METADATA_FIELDS
            }
            frontmatter["name"] = pi_name
            frontmatter["description"] = descriptions[id(skill)]

            fm_yaml = yaml.dump(frontmatter, sort_keys=False, allow_unicode=True)
            full_content = f"---\n{fm_yaml}---\n\n{skill.content}"

            if dry_run:
                console.print(f"[blue]Would write {skill_file}[/blue]")
            else:
                skill_dir.mkdir(parents=True, exist_ok=True)
                self._copy_bundled_resources(skill, skill_dir)
                skill_file.write_text(full_content, encoding="utf-8")
                saved_count += 1

        return saved_count

    def save_commands(
        self, commands: List[Command], dry_run: bool = False, force: bool = False
    ) -> int:
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
                self.prompts_dir.mkdir(parents=True, exist_ok=True)
                cmd_path.write_text(full_content, encoding="utf-8")
                saved_count += 1

        return saved_count
