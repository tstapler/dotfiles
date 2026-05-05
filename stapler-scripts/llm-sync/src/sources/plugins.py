import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    from core import Command, Plugin, Skill
except ImportError:
    from ..core import Command, Plugin, Skill

from rich.console import Console

console = Console()

PLUGIN_MANIFEST = ".claude-plugin/plugin.json"


class PluginSource:
    def __init__(
        self,
        global_plugins_dir: Optional[Path] = None,
        local_plugins_dir: Optional[Path] = None,
    ):
        # Global: checked into dotfiles (e.g. ./plugins/ relative to dotfiles root)
        self.global_plugins_dir = global_plugins_dir or self._find_global()
        # Local: project-specific plugins, lower priority (overrides global by name)
        self.local_plugins_dir = local_plugins_dir or self._find_local()

    def _find_global(self) -> Optional[Path]:
        candidates = [
            Path.cwd() / "plugins",
            Path.home() / ".config" / "llm-sync" / "plugins",
        ]
        for p in candidates:
            if p.exists() and any(p.iterdir()):
                return p
        return None

    def _find_local(self) -> Optional[Path]:
        local = Path.cwd() / ".claude-plugins"
        return local if local.exists() else None

    def load_plugins(self) -> List[Plugin]:
        plugins: Dict[str, Plugin] = {}

        for plugins_dir in [self.global_plugins_dir, self.local_plugins_dir]:
            if plugins_dir and plugins_dir.exists():
                loaded = self._load_from_dir(plugins_dir)
                plugins.update({p.name: p for p in loaded})
                console.print(
                    f"[dim]Loaded {len(loaded)} plugins from {plugins_dir}[/dim]"
                )

        return list(plugins.values())

    def _load_from_dir(self, plugins_dir: Path) -> List[Plugin]:
        plugins = []
        for entry in sorted(plugins_dir.iterdir()):
            if not entry.is_dir():
                continue
            manifest_path = entry / PLUGIN_MANIFEST
            if not manifest_path.exists():
                continue
            plugin = self._load_plugin(entry, manifest_path)
            if plugin:
                plugins.append(plugin)
        return plugins

    def _load_plugin(self, plugin_dir: Path, manifest_path: Path) -> Optional[Plugin]:
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            name = manifest.get("name", plugin_dir.name)
            description = manifest.get("description", "")
            version = manifest.get("version", "0.0.0")

            commands = self._load_commands(plugin_dir, name)
            skills = self._load_skills(plugin_dir)
            hooks = self._load_hooks(plugin_dir)

            return Plugin(
                name=name,
                description=description,
                version=version,
                commands=commands,
                skills=skills,
                hooks=hooks,
                source_dir=str(plugin_dir),
            )
        except Exception as e:
            console.print(f"[red]Error loading plugin from {plugin_dir}: {e}[/red]")
            return None

    def _load_commands(self, plugin_dir: Path, plugin_name: str) -> List[Command]:
        commands = []
        commands_dir = plugin_dir / "commands"
        if not commands_dir.exists():
            return commands

        for cmd_file in sorted(commands_dir.glob("**/*.md")):
            try:
                content = cmd_file.read_text(encoding="utf-8")
                rel = cmd_file.relative_to(commands_dir)
                # Namespace under plugin name: sdd/1-ideate
                name = f"{plugin_name}/{str(rel.with_suffix('')).replace(chr(92), '/')}"
                commands.append(
                    Command(name=name, description="", content=content)
                )
            except Exception as e:
                console.print(f"[red]Error reading command {cmd_file}: {e}[/red]")
        return commands

    def _load_skills(self, plugin_dir: Path) -> List[Skill]:
        skills = []
        skills_dir = plugin_dir / "skills"
        if not skills_dir.exists():
            return skills

        for skill_file in sorted(skills_dir.glob("**/SKILL.md")):
            try:
                content = skill_file.read_text(encoding="utf-8")
                # Use the parent directory name as the skill name
                skill_name = skill_file.parent.name
                skills.append(
                    Skill(name=skill_name, description="", content=content)
                )
            except Exception as e:
                console.print(f"[red]Error reading skill {skill_file}: {e}[/red]")
        return skills

    def _load_hooks(self, plugin_dir: Path) -> Dict[str, List[dict]]:
        hooks_file = plugin_dir / "hooks" / "hooks.json"
        if not hooks_file.exists():
            return {}
        try:
            with open(hooks_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[red]Error reading hooks {hooks_file}: {e}[/red]")
            return {}
