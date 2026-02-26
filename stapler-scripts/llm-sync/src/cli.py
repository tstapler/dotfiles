import argparse
import sys
from pathlib import Path
from rich.console import Console

# Allow running from src directly or as module
try:
    from .sources.claude import ClaudeSource
    from .targets.gemini import GeminiTarget
    from .targets.opencode import OpenCodeTarget
except ImportError:
    # Fallback if run as script (hacky but useful during dev)
    sys.path.append(str(Path(__file__).parent))
    from sources.claude import ClaudeSource
    from targets.gemini import GeminiTarget
    from targets.opencode import OpenCodeTarget

console = Console()

def main():
    parser = argparse.ArgumentParser(description="Sync LLM agents from Claude to Gemini and OpenCode")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes")
    parser.add_argument("--force", action="store_true", help="Overwrite existing agents")
    parser.add_argument("--target", choices=['gemini', 'opencode', 'all'], default='all', help="Target platform(s) to sync to")

    args = parser.parse_args()

    console.print("[bold]Starting LLM Agent Sync[/bold]")

    # 1. Load from Source
    try:
        source = ClaudeSource()
        agents = source.load_agents()
        skills = source.load_skills()
        commands = source.load_commands()

        console.print(f"Found {len(agents)} agents, {len(skills)} skills, and {len(commands)} commands")

        if not any([agents, skills, commands]):
            console.print("[yellow]Nothing found to sync. Check configuration paths.[/yellow]")
            return

        # 2. Save to Targets
        targets = []
        if args.target in ['gemini', 'all']:
            targets.append(GeminiTarget())
        if args.target in ['opencode', 'all']:
            targets.append(OpenCodeTarget())

        for target in targets:
            target_name = target.__class__.__name__
            console.print(f"\n[bold]Syncing to {target_name}...[/bold]")

            counts = []
            if agents:
                a_saved = target.save_agents(agents, dry_run=args.dry_run, force=args.force)
                counts.append(f"{a_saved} agents")

            if skills:
                s_saved = target.save_skills(skills, dry_run=args.dry_run, force=args.force)
                counts.append(f"{s_saved} skills")

            if commands:
                c_saved = target.save_commands(commands, dry_run=args.dry_run, force=args.force)
                counts.append(f"{c_saved} commands")

            if counts:
                console.print(f"[green]Saved {', '.join(counts)} to {target_name}[/green]")

        console.print(f"\n[bold green]Sync Complete.[/bold green]")

    except Exception as e:
        console.print(f"[bold red]An error occurred:[/bold red] {e}")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    main()
