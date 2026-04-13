"""Test Bedrock model mapping validation."""
import subprocess
import sys
from pathlib import Path


def test_bedrock_models_config_exists():
    """Config file should exist."""
    config_file = Path(__file__).parent.parent / "config" / "bedrock_models.json"
    assert config_file.exists(), f"Missing {config_file} - run: python scripts/validate_bedrock_models.py --generate"


def test_bedrock_models_validation():
    """Validate hardcoded mapping against actual Bedrock models."""
    script = Path(__file__).parent.parent / "scripts" / "validate_bedrock_models.py"
    result = subprocess.run(
        [sys.executable, str(script), "--validate"],
        capture_output=True,
        text=True,
        timeout=30
    )

    # Exit code 0 means validation passed (warnings are OK, errors are not)
    if result.returncode != 0:
        print("\nValidation output:", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)

    assert result.returncode == 0, "Bedrock model mapping validation failed - see output above"
