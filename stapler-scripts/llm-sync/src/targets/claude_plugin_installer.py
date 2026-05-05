import json
from pathlib import Path
from typing import List, Optional

try:
    from core import Plugin
except ImportError:
    from ..core import Plugin

from rich.console import Console

console = Console()


class ClaudePluginInstaller:
    """Installs Claude plugins into a .claude/ directory (global or local)."""

    def __init__(self, target_dir: Optional[Path] = None):
        # Default to global ~/.claude/; pass a project's .claude/ for local installs
        self.target_dir = target_dir or Path.home() / ".claude"
        self.settings_file = self.target_dir / "settings.json"

    def install_plugins(self, plugins: List[Plugin], dry_run: bool = False) -> int:
        installed = 0
        for plugin in plugins:
            count = self._install_plugin(plugin, dry_run)
            installed += count
            if not dry_run:
                console.print(
                    f"[green]Installed plugin '{plugin.name}' "
                    f"({count} items) -> {self.target_dir}[/green]"
                )
        return installed

    def _install_plugin(self, plugin: Plugin, dry_run: bool) -> int:
        count = 0
        count += self._install_commands(plugin, dry_run)
        count += self._install_skills(plugin, dry_run)
        count += self._install_hooks(plugin, dry_run)
        return count

    def _install_commands(self, plugin: Plugin, dry_run: bool) -> int:
        commands_base = self.target_dir / "commands"
        count = 0
        for cmd in plugin.commands:
            dest = commands_base / f"{cmd.name}.md"
            if dry_run:
                console.print(f"[blue]Would write command {dest}[/blue]")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(cmd.content, encoding="utf-8")
            count += 1
        return count

    def _install_skills(self, plugin: Plugin, dry_run: bool) -> int:
        skills_base = self.target_dir / "skills"
        count = 0
        for skill in plugin.skills:
            dest = skills_base / skill.name / "SKILL.md"
            if dry_run:
                console.print(f"[blue]Would write skill {dest}[/blue]")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(skill.content, encoding="utf-8")
            count += 1
        return count

    def _install_hooks(self, plugin: Plugin, dry_run: bool) -> int:
        if not plugin.hooks:
            return 0

        settings = {}
        if self.settings_file.exists():
            try:
                settings = json.loads(self.settings_file.read_text(encoding="utf-8"))
            except Exception as e:
                console.print(f"[red]Error reading {self.settings_file}: {e}[/red]")
                return 0

        existing_hooks: dict = settings.get("hooks", {})
        new_count = self._merge_hooks(existing_hooks, plugin.hooks, plugin.name)

        if dry_run:
            console.print(
                f"[blue]Would merge {sum(len(v) for v in plugin.hooks.values())} "
                f"hook entries for plugin '{plugin.name}' into {self.settings_file}[/blue]"
            )
            return new_count

        settings["hooks"] = existing_hooks
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings_file.write_text(
            json.dumps(settings, indent=2) + "\n", encoding="utf-8"
        )
        return new_count

    def _merge_hooks(
        self,
        existing: dict,
        plugin_hooks: dict,
        plugin_name: str,
    ) -> int:
        """Merge plugin hooks into existing, deduplicating by command string."""
        added = 0
        for event_type, entries in plugin_hooks.items():
            existing_entries: list = existing.setdefault(event_type, [])
            existing_commands = self._collect_commands(existing_entries)

            for entry in entries:
                new_hooks = []
                for hook in entry.get("hooks", []):
                    cmd = hook.get("command", "")
                    if cmd and cmd not in existing_commands:
                        new_hooks.append(hook)
                        existing_commands.add(cmd)
                        added += 1

                if new_hooks:
                    new_entry = {"hooks": new_hooks}
                    if entry.get("matcher"):
                        new_entry["matcher"] = entry["matcher"]
                    existing_entries.append(new_entry)

        return added

    def _collect_commands(self, entries: list) -> set:
        cmds = set()
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                if cmd:
                    cmds.add(cmd)
        return cmds
