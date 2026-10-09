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


def _canonical_skill_name(name: str) -> str:
    """Remove nested plugin layout directories from a Claude skill identity.

    Claude plugins conventionally store a skill at
    ``<plugin>/skills/<skill>/SKILL.md``.  ``ClaudeSource`` preserves that
    on-disk path as (for example) ``sdd/skills/full``.  The intermediate
    ``skills`` segment is packaging structure, not part of the invocation
    name; retaining it makes Pi advertise the less discoverable
    ``sdd-skills-full`` instead of ``sdd-full``.
    """
    parts = str(name).replace("\\", "/").split("/")
    return "/".join(
        part for index, part in enumerate(parts) if part != "skills" or index == 0
    )


def _normalize_name(name: str) -> str:
    """Convert a name to a valid, stable Agent Skills identifier."""
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


def _normalize_skill_name(name: str) -> str:
    """Convert a source skill name to its Pi-facing identifier."""
    return _normalize_name(_canonical_skill_name(name))


def _legacy_normalize_skill_name(name: str) -> str:
    """Return the Pi identifier emitted before plugin-layout normalization."""
    return _normalize_name(name)


def _flatten(name: str) -> str:
    """Flatten a namespaced command name for Pi's non-recursive prompts dir."""
    return name.replace("/", "-")


def _description_for_pi(description: str) -> str:
    return str(description or "").strip()[:_MAX_SKILL_DESCRIPTION]


class PiTarget(SyncTarget, SyncSource):
    # Changing this invalidates only Pi skill state, forcing a safe one-time
    # rewrite when the target's naming rules change.
    _SKILL_NAMING_VERSION = "2"

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

    def get_sync_hash(self, item, item_type: str) -> str:
        """Version Pi skill state when its output layout changes."""
        item_hash = item.get_hash()
        if item_type == "skills":
            return f"pi-skill-name-v{self._SKILL_NAMING_VERSION}:{item_hash}"
        return item_hash

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

    def cleanup_legacy_skill_layout(
        self, skills: List[Skill], dry_run: bool = False
    ) -> int:
        """Remove prior generated names after a naming-format migration.

        Only remove a directory when its frontmatter proves it was generated
        using the old name, and never when that name remains a current output.
        """
        valid_skills = [
            skill for skill in skills if _description_for_pi(skill.description)
        ]
        pi_names = self._pi_names(valid_skills)
        current_names = set(pi_names.values())
        removed = 0

        for skill in valid_skills:
            old_name = _legacy_normalize_skill_name(skill.name)
            new_name = pi_names[id(skill)]
            if old_name == new_name or old_name in current_names:
                continue

            old_dir = self.skills_dir / old_name
            old_file = old_dir / "SKILL.md"
            new_file = self.skills_dir / new_name / "SKILL.md"
            # State may have been updated by a separate --pi-dir run. Never
            # delete a legacy output until the canonical replacement exists
            # at this target location.
            if not old_file.is_file() or not new_file.is_file():
                continue
            try:
                metadata = yaml.safe_load(
                    old_file.read_text(encoding="utf-8").split("---", 2)[1]
                ) or {}
            except (IndexError, OSError, yaml.YAMLError):
                continue
            if metadata.get("name") != old_name:
                continue

            if dry_run:
                console.print(f"[blue]Would remove legacy Pi skill {old_dir}[/blue]")
            else:
                shutil.rmtree(old_dir)
            removed += 1

        return removed

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
