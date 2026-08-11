import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml

try:
    from core import Command, Plugin, Skill
except ImportError:
    from ..core import Command, Plugin, Skill

from rich.console import Console

console = Console()

PLUGIN_MANIFEST = ".claude-plugin/plugin.json"

DEFAULT_INSTALLED_PLUGINS_FILE = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
DEFAULT_CLAUDE_SETTINGS_FILE = Path.home() / ".claude" / "settings.json"
DEFAULT_CLAUDE_SETTINGS_LOCAL_FILE = Path.home() / ".claude" / "settings.local.json"


class PluginSource:
    def __init__(
        self,
        global_plugins_dir: Optional[Path] = None,
        local_plugins_dir: Optional[Path] = None,
        installed_plugins_file: Optional[Path] = None,
        claude_settings_file: Optional[Path] = None,
        claude_settings_local_file: Optional[Path] = None,
    ):
        # Global: checked into dotfiles (e.g. ./plugins/ relative to dotfiles root)
        self.global_plugins_dir = global_plugins_dir or self._find_global()
        # Local: project-specific plugins, lower priority (overrides global by name)
        self.local_plugins_dir = local_plugins_dir or self._find_local()

        # Marketplace-installed plugins (via `/plugin install`), lowest priority of the
        # three sources (dotfiles-committed plugins always win on a name collision).
        self.installed_plugins_file = installed_plugins_file or DEFAULT_INSTALLED_PLUGINS_FILE
        self.claude_settings_file = claude_settings_file or DEFAULT_CLAUDE_SETTINGS_FILE
        self.claude_settings_local_file = claude_settings_local_file or DEFAULT_CLAUDE_SETTINGS_LOCAL_FILE
        self.marketplace_plugin_dirs = self._find_marketplace_plugins()

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

    def _load_json(self, path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            console.print(f"[yellow]Warning: couldn't read {path}: {e}[/yellow]")
            return None

    def _disabled_plugin_keys(self) -> set:
        """Plugin keys ('<name>@<marketplace>') disabled via enabledPlugins.

        Checked in both settings.json and settings.local.json since precedence
        between the two isn't documented; a plugin disabled in either wins.
        """
        disabled = set()
        for settings_file in (self.claude_settings_file, self.claude_settings_local_file):
            data = self._load_json(settings_file)
            if not isinstance(data, dict):
                continue
            enabled_map = data.get("enabledPlugins")
            if not isinstance(enabled_map, dict):
                continue
            for key, enabled in enabled_map.items():
                if enabled is False:
                    disabled.add(key)
        return disabled

    def _find_marketplace_plugins(self) -> List[Path]:
        data = self._load_json(self.installed_plugins_file)
        if not isinstance(data, dict):
            return []
        plugins_map = data.get("plugins")
        if not isinstance(plugins_map, dict):
            return []

        disabled_keys = self._disabled_plugin_keys()
        dirs = []
        for key, records in plugins_map.items():
            if key in disabled_keys:
                continue
            if isinstance(records, dict):
                records = [records]
            elif not isinstance(records, list):
                continue

            # A key can carry multiple scope records (e.g. user + project); resolve
            # to a single dir, preferring the "user" scope, falling back to the
            # first record whose installPath still exists on disk.
            chosen = None
            for rec in sorted(
                (r for r in records if isinstance(r, dict)),
                key=lambda r: 0 if r.get("scope") == "user" else 1,
            ):
                install_path = rec.get("installPath")
                if not install_path:
                    continue
                path = Path(install_path)
                if path.exists():
                    chosen = path
                    break

            if chosen is not None:
                dirs.append(chosen)
            else:
                console.print(
                    f"[yellow]Warning: no valid installPath found for marketplace plugin {key}[/yellow]"
                )
        return dirs

    def load_plugins(self) -> List[Plugin]:
        plugins: Dict[str, Plugin] = {}

        # Marketplace plugins load first so dotfiles-committed global/local plugins
        # keep winning on a name collision (see the comment in __init__ above).
        marketplace_loaded = self._load_entries(self.marketplace_plugin_dirs)
        plugins.update({p.name: p for p in marketplace_loaded})
        if marketplace_loaded:
            console.print(
                f"[dim]Loaded {len(marketplace_loaded)} plugins from marketplace installs[/dim]"
            )

        for plugins_dir in [self.global_plugins_dir, self.local_plugins_dir]:
            if plugins_dir and plugins_dir.exists():
                loaded = self._load_from_dir(plugins_dir)
                plugins.update({p.name: p for p in loaded})
                console.print(
                    f"[dim]Loaded {len(loaded)} plugins from {plugins_dir}[/dim]"
                )

        return list(plugins.values())

    def _load_from_dir(self, plugins_dir: Path) -> List[Plugin]:
        return self._load_entries(sorted(plugins_dir.iterdir()))

    def _load_entries(self, entries: List[Path]) -> List[Plugin]:
        plugins = []
        for entry in entries:
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
                description = self._extract_frontmatter_description(content)
                rel = cmd_file.relative_to(commands_dir)
                # Namespace under plugin name: sdd/1-ideate
                name = f"{plugin_name}/{str(rel.with_suffix('')).replace(chr(92), '/')}"
                commands.append(
                    Command(name=name, description=description, content=content)
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
                description = self._extract_frontmatter_description(content)
                # Use the parent directory name as the skill name
                skill_name = skill_file.parent.name
                skills.append(
                    Skill(name=skill_name, description=description, content=content)
                )
            except Exception as e:
                console.print(f"[red]Error reading skill {skill_file}: {e}[/red]")
        return skills

    def _extract_frontmatter_description(self, content: str) -> str:
        """Extract the 'description' field from YAML frontmatter (first --- block)."""
        m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if m:
            try:
                fm = yaml.safe_load(m.group(1))
                if isinstance(fm, dict):
                    return fm.get("description") or ""
            except yaml.YAMLError:
                pass
        return ""

    def _load_hooks(self, plugin_dir: Path) -> Dict[str, List[dict]]:
        hooks_file = plugin_dir / "hooks" / "hooks.json"
        if not hooks_file.exists():
            return {}
        try:
            with open(hooks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "hooks" in data and len(data) == 1:
                    return data["hooks"]
                return data
        except Exception as e:
            console.print(f"[red]Error reading hooks {hooks_file}: {e}[/red]")
            return {}
