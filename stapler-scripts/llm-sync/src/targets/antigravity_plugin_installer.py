import json
import re
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from core import Plugin
except ImportError:
    from ..core import Plugin

from rich.console import Console

console = Console()


def _to_antigravity_hook_spec(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert Claude Code's per-event hook list into Antigravity's hooks.json shape.

    Claude's settings.json represents each lifecycle event as a *list* of
    {matcher, hooks} groups. Antigravity's plugin loader (jsonhook.JSONHookSpec,
    confirmed empirically against a live agy 1.2.14 session — it fails with
    "cannot unmarshal array into Go struct field .<Event> of type
    jsonhook.JSONHookSpec" otherwise) expects a *single* {matcher, hooks} object
    per event. Multiple Claude matcher groups collapse into one: matchers are
    unioned (broadest one wins if any group is unscoped/"*"/".*"), and hook
    commands are concatenated in order with exact duplicates removed.
    """
    matchers: List[str] = []
    hooks: List[Dict[str, Any]] = []
    seen = set()
    for entry in entries:
        matcher = entry.get("matcher") or ""
        if matcher and matcher not in matchers:
            matchers.append(matcher)
        for hook in entry.get("hooks", []):
            key = json.dumps(hook, sort_keys=True)
            if key not in seen:
                seen.add(key)
                hooks.append(hook)
    if not matchers or "*" in matchers or ".*" in matchers:
        merged_matcher = ".*"
    else:
        merged_matcher = "|".join(matchers)
    return {"matcher": merged_matcher, "hooks": hooks}


class AntigravityPluginInstaller:
    """Installs Antigravity plugins into a global or local customizations plugins directory."""

    def __init__(self, target_dir: Optional[Path] = None):
        # Default to global ~/.gemini/config/plugins/
        self.target_dir = target_dir or Path.home() / ".gemini" / "config" / "plugins"

    def install_plugins(self, plugins: List[Plugin], dry_run: bool = False) -> int:
        import subprocess
        import shutil
        import tempfile

        installed = 0
        for plugin in plugins:
            count = self._install_plugin(plugin, dry_run)
            installed += count
            if not dry_run:
                console.print(
                    f"[green]Installed Antigravity plugin '{plugin.name}' "
                    f"({count} items) -> {self.target_dir}[/green]"
                )

                # Check if 'agy' executable exists before running it
                if shutil.which("agy"):
                    # `agy plugin install <path>` copies FROM <path> into agy's own
                    # plugin store and registers it in agy's import ledger (the step
                    # that actually makes hooks/skills take effect — a plugin dropped
                    # on disk without this never gets loaded). It refuses to run when
                    # <path> already IS that plugin store (self.target_dir / name is
                    # exactly that when target_dir is agy's own default), so hand it a
                    # throwaway copy instead of the path we just wrote to.
                    plugin_base = self.target_dir / plugin.name
                    with tempfile.TemporaryDirectory(prefix="llm-sync-agy-") as staging:
                        staging_path = Path(staging) / plugin.name
                        shutil.copytree(plugin_base, staging_path)
                        try:
                            subprocess.run(
                                ["agy", "plugin", "install", str(staging_path)],
                                check=True,
                                capture_output=True,
                            )
                            console.print(f"[green]Registered plugin '{plugin.name}' with agy[/green]")
                        except subprocess.CalledProcessError as e:
                            console.print(f"[red]Failed to register '{plugin.name}' with agy: {e.stderr.decode().strip()}[/red]")
                else:
                    console.print("[yellow]agy CLI not found in PATH; skipping registration[/yellow]")

        return installed

    def _install_plugin(self, plugin: Plugin, dry_run: bool) -> int:
        plugin_base = self.target_dir / plugin.name
        return (
            self._install_manifest(plugin_base, plugin, dry_run)
            + self._install_skills(plugin_base, plugin, dry_run)
            + self._install_commands(plugin_base, plugin, dry_run)
            + self._install_hooks(plugin_base, plugin, dry_run)
        )

    def _install_manifest(self, plugin_base: Path, plugin: Plugin, dry_run: bool) -> int:
        manifest = {
            "name": plugin.name,
            "version": plugin.version,
            "description": plugin.description,
        }
        dest = plugin_base / "plugin.json"
        if dry_run:
            console.print(f"[blue]Would write Antigravity plugin manifest {dest}[/blue]")
        else:
            plugin_base.mkdir(parents=True, exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
                f.write("\n")
        return 1

    def _install_skills(self, plugin_base: Path, plugin: Plugin, dry_run: bool) -> int:
        skills_base = plugin_base / "skills"
        for skill in plugin.skills:
            dest = skills_base / skill.name / "SKILL.md"
            frontmatter = {
                "name": skill.name,
                "description": skill.description or f"Skill {skill.name}",
            }
            fm_yaml = yaml.dump(frontmatter, sort_keys=False)
            content = f"---\n{fm_yaml}---\n\n{skill.content}"

            if dry_run:
                console.print(f"[blue]Would write Antigravity skill {dest}[/blue]")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
        return len(plugin.skills)

    def _install_commands(self, plugin_base: Path, plugin: Plugin, dry_run: bool) -> int:
        # Commands sync as skills in Antigravity — there's no explicit-invocation
        # equivalent (see AGENTS.md's "$ARGUMENTS limitation" note).
        skills_base = plugin_base / "skills"
        for cmd in plugin.commands:
            # Replace slashes with hyphens for flat skill naming structure
            normalized_name = cmd.name.replace("/", "-")
            dest = skills_base / normalized_name / "SKILL.md"
            frontmatter = {
                "name": normalized_name,
                "description": cmd.description or f"Command {normalized_name}",
            }
            fm_yaml = yaml.dump(frontmatter, sort_keys=False)
            clean_content = self._strip_frontmatter(cmd.content)
            content = f"---\n{fm_yaml}---\n\n{clean_content}"

            if dry_run:
                console.print(f"[blue]Would write Antigravity command skill {dest}[/blue]")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
        return len(plugin.commands)

    def _install_hooks(self, plugin_base: Path, plugin: Plugin, dry_run: bool) -> int:
        # Claude's schema (event -> list of {matcher, hooks} groups) must be
        # converted to Antigravity's (event -> single {matcher, hooks} object)
        # or the plugin fails to parse at every agy session start — see
        # _to_antigravity_hook_spec's docstring.
        if not plugin.hooks:
            return 0
        dest = plugin_base / "hooks.json"
        antigravity_hooks = {
            event: _to_antigravity_hook_spec(entries)
            for event, entries in plugin.hooks.items()
        }
        if dry_run:
            console.print(f"[blue]Would write Antigravity hooks {dest}[/blue]")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(antigravity_hooks, f, indent=2)
                f.write("\n")
        return 1

    def _strip_frontmatter(self, content: str) -> str:
        """Remove the first YAML frontmatter block (--- ... ---) from content."""
        return re.sub(r'^---\s*\n.*?\n---\s*\n?', '', content, count=1, flags=re.DOTALL)
