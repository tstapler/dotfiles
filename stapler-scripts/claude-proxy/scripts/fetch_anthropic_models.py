#!/usr/bin/env python3
"""
Fetch available Claude models from Anthropic API.

Usage:
    python scripts/fetch_anthropic_models.py --list          # List all models
    python scripts/fetch_anthropic_models.py --generate      # Generate anthropic_models.json

Uses Claude Code OAuth token from config.py.
"""
import argparse
import json
import sys
from pathlib import Path

# Add parent dir to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

try:
    import requests
except ImportError:
    print("Error: requests package not installed", file=sys.stderr)
    print("Install: pip install requests", file=sys.stderr)
    sys.exit(1)


def get_anthropic_models() -> list[dict]:
    """Fetch available models from Anthropic API.

    Uses Claude Code OAuth token from config.CLAUDE_CODE_OAUTH_TOKEN.
    API Reference: https://platform.claude.com/docs/en/api/models/list
    """
    token = config.CLAUDE_CODE_OAUTH_TOKEN
    if not token:
        print("Error: CLAUDE_CODE_OAUTH_TOKEN not set in environment", file=sys.stderr)
        print("This is the OAuth token Claude Code uses to authenticate", file=sys.stderr)
        sys.exit(1)

    try:
        resp = requests.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": token,
                "anthropic-version": "2023-06-01"
            },
            timeout=15
        )
        resp.raise_for_status()

        data = resp.json()
        models = []

        for model in data.get("data", []):
            models.append({
                "id": model["id"],
                "display_name": model["display_name"],
                "created_at": model["created_at"],
                "max_input_tokens": model["max_input_tokens"],
                "max_tokens": model["max_tokens"],
                "capabilities": model.get("capabilities", {}),
            })

        return models

    except requests.RequestException as e:
        print(f"Error fetching models from Anthropic API: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def list_models(models: list[dict]) -> None:
    """List all Anthropic models."""
    print(f"Available Claude models on Anthropic API ({len(models)}):\n")

    for model in models:
        # Format capabilities summary
        caps = model.get("capabilities", {})
        cap_list = []
        if caps.get("thinking", {}).get("supported"):
            cap_list.append("thinking")
        if caps.get("code_execution", {}).get("supported"):
            cap_list.append("code_exec")
        if caps.get("context_management", {}).get("supported"):
            cap_list.append("ctx_mgmt")
        if caps.get("effort", {}).get("supported"):
            cap_list.append("effort")

        cap_str = ",".join(cap_list) if cap_list else "basic"

        print(f"  {model['id']:<40} {model['display_name']:<25} "
              f"in:{model['max_input_tokens']:>8} out:{model['max_tokens']:>6}  [{cap_str}]")


def generate_config(models: list[dict], output_file: Path) -> None:
    """Generate anthropic_models.json config file."""
    from datetime import datetime

    config = {
        "_comment": "Claude models fetched from Anthropic API /v1/models",
        "_source": "https://api.anthropic.com/v1/models",
        "_api_docs": "https://platform.claude.com/docs/en/api/models/list",
        "_generated": datetime.now().isoformat(),
        "models": {m["id"]: m for m in models}
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✅ Generated {output_file}")
    print(f"   {len(models)} models")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Claude models from Anthropic API",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--list", action="store_true", help="List available models")
    parser.add_argument("--generate", action="store_true", help="Generate anthropic_models.json")
    parser.add_argument("--output", type=Path, default=Path("config/anthropic_models.json"),
                       help="Output file for --generate")

    args = parser.parse_args()

    if not (args.list or args.generate):
        parser.print_help()
        sys.exit(1)

    models = get_anthropic_models()

    if args.list:
        list_models(models)

    if args.generate:
        generate_config(models, args.output)


if __name__ == "__main__":
    main()
