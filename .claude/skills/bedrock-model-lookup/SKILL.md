---
name: bedrock-model-lookup
description: Discover new Claude models available in AWS Bedrock and add them to the claude-proxy configuration.
model: haiku
---

# Bedrock Model Lookup

Discover new Claude models available in AWS Bedrock and add them to the claude-proxy configuration.

## When to Use This Skill

Use this skill when:
- A new Claude model is released (e.g., Claude Opus 4.7, Claude Sonnet 4.7)
- Claude Code returns "Invalid model name" errors from Bedrock
- You need to verify the correct Bedrock model ID for a Claude model
- You want to update the claude-proxy model mapping with new models

> For selecting the right Claude model for a task based on capability and cost, apply the `meta-model-selection` skill.

## Discovery Methods

### Method 1: AWS CLI (Fastest)

List all available Anthropic models in your region:

```bash
aws bedrock list-foundation-models \
  --region=us-west-2 \
  --by-provider anthropic \
  --query "modelSummaries[*].[modelId, modelName]" \
  --output table
```

Filter for specific models:

```bash
# Find all Claude 4.6 models
aws bedrock list-foundation-models \
  --region=us-west-2 \
  --by-provider anthropic \
  --query "modelSummaries[?contains(modelId, '4-6')].[modelId, modelName]" \
  --output table

# Find latest models (check last month)
aws bedrock list-foundation-models \
  --region=us-west-2 \
  --by-provider anthropic \
  --query "modelSummaries[?created >= '2026-02-01'].[modelId, modelName, created]" \
  --output table
```

Get detailed model information:

```bash
aws bedrock get-foundation-model \
  --region=us-west-2 \
  --model-identifier "anthropic.claude-sonnet-4-6" \
  --query "{ModelId: modelId, ModelArn: modelArn, InputModalities: inputModalities, OutputModalities: outputModalities, Streaming: responseStreamingSupported}"
```

### Method 2: AWS Documentation (Most Comprehensive)

Search the official AWS Bedrock documentation:

