import json
import re
import yaml
from pathlib import Path
from typing import List, Optional

try:
    from core import Plugin
except ImportError:
    from ..core import Plugin

from rich.console import Console

console = Console()


class AntigravityPluginInstaller:
    """Installs Antigravity plugins into a global or local customizations plugins directory."""

    def __init__(self, target_dir: Optional[Path] = None):
        # Default to global ~/.gemini/config/plugins/
        self.target_dir = target_dir or Path.home() / ".gemini" / "config" / "plugins"

    def install_plugins(self, plugins: List[Plugin], dry_run: bool = False) -> int:
        import subprocess
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
                
                # Check if 'agy' executable exists before running it
                if shutil.which("agy"):
                    try:
                        plugin_path = str(self.target_dir / plugin.name)
                        # We use the absolute path so agy knows exactly which folder to load
                        subprocess.run(
                            ["agy", "plugin", "install", plugin_path],
                            check=True,
                            capture_output=True
                        )
                        console.print(f"[green]Registered plugin '{plugin.name}' with agy[/green]")
                    except subprocess.CalledProcessError as e:
                        console.print(f"[red]Failed to register '{plugin.name}' with agy: {e.stderr.decode().strip()}[/red]")
                else:
                    console.print("[yellow]agy CLI not found in PATH; skipping registration[/yellow]")

        return installed

    def _install_plugin(self, plugin: Plugin, dry_run: bool) -> int:
        plugin_base = self.target_dir / plugin.name
        count = 0

        # Create plugin manifest
        manifest = {
            "name": plugin.name,
            "version": plugin.version,
            "description": plugin.description,
        }

        if dry_run:
            console.print(f"[blue]Would write Antigravity plugin manifest {plugin_base / 'plugin.json'}[/blue]")
        else:
            plugin_base.mkdir(parents=True, exist_ok=True)
            with open(plugin_base / "plugin.json", "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
                f.write("\n")
        count += 1

        # Install skills
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
            count += 1

        # Install commands (as skills in Antigravity)
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
            count += 1

        # Install hooks
        if plugin.hooks:
            dest = plugin_base / "hooks.json"
            if dry_run:
                console.print(f"[blue]Would write Antigravity hooks {dest}[/blue]")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "w", encoding="utf-8") as f:
                    json.dump(plugin.hooks, f, indent=2)
                    f.write("\n")
            count += 1

        return count

    def _strip_frontmatter(self, content: str) -> str:
        """Remove the first YAML frontmatter block (--- ... ---) from content."""
        return re.sub(r'^---\s*\n.*?\n---\s*\n?', '', content, count=1, flags=re.DOTALL)
