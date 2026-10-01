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
    """Antigravity wants one {matcher, hooks} object per lifecycle event; Claude
    gives a list of {matcher, hooks} groups. Merge matchers (broadest wins) and
    concatenate hooks in order, deduping exact repeats.
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
        import shutil

        installed = 0
        for plugin in plugins:
            count = self._install_plugin(plugin, dry_run)
            installed += count
            if not dry_run:
                console.print(
                    f"[green]Installed Antigravity plugin '{plugin.name}' "
                    f"({count} items) -> {self.target_dir}[/green]"
                )
                if shutil.which("agy"):
                    self._register_with_agy(plugin)
                else:
                    console.print("[yellow]agy CLI not found in PATH; skipping registration[/yellow]")

        return installed

    def _register_with_agy(self, plugin: Plugin) -> None:
        """`agy plugin install <path>` refuses a path that's already its own
        plugin store, so stage a throwaway copy of what we just wrote and hand
        it that instead. Degrades per-plugin on failure — never aborts the loop.
        """
        import subprocess
        import shutil
        import tempfile

        plugin_base = self.target_dir / plugin.name
        try:
            with tempfile.TemporaryDirectory(prefix="llm-sync-agy-") as staging:
                staging_path = Path(staging) / plugin.name
                shutil.copytree(plugin_base, staging_path)
                subprocess.run(
                    ["agy", "plugin", "install", str(staging_path)],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
            console.print(f"[green]Registered plugin '{plugin.name}' with agy[/green]")
        except subprocess.TimeoutExpired:
            console.print(f"[red]Timed out registering '{plugin.name}' with agy after 30s[/red]")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode().strip() if e.stderr else ""
            console.print(f"[red]Failed to register '{plugin.name}' with agy: {stderr}[/red]")
        except OSError as e:
            console.print(f"[red]Failed to stage '{plugin.name}' for agy registration: {e}[/red]")

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

    def _write_skill_markdown(
        self, dest: Path, name: str, description: str, content: str, dry_run: bool
    ) -> None:
        frontmatter = {"name": name, "description": description}
        fm_yaml = yaml.dump(frontmatter, sort_keys=False)
        full_content = f"---\n{fm_yaml}---\n\n{content}"

        if dry_run:
            console.print(f"[blue]Would write Antigravity skill {dest}[/blue]")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(full_content, encoding="utf-8")

    def _install_skills(self, plugin_base: Path, plugin: Plugin, dry_run: bool) -> int:
        skills_base = plugin_base / "skills"
        for skill in plugin.skills:
            dest = skills_base / skill.name / "SKILL.md"
            self._write_skill_markdown(
                dest, skill.name, skill.description or f"Skill {skill.name}", skill.content, dry_run
            )
        return len(plugin.skills)

    def _install_commands(self, plugin_base: Path, plugin: Plugin, dry_run: bool) -> int:
        # Commands sync as skills in Antigravity — there's no explicit-invocation
        # equivalent (see AGENTS.md's "$ARGUMENTS limitation" note).
        skills_base = plugin_base / "skills"
        for cmd in plugin.commands:
            # Replace slashes with hyphens for flat skill naming structure
            normalized_name = cmd.name.replace("/", "-")
            dest = skills_base / normalized_name / "SKILL.md"
            clean_content = self._strip_frontmatter(cmd.content)
            self._write_skill_markdown(
                dest, normalized_name, cmd.description or f"Command {normalized_name}", clean_content, dry_run
            )
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
