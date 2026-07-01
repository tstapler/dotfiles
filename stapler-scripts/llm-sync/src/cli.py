import argparse
import sys
from pathlib import Path
from typing import List, Set, Dict, Any, Optional
from rich.console import Console

# Allow running from src directly or as module
try:
    from .sources.claude import ClaudeSource
    from .sources.mcp_config import McpConfigSource
    from .sources.plugins import PluginSource
    from .targets.gemini import GeminiTarget, AntigravityTarget
    from .targets.opencode import OpenCodeTarget
    from .targets.claude_settings import ClaudeSettingsTarget
    from .targets.claude_plugin_installer import ClaudePluginInstaller
    from .targets.antigravity_plugin_installer import AntigravityPluginInstaller
    from .targets.antigravity_mcp import AntigravityMcpTarget
    from .core import Agent, Skill, Command
    from .state import SyncStateManager
except ImportError:
    # Fallback if run as script (hacky but useful during dev)
    sys.path.append(str(Path(__file__).parent))
    from sources.claude import ClaudeSource
    from sources.mcp_config import McpConfigSource
    from sources.plugins import PluginSource
    from targets.gemini import GeminiTarget, AntigravityTarget
    from targets.opencode import OpenCodeTarget
    from targets.claude_settings import ClaudeSettingsTarget
    from targets.claude_plugin_installer import ClaudePluginInstaller
    from targets.antigravity_plugin_installer import AntigravityPluginInstaller
    from targets.antigravity_mcp import AntigravityMcpTarget
    from core import Agent, Skill, Command
    from state import SyncStateManager

console = Console()

def cleanup_legacy_files(target, items: List, dry_run: bool = False):
    """Remove files that don't match the namespaced version if they exist in the root."""
    target_name = target.__class__.__name__
    namespaced_names = [item.name for item in items if '/' in item.name]
    deleted_count = 0
    if hasattr(target, 'agents_dir'):
        for name in namespaced_names:
            legacy_name = name.split('/')[-1]
            legacy_file = target.agents_dir / f"{legacy_name}.md"
            if legacy_file.exists():
                if dry_run: console.print(f"[yellow]Would delete legacy agent {legacy_file}[/yellow]")
                else:
                    legacy_file.unlink()
                    console.print(f"[red]Deleted legacy agent {legacy_file}[/red]")
                    deleted_count += 1
    if hasattr(target, 'commands_dir'):
        ext = ".toml" if "Gemini" in target_name else ".md"
        for name in namespaced_names:
            legacy_name = name.split('/')[-1]
            legacy_file = target.commands_dir / f"{legacy_name}{ext}"
            if legacy_file.exists():
                if dry_run: console.print(f"[yellow]Would delete legacy command {legacy_file}[/yellow]")
                else:
                    legacy_file.unlink()
                    console.print(f"[red]Deleted legacy command {legacy_file}[/red]")
                    deleted_count += 1
    return deleted_count

def sync_to_target(source, target, state_manager: SyncStateManager, dry_run: bool, force: bool):
    source_name = source.__class__.__name__
    target_name = target.__class__.__name__
    
    console.print(f"\n[bold]Syncing {source_name} -> {target_name}...[/bold]")
    
    # Load all items from source
    agents = source.load_agents()
    skills = source.load_skills()
    commands = source.load_commands()
    
    def get_changed(items: List, item_type: str):
        changed = []
        for item in items:
            current_hash = item.get_hash()
            last_hash = state_manager.get_hash('to-target', target_name, item_type, item.name)
            if force or current_hash != last_hash:
                changed.append(item)
        return changed

    changed_agents = get_changed(agents, 'agents')
    changed_skills = get_changed(skills, 'skills')
    changed_commands = get_changed(commands, 'commands')
    
    total_found = len(agents) + len(skills) + len(commands)
    total_changed = len(changed_agents) + len(changed_skills) + len(changed_commands)
    
    console.print(f"Detected {total_changed}/{total_found} modified items.")

    counts = []
    if changed_agents:
        a_saved = target.save_agents(changed_agents, dry_run=dry_run, force=True) # force=True because we've already filtered
        counts.append(f"{a_saved} agents")
        if not dry_run:
            for a in changed_agents: state_manager.set_hash('to-target', target_name, 'agents', a.name, a.get_hash())
            
    if changed_skills:
        s_saved = target.save_skills(changed_skills, dry_run=dry_run, force=True)
        counts.append(f"{s_saved} skills")
        if not dry_run:
            for s in changed_skills: state_manager.set_hash('to-target', target_name, 'skills', s.name, s.get_hash())
            
    if changed_commands:
        c_saved = target.save_commands(changed_commands, dry_run=dry_run, force=True)
        counts.append(f"{c_saved} commands")
        if not dry_run:
            for c in changed_commands: state_manager.set_hash('to-target', target_name, 'commands', c.name, c.get_hash())
    
    if counts:
        console.print(f"[green]Saved {', '.join(counts)} to {target_name}[/green]")
    else:
        console.print("[yellow]Everything is up to date.[/yellow]")