1. **Supported Models Page**: [https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html) — complete table of all models with IDs, regions, and capabilities
2. **Claude on Bedrock Page**: [https://platform.claude.com/docs/en/build-with-claude/claude-on-amazon-bedrock](https://platform.claude.com/docs/en/build-with-claude/claude-on-amazon-bedrock) — official Anthropic docs, model ID table with global vs regional profiles
3. **AWS What's New**: [https://aws.amazon.com/about-aws/whats-new/](https://aws.amazon.com/about-aws/whats-new/) — search "Claude" or "Bedrock Anthropic"

### Method 3: Web Search (For Breaking News)

When AWS CLI and docs aren't updated yet, search: `AWS Bedrock Claude [MODEL_NAME] model ID 2026`

## Model ID Formats

**CRITICAL**: AWS Bedrock requires **inference profiles** (a `us.`/`global.`/`eu.`/etc. prefix) for ALL Claude models with on-demand throughput — Claude 3.x, 4, and 4.5. Base model IDs without a prefix only work for Claude 4.6+, and will otherwise fail with a `ValidationException`. See [Model ID Formats](references/model-id-formats.md) for the full breakdown of US/global/regional profile syntax and naming patterns.

## Adding Models to Claude-Proxy

### Step 1: Verify Model Availability

```bash
aws bedrock invoke-model \
  --region us-west-2 \
  --model-id "anthropic.claude-sonnet-4-6" \
  --body '{"max_tokens":100,"messages":[{"role":"user","content":"Hello"}],"anthropic_version":"bedrock-2023-05-31"}' \
  /tmp/response.json && cat /tmp/response.json
```

### Step 2: Update Model Mapping

Edit the Bedrock provider model mapping in `providers/bedrock.py`:

```python
def _convert_to_bedrock_model(self, model: str) -> str:
    """Convert model name to Bedrock format."""
    model_mapping = {
        # Add new model here (normalized name → Bedrock inference profile)
        # IMPORTANT: Use inference profile format (us./global./eu./jp./apac. prefix)
        # Base model IDs without prefixes will FAIL for on-demand throughput!
        "claude-sonnet-4-7": "us.anthropic.claude-sonnet-4-7-v1:0",  # US inference profile
        "claude-opus-4-7": "us.anthropic.claude-opus-4-7-v1:0",      # US inference profile

        # Existing models...
        "claude-opus-4-6": "anthropic.claude-opus-4-6-v1",           # Base ID (4.6 only)
        "claude-sonnet-4-6": "anthropic.claude-sonnet-4-6",          # Base ID (4.6 only)
        "claude-sonnet-4-5-20250929": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        # ...
    }
```

**Key points:**
- **Left side (key)**: Normalized Claude Code model name (no provider prefix, no `us.`/`global.`)
- **Right side (value)**: Bedrock inference profile ID (with region prefix for 4.5 and earlier)
- **CRITICAL**: Claude 4.5 and earlier models MUST use inference profile format — `anthropic.claude-sonnet-4-5-20250929-v1:0` alone WILL FAIL; `us.anthropic.claude-sonnet-4-5-20250929-v1:0` is correct
- Claude 4.6+ models can use base format without prefix

### Step 3: Update Beta Feature Compatibility (if applicable)

If the new model supports new beta features, update `BEDROCK_BETA_COMPATIBILITY`:

```python
BEDROCK_BETA_COMPATIBILITY = {
    "new-beta-feature-2026-03-01": [
        "claude-sonnet-4-7",  # Add new model support
        "claude-opus-4-7",
    ],
    # Existing features...
}
```

### Step 4: Test the Changes

```bash
# Restart the proxy
cd ~/dotfiles/stapler-scripts/claude-proxy
make restart

# Test with Claude Code
claude chat --model claude-sonnet-4-7 "Hello, world"

# Check logs for errors
make app-logs
```

### Step 5: Update Documentation

Update `claude-proxy/.claude/CLAUDE.md` to document the new model in the "Supported Models" section if it exists, or add it to the architecture notes.

## Troubleshooting and Common Patterns

If you hit "Invalid model name" errors, region-specific access issues, or need the workflow for a new major version release vs. a same-version model update, see [Troubleshooting and Common Patterns](references/troubleshooting-and-patterns.md).

## Quick Reference

**Essential Commands:**

```bash
# List all Anthropic models in Bedrock
aws bedrock list-foundation-models --by-provider anthropic --region us-west-2

# Get specific model details
aws bedrock get-foundation-model --model-identifier "anthropic.claude-sonnet-4-6" --region us-west-2

# Test model with API call
aws bedrock invoke-model \
  --model-id "anthropic.claude-sonnet-4-6" \
  --region us-west-2 \
  --body '{"max_tokens":100,"messages":[{"role":"user","content":"test"}],"anthropic_version":"bedrock-2023-05-31"}' \
  /tmp/test.json

# Restart proxy after changes
cd ~/dotfiles/stapler-scripts/claude-proxy && make restart

# Monitor for errors
tail -f /tmp/claude-proxy.app.log
```

**Key Files:**
- Model mapping: `~/dotfiles/stapler-scripts/claude-proxy/providers/bedrock.py`
- Beta features: Same file, `BEDROCK_BETA_COMPATIBILITY` dict
- Service config: `~/dotfiles/stapler-scripts/claude-proxy/com.claude-proxy.plist`
- Documentation: `~/dotfiles/stapler-scripts/claude-proxy/.claude/CLAUDE.md`

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `meta-model-selection` | Choosing which Claude model tier (Opus/Sonnet/Haiku) to use for a task |
| `meta-research-workflow` | Researching AWS docs or What's New for newly released model information |
| `meta-claude-technique-evaluator` | Evaluating whether to adopt a newly available model into the workflow |

## References

- [Model ID Formats](references/model-id-formats.md) — inference profile syntax, regional/global routing, naming patterns
- [Troubleshooting and Common Patterns](references/troubleshooting-and-patterns.md) — error diagnosis and release-handling workflows
- [AWS Bedrock Supported Models](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html)
- [Claude on Amazon Bedrock (Anthropic)](https://platform.claude.com/docs/en/build-with-claude/claude-on-amazon-bedrock)
- [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Anthropic Model Releases](https://www.anthropic.com/news)
