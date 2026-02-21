# Bedrock Model Lookup

Discover new Claude models available in AWS Bedrock and add them to the claude-proxy configuration.

## When to Use This Skill

Use this skill when:
- A new Claude model is released (e.g., Claude Opus 4.7, Claude Sonnet 4.7)
- Claude Code returns "Invalid model name" errors from Bedrock
- You need to verify the correct Bedrock model ID for a Claude model
- You want to update the claude-proxy model mapping with new models

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

1. **Supported Models Page**: [https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html)
   - Complete table of all models with IDs, regions, and capabilities
   - Organized by model provider (Anthropic, etc.)

2. **Claude on Bedrock Page**: [https://platform.claude.com/docs/en/build-with-claude/claude-on-amazon-bedrock](https://platform.claude.com/docs/en/build-with-claude/claude-on-amazon-bedrock)
   - Official Anthropic documentation
   - Includes model ID table with global vs regional profiles
   - Code examples in multiple languages

3. **AWS What's New**: [https://aws.amazon.com/about-aws/whats-new/](https://aws.amazon.com/about-aws/whats-new/)
   - Announcements of new model releases
   - Search for "Claude" or "Bedrock Anthropic"

### Method 3: Web Search (For Breaking News)

When AWS CLI and docs aren't updated yet:

```
Brave Search query: "AWS Bedrock Claude [MODEL_NAME] model ID 2026"
```

Example queries:
- `AWS Bedrock Claude Sonnet 4.6 model ID 2026`
- `AWS Bedrock Claude Opus 4.7 available 2026`
- `Anthropic Claude new model Bedrock 2026`

## Model ID Formats

### Inference Profiles (Critical!)

**CRITICAL**: AWS Bedrock requires **inference profiles** for ALL Claude models with on-demand throughput. Base model IDs without region prefixes will fail with:

```
ValidationException: Invocation of model ID anthropic.claude-sonnet-4-6
with on-demand throughput isn't supported. Retry your request with the ID or ARN of an
inference profile that contains this model.
```

This applies to ALL Claude models: 3.x, 4, 4.5, and 4.6+.

**Inference Profile Formats:**

**US Regional Inference Profile** (recommended for us-west-2 region):
```
us.anthropic.claude-sonnet-4-5-20250929-v1:0
us.anthropic.claude-opus-4-5-20251101-v1:0
us.anthropic.claude-haiku-4-5-20251001-v1:0
```
- Used for Claude 4.5, 4, and 3.x models
- Includes `us.` prefix for US regional routing
- Required for on-demand throughput

**Global Inference Profile** (cross-region routing):
```
global.anthropic.claude-sonnet-4-5-20250929-v1:0
global.anthropic.claude-opus-4-6-v1
```
- Dynamic routing for maximum availability
- Can route to any region with capacity
- May have slightly higher latency due to cross-region routing

**Base Model IDs** (Claude 4.6 only):
```
anthropic.claude-opus-4-6-v1
anthropic.claude-sonnet-4-6
```
- Only works for Claude 4.6+ models
- No region prefix needed for these models
- Automatically uses appropriate inference profile internally

**Regional Inference Profiles** (other regions):
```
eu.anthropic.claude-sonnet-4-5-20250929-v1:0    # EU regional
jp.anthropic.claude-sonnet-4-5-20250929-v1:0    # Japan regional
apac.anthropic.claude-sonnet-4-20250514-v1:0    # Asia-Pacific regional
```
- Route traffic through specific geographic regions
- Required for data residency/compliance
- 10% pricing premium over global profiles

### Model Naming Patterns

Claude models follow consistent naming:

```
[provider].[model-family]-[model-size]-[version-date]-[variant]:[revision]
```

Examples:
- `anthropic.claude-sonnet-4-6` → Claude Sonnet 4.6 (latest)
- `anthropic.claude-opus-4-6-v1` → Claude Opus 4.6 v1
- `anthropic.claude-sonnet-4-5-20250929-v1:0` → Claude Sonnet 4.5 (Sept 29, 2025) v1 rev 0

## Adding Models to Claude-Proxy

### Step 1: Verify Model Availability

Test the model with AWS CLI:

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
    # ... existing code ...

    model_mapping = {
        # Add new model here (normalized name → Bedrock inference profile)
        # IMPORTANT: Use inference profile format (us./global./eu./jp./apac. prefix)
        # Base model IDs without prefixes will FAIL for on-demand throughput!

        # Claude 4.7 models (hypothetical - check AWS docs for actual format)
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
- **CRITICAL**: Claude 4.5 and earlier models MUST use inference profile format (`us.`/`global.`/etc.)
  - ❌ `anthropic.claude-sonnet-4-5-20250929-v1:0` (WILL FAIL)
  - ✅ `us.anthropic.claude-sonnet-4-5-20250929-v1:0` (CORRECT)
- Claude 4.6+ models can use base format without prefix
- Use `us.` prefix for US region (configured in `com.claude-proxy.plist`)
- Alternative: Use `global.` for cross-region routing (may have latency impact)

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

## Troubleshooting

### "Invalid model name" Error

**Symptom**: `400: {'error': 'anthropic_messages: Invalid model name passed in model=claude-sonnet-4-7'}`

**Diagnosis**:
1. Check if model exists in your region: `aws bedrock list-foundation-models --region us-west-2 --by-provider anthropic`
2. Verify you have model access: AWS Console → Bedrock → Model Access
3. Check model ID format: Compare with AWS documentation

**Solutions**:
- Request model access in AWS Console if not enabled
- Verify region supports the model (some models are region-specific)
- Check for typos in model ID mapping

### Model Available but Proxy Can't Find It

**Symptom**: Model shows in AWS CLI but proxy returns "Invalid model name"

**Diagnosis**: Check the model mapping normalization logic

**Solution**:
1. Verify normalized name matches Claude Code's format
2. Test normalization: Add debug logging to `normalize_model_name()` in `providers/__init__.py`
3. Ensure model mapping key matches normalized name exactly

### Region-Specific Model Access

Some models are only available in specific regions. Check:

```bash
# Check model's available regions
aws bedrock get-foundation-model \
  --region us-west-2 \
  --model-identifier "anthropic.claude-sonnet-4-6" \
  --query "regions"
```

If model isn't in your configured region (`AWS_REGION` in `com.claude-proxy.plist`), either:
- Change region in plist and restart service
- Use a model available in your region

## Common Patterns

### When New Major Version Released (e.g., Claude 5)

1. Search AWS news: `aws bedrock claude 5 announcement`
2. List models: `aws bedrock list-foundation-models --by-provider anthropic`
3. Add all variants (Opus, Sonnet, Haiku) to model mapping
4. Update beta compatibility for any new features
5. Test each model variant
6. Document in project CLAUDE.md

### When Model Updated (Same Version, New Date)

1. Find new model ID with date: `aws bedrock list-foundation-models --query "modelSummaries[?contains(modelId, '2026')]"`
2. Add new mapping entry (keep old one for compatibility)
3. Test both old and new model IDs

### When Global Inference Profiles Change

Global inference profiles use different syntax but map to same underlying models:
- `global.anthropic.claude-sonnet-4-6` → routes to `anthropic.claude-sonnet-4-6`
- Proxy should use base format without `global.` prefix
- AWS SDK handles `global.` prefix internally

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

## References

- [AWS Bedrock Supported Models](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html)
- [Claude on Amazon Bedrock (Anthropic)](https://platform.claude.com/docs/en/build-with-claude/claude-on-amazon-bedrock)
- [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Anthropic Model Releases](https://www.anthropic.com/news)