def sync_from_target(source, target, state_manager: SyncStateManager, dry_run: bool, force: bool):
    source_name = source.__class__.__name__
    target_name = target.__class__.__name__
    
    console.print(f"\n[bold]Syncing {target_name} -> {source_name}...[/bold]")
    
    t_agents = target.load_agents()
    t_skills = target.load_skills()
    t_commands = target.load_commands()
    
    def get_new_or_modified(items: List, item_type: str):
        results = []
        for item in items:
            current_hash = item.get_hash()
            last_hash = state_manager.get_hash('from-target', target_name, item_type, item.name)
            
            # For pull, we only care if it's DIFFERENT from what we last saw on this target.
            # This detects updates made ON the target platform.
            if force or current_hash != last_hash:
                results.append(item)
        return results

    new_agents = get_new_or_modified(t_agents, 'agents')
    new_skills = get_new_or_modified(t_skills, 'skills')
    new_commands = get_new_or_modified(t_commands, 'commands')

    counts = []
    if new_agents:
        a_saved = source.save_agents(new_agents, dry_run=dry_run, force=force)
        counts.append(f"{a_saved} agents")
        if not dry_run:
            for a in new_agents: state_manager.set_hash('from-target', target_name, 'agents', a.name, a.get_hash())
            
    if new_skills:
        s_saved = source.save_skills(new_skills, dry_run=dry_run, force=force)
        counts.append(f"{s_saved} skills")
        if not dry_run:
            for s in new_skills: state_manager.set_hash('from-target', target_name, 'skills', s.name, s.get_hash())
            
    if new_commands:
        c_saved = source.save_commands(new_commands, dry_run=dry_run, force=force)
        counts.append(f"{c_saved} commands")
        if not dry_run:
            for c in new_commands: state_manager.set_hash('from-target', target_name, 'commands', c.name, c.get_hash())
    
    if counts:
        console.print(f"[green]Saved {', '.join(counts)} from {target_name} to {source_name}[/green]")
    else:
        console.print(f"[yellow]No modifications detected in {target_name}.[/yellow]")

def sync_plugins(plugin_source: PluginSource, dry_run: bool, antigravity_dir: Optional[Path] = None):
    plugins = plugin_source.load_plugins()
    if not plugins:
        console.print("[yellow]No plugins found.[/yellow]")
        return

    console.print(f"\n[bold]Installing {len(plugins)} plugin(s)...[/bold]")

    if plugin_source.global_plugins_dir:
        global_plugins = [
            p for p in plugins
            if p.source_dir and str(plugin_source.global_plugins_dir) in (p.source_dir or "")
        ]
        if global_plugins:
            # Claude Global
            installer = ClaudePluginInstaller(target_dir=Path.home() / ".claude")
            console.print(f"[dim]Claude Global install -> {installer.target_dir}[/dim]")
            installer.install_plugins(global_plugins, dry_run=dry_run)

            # Antigravity Global
            ag_target = (antigravity_dir or (Path.home() / ".gemini" / "antigravity-cli")) / "plugins"
            ag_installer = AntigravityPluginInstaller(target_dir=ag_target)
            console.print(f"[dim]Antigravity Global install -> {ag_installer.target_dir}[/dim]")
            ag_installer.install_plugins(global_plugins, dry_run=dry_run)

    if plugin_source.local_plugins_dir:
        local_plugins = [
            p for p in plugins
            if p.source_dir and str(plugin_source.local_plugins_dir) in (p.source_dir or "")
        ]
        if local_plugins:
            # Claude Local
            local_claude = Path.cwd() / ".claude"
            installer = ClaudePluginInstaller(target_dir=local_claude)
            console.print(f"[dim]Claude Local install -> {installer.target_dir}[/dim]")
            installer.install_plugins(local_plugins, dry_run=dry_run)

            # Antigravity Local (workspace customization root .agents/plugins)
            local_ag = Path.cwd() / ".agents" / "plugins"
            ag_installer = AntigravityPluginInstaller(target_dir=local_ag)
            console.print(f"[dim]Antigravity Local install -> {ag_installer.target_dir}[/dim]")
            ag_installer.install_plugins(local_plugins, dry_run=dry_run)



def sync_mcp(mcp_source: McpConfigSource, settings_target: ClaudeSettingsTarget, dry_run: bool):
    console.print(f"\n[bold]Syncing MCP servers -> {settings_target.settings_file}...[/bold]")
    servers = mcp_source.load_servers()
    if not servers:
        console.print("[yellow]No MCP servers found.[/yellow]")
        return
    count = settings_target.save_mcp_servers(servers, dry_run=dry_run)
    if not dry_run:
        console.print(f"[green]Wrote {count} MCP servers to {settings_target.settings_file}[/green]")

