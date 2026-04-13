#!/usr/bin/env python3
"""
Validate Bedrock model mappings and generate config.

Usage:
    python scripts/validate_bedrock_models.py --validate    # Validate hardcoded mapping
    python scripts/validate_bedrock_models.py --generate    # Generate bedrock_models.json
    python scripts/validate_bedrock_models.py --list        # List available models
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def get_bedrock_models() -> list[str]:
    """Fetch available Claude models from AWS Bedrock."""
    try:
        result = subprocess.run(
            [
                "aws", "bedrock", "list-foundation-models",
                "--region", "us-east-1",
                "--by-provider", "anthropic",
                "--query", "modelSummaries[?contains(modelId, 'claude')].modelId",
                "--output", "text"
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        models = [m.strip() for m in result.stdout.strip().split() if m.strip()]
        return sorted(models)
    except subprocess.CalledProcessError as e:
        print(f"Error fetching models from Bedrock: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Timeout fetching models from Bedrock", file=sys.stderr)
        sys.exit(1)


def normalize_model_name(bedrock_id: str) -> str:
    """
    Convert Bedrock model ID to normalized name for mapping.

    Examples:
        anthropic.claude-3-5-haiku-20241022-v1:0 -> claude-3-5-haiku-20241022
        anthropic.claude-sonnet-4-6 -> claude-sonnet-4-6
        anthropic.claude-opus-4-6-v1 -> claude-opus-4-6
    """
    # Remove anthropic. prefix
    name = bedrock_id.replace("anthropic.", "")

    # Remove version suffix patterns: -v1:0, -v1, :0, etc.
    # Keep the date suffix (YYYYMMDD) if present
    if "-v1:0" in name:
        name = name.replace("-v1:0", "")
    elif "-v1" in name:
        name = name.replace("-v1", "")
    elif name.endswith(":0"):
        name = name[:-2]

    return name


def build_model_mapping(bedrock_models: list[str]) -> dict[str, str]:
    """
    Build mapping from normalized names to Bedrock IDs.

    Returns:
        {
            "claude-3-5-haiku-20241022": "anthropic.claude-3-5-haiku-20241022-v1:0",
            "claude-sonnet-4-6": "anthropic.claude-sonnet-4-6",
            ...
        }
    """
    mapping = {}
    for bedrock_id in bedrock_models:
        normalized = normalize_model_name(bedrock_id)
        mapping[normalized] = bedrock_id
    return mapping


def get_loaded_mapping() -> dict[str, str]:
    """Load model mapping from config file (what the proxy actually uses)."""
    config_file = Path(__file__).parent.parent / "config" / "bedrock_models.json"

    if not config_file.exists():
        print(f"Warning: {config_file} not found, cannot validate", file=sys.stderr)
        return {}

    try:
        with open(config_file) as f:
            data = json.load(f)
            # The proxy adds us. prefix, so we need to add it for comparison
            return {
                normalized: f"us.{bedrock_id}"
                for normalized, bedrock_id in data.get("models", {}).items()
            }
    except Exception as e:
        print(f"Error loading {config_file}: {e}", file=sys.stderr)
        return {}


def validate_mapping(hardcoded: dict[str, str], actual: dict[str, str]) -> bool:
    """
    Validate hardcoded mapping against actual Bedrock models.

    Returns True if valid, False if issues found.
    """
    issues = []

    # Check for models in hardcoded that don't exist in Bedrock
    for normalized, bedrock_id in hardcoded.items():
        # Skip comments or empty entries
        if not normalized or not bedrock_id:
            continue

        # Check if the bedrock_id (without us. prefix) exists
        base_id = bedrock_id.replace("us.", "").replace("eu.", "").replace("global.", "")

        if base_id not in [m for m in actual.values()]:
            # Check if normalized key exists as a model
            if normalized not in actual:
                issues.append(f"❌ {normalized} -> {bedrock_id} (model not found in Bedrock)")
            else:
                actual_id = actual[normalized]
                if base_id != actual_id:
                    issues.append(f"⚠️  {normalized} -> {bedrock_id} (actual: {actual_id})")

    # Check for models in Bedrock that aren't in hardcoded
    missing = []
    for normalized, bedrock_id in actual.items():
        if normalized not in hardcoded:
            missing.append(f"📝 {normalized} (available but not mapped)")

    if issues:
        print("Validation Issues:")
        for issue in issues:
            print(f"  {issue}")
        print()

    if missing:
        print("Missing Models (available in Bedrock but not in mapping):")
        for m in missing:
            print(f"  {m}")
        print()

    if not issues and not missing:
        print("✅ All mappings valid!")
        return True

    return len(issues) == 0  # Allow missing models, but not invalid ones


def generate_config(mapping: dict[str, str], output_file: Path) -> None:
    """Generate bedrock_models.json config file."""
    config = {
        "_comment": "Auto-generated from AWS Bedrock list-foundation-models",
        "_generated": subprocess.check_output(["date", "-Iseconds"], text=True).strip(),
        "models": mapping
    }

    with open(output_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✅ Generated {output_file}")
    print(f"   {len(mapping)} models")


def list_models(models: list[str]) -> None:
    """List all available Claude models on Bedrock."""
    print(f"Available Claude models on Bedrock ({len(models)}):\n")

    # Group by version family
    families = {}
    for model in models:
        normalized = normalize_model_name(model)
        # Extract family (e.g., "claude-3-5-haiku", "claude-sonnet-4")
        parts = normalized.split("-")
        if len(parts) >= 3:
            family = "-".join(parts[:4])  # claude-3-5-haiku or claude-sonnet-4
        else:
            family = normalized

        if family not in families:
            families[family] = []
        families[family].append((normalized, model))

    for family in sorted(families.keys()):
        print(f"  {family}:")
        for normalized, bedrock_id in families[family]:
            print(f"    {normalized:<35} -> {bedrock_id}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Validate and generate Bedrock model mappings",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--validate", action="store_true", help="Validate hardcoded mapping")
    parser.add_argument("--generate", action="store_true", help="Generate bedrock_models.json")
    parser.add_argument("--list", action="store_true", help="List available models")
    parser.add_argument("--output", type=Path, default=Path("config/bedrock_models.json"),
                       help="Output file for --generate")

    args = parser.parse_args()

    if not (args.validate or args.generate or args.list):
        parser.print_help()
        sys.exit(1)

    # Fetch models from Bedrock
    print("Fetching models from AWS Bedrock...")
    bedrock_models = get_bedrock_models()
    actual_mapping = build_model_mapping(bedrock_models)

    if args.list:
        list_models(bedrock_models)

    if args.generate:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        generate_config(actual_mapping, args.output)

    if args.validate:
        print("\nValidating config/bedrock_models.json against live AWS Bedrock...")
        loaded = get_loaded_mapping()
        if not loaded:
            print("No config to validate - run --generate first", file=sys.stderr)
            sys.exit(1)
        valid = validate_mapping(loaded, actual_mapping)
        sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
