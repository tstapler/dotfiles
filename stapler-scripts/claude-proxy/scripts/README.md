# Claude Proxy Scripts

Validation and config generation scripts for model mappings.

## Model Validation & Config Generation

### Bedrock Models

**Fetch available models from AWS Bedrock and validate mapping:**

```bash
# List all Claude models available on Bedrock
python scripts/validate_bedrock_models.py --list

# Validate hardcoded mapping in providers/bedrock.py
python scripts/validate_bedrock_models.py --validate

# Generate config/bedrock_models.json
python scripts/validate_bedrock_models.py --generate
```

**Requires:** AWS credentials configured (via aws-vault or environment)

**Output:** `config/bedrock_models.json` — Auto-loaded by `BedrockProvider` at runtime

### Anthropic Models

**Fetch live model data from Anthropic API:**

```bash
# List all Claude models available on Anthropic API
python scripts/fetch_anthropic_models.py --list

# Generate config/anthropic_models.json
python scripts/fetch_anthropic_models.py --generate
```

**Authentication:** Uses `CLAUDE_CODE_OAUTH_TOKEN` from your environment (same token Claude Code uses)

**Output:** `config/anthropic_models.json` — Reference config with full model capabilities (not auto-loaded by proxy)

**Model data includes:**
- Model ID, display name, creation date
- Max input/output tokens
- Capabilities: thinking, code execution, context management, effort, structured outputs, etc.

## CI Integration

**Add to test suite:**

```python
# tests/test_bedrock_models.py
def test_bedrock_models_validation():
    """Validate Bedrock model mapping against live AWS API."""
    result = subprocess.run(
        ["python", "scripts/validate_bedrock_models.py", "--validate"],
        capture_output=True
    )
    assert result.returncode == 0, "Bedrock model validation failed"
```

**Run in CI:**

```yaml
# .github/workflows/test.yml
- name: Validate Bedrock models
  run: python scripts/validate_bedrock_models.py --validate
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

## Regenerating Configs

**When new Claude models are released:**

1. Regenerate both configs:
   ```bash
   make regenerate-configs  # Runs both scripts
   # OR individually:
   python scripts/validate_bedrock_models.py --generate  # From AWS Bedrock
   python scripts/fetch_anthropic_models.py --generate   # From Anthropic API
   ```

2. Reload proxy to apply new Bedrock models:
   ```bash
   make reload  # Proxy auto-loads config/bedrock_models.json
   ```

3. Run validation:
   ```bash
   make validate-models
   uv run pytest tests/test_bedrock_models.py
   ```

**Note:** Both scripts fetch live data:
- `validate_bedrock_models.py` queries AWS Bedrock API (requires AWS credentials)
- `fetch_anthropic_models.py` queries Anthropic API (uses `CLAUDE_CODE_OAUTH_TOKEN`)

## Config File Locations

```
claude-proxy/
├── config/
│   ├── bedrock_models.json       # Auto-loaded by BedrockProvider
│   └── anthropic_models.json     # Reference only
└── scripts/
    ├── validate_bedrock_models.py
    ├── fetch_anthropic_models.py
    └── README.md (this file)
```

## How It Works

### Bedrock Provider

The `BedrockProvider` loads `config/bedrock_models.json` at startup:

```python
# providers/bedrock.py
def _load_bedrock_model_mapping() -> Dict[str, str]:
    config_file = Path(__file__).parent.parent / "config" / "bedrock_models.json"
    if config_file.exists():
        with open(config_file) as f:
            data = json.load(f)
            # Add us. inference profile prefix
            return {
                normalized: f"us.{bedrock_id}"
                for normalized, bedrock_id in data["models"].items()
            }
    # Fallback to hardcoded mapping if config missing
    return {...}
```

### Model ID Format

**Anthropic API:**
- `claude-sonnet-4-6` (no prefix, no version)

**AWS Bedrock:**
- Base: `anthropic.claude-sonnet-4-6`
- Inference profile: `us.anthropic.claude-sonnet-4-6` (used by proxy)

**Inconsistencies:**
- Claude 4.6 Opus: `anthropic.claude-opus-4-6-v1` (no `:0`)
- Claude 4.6 Sonnet: `anthropic.claude-sonnet-4-6` (no version)
- Claude 4.5: `anthropic.claude-sonnet-4-5-20250929-v1:0` (standard)

The validation script detects these inconsistencies and generates correct mappings.

## Troubleshooting

**Validation fails with "model not found":**
- Model was removed from Bedrock or doesn't exist yet
- Remove from hardcoded fallback in `providers/bedrock.py`

**Proxy returns 400 "Invalid model name":**
- Model ID format is wrong
- Run `--validate` to check mapping
- Regenerate config with `--generate`

**AWS credentials error:**
- Ensure `aws-vault exec dev` or AWS env vars are set
- Test with: `aws bedrock list-foundation-models --region us-east-1`