def main():
    parser = argparse.ArgumentParser(description="Sync LLM agents between Claude, Gemini, and OpenCode")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes")
    parser.add_argument("--force", action="store_true", help="Force sync regardless of content hash")
    parser.add_argument("--cleanup", action="store_true", help="Remove legacy non-namespaced files")
    parser.add_argument("--target", choices=['gemini', 'opencode', 'antigravity', 'all'], default='all', help="Target platform(s)")
    parser.add_argument("--direction", choices=['to-target', 'from-target', 'both'], default='to-target',
                        help="Sync direction")
    parser.add_argument("--state-file", type=Path, help="Custom state file path")

    # Custom paths
    parser.add_argument("--source-dir", type=Path, help="Override base directory for Claude assets")
    parser.add_argument("--gemini-dir", type=Path, help="Override base directory for Gemini assets")
    parser.add_argument("--antigravity-dir", type=Path, help="Override base directory for Antigravity config")
    parser.add_argument("--opencode-dir", type=Path, help="Override base directory for OpenCode assets")
    parser.add_argument("--mcp-global-config", type=Path, help="Override global MCP servers JSON file")
    parser.add_argument("--mcp-local-config", type=Path, help="Override machine-local MCP servers JSON file")
    parser.add_argument("--claude-settings-file", type=Path, help="Override path to ~/.claude/settings.json")

    # Plugin install
    parser.add_argument("--plugins-global-dir", type=Path,
                        help="Directory of plugins to install globally")
    parser.add_argument("--plugins-local-dir", type=Path,
                        help="Directory of plugins to install locally")
    parser.add_argument("--plugins-only", action="store_true",
                        help="Only sync plugins (skip agents, skills, commands, MCP)")

    args = parser.parse_args()

    console.print("[bold]LLM Agent Sync (Hash-based)[/bold]")

    state_manager = SyncStateManager(args.state_file)

    try:
        plugin_source = PluginSource(
            global_plugins_dir=args.plugins_global_dir,
            local_plugins_dir=args.plugins_local_dir,
        )
        sync_plugins(plugin_source, args.dry_run, antigravity_dir=args.antigravity_dir)

        if not args.plugins_only:
            source_params = {}
            if args.source_dir:
                source_params['agents_dir'] = args.source_dir / "agents"
                source_params['skills_dir'] = args.source_dir / "skills"
                source_params['commands_dir'] = args.source_dir / "commands"
            claude = ClaudeSource(**source_params)

            targets = []
            if args.target in ['gemini', 'all']:
                gemini_params = {}
                if args.gemini_dir:
                    gemini_params['agents_dir'] = args.gemini_dir / "agents"
                    gemini_params['skills_dir'] = args.gemini_dir / "skills"
                    gemini_params['commands_dir'] = args.gemini_dir / "commands"
                targets.append(GeminiTarget(**gemini_params))

            if args.target in ['antigravity', 'all']:
                antigravity_params = {}
                if args.antigravity_dir:
                    antigravity_params['agents_dir'] = args.antigravity_dir / "agents"
                    antigravity_params['skills_dir'] = args.antigravity_dir / "skills"
                targets.append(AntigravityTarget(**antigravity_params))

            if args.target in ['opencode', 'all']:
                opencode_params = {}
                if args.opencode_dir:
                    opencode_params['agents_dir'] = args.opencode_dir / "agents"
                    opencode_params['commands_dir'] = args.opencode_dir / "commands"
                targets.append(OpenCodeTarget(**opencode_params))

            if args.cleanup:
                console.print("\n[bold]Cleaning up legacy files...[/bold]")
                agents = claude.load_agents()
                commands = claude.load_commands()
                for t in targets:
                    cleanup_legacy_files(t, agents + commands, dry_run=args.dry_run)

            for target in targets:
                if args.direction in ['to-target', 'both']:
                    sync_to_target(claude, target, state_manager, args.dry_run, args.force)

                if args.direction in ['from-target', 'both']:
                    sync_from_target(claude, target, state_manager, args.dry_run, args.force)

            mcp_source = McpConfigSource(
                global_config_file=args.mcp_global_config,
                local_config_file=args.mcp_local_config,
            )
            claude_settings = ClaudeSettingsTarget(settings_file=args.claude_settings_file)
            sync_mcp(mcp_source, claude_settings, args.dry_run)

            antigravity_mcp = AntigravityMcpTarget()
            sync_mcp(mcp_source, antigravity_mcp, args.dry_run)

        if not args.dry_run:
            state_manager.save()
            
        console.print(f"\n[bold green]Operations Complete.[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]An error occurred:[/bold red] {e}")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()
