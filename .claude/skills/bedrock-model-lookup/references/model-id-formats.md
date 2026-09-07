# Model ID Formats

## Inference Profiles (Critical!)

**CRITICAL**: AWS Bedrock requires **inference profiles** for ALL Claude models with on-demand throughput. Base model IDs without region prefixes will fail with:

```
ValidationException: Invocation of model ID anthropic.claude-sonnet-4-6
with on-demand throughput isn't supported. Retry your request with the ID or ARN of an
inference profile that contains this model.
```

This applies to ALL Claude models: 3.x, 4, 4.5, and 4.6+.

### Inference Profile Formats

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

## Model Naming Patterns

Claude models follow consistent naming:

```
[provider].[model-family]-[model-size]-[version-date]-[variant]:[revision]
```

Examples:
- `anthropic.claude-sonnet-4-6` → Claude Sonnet 4.6 (latest)
- `anthropic.claude-opus-4-6-v1` → Claude Opus 4.6 v1
- `anthropic.claude-sonnet-4-5-20250929-v1:0` → Claude Sonnet 4.5 (Sept 29, 2025) v1 rev 0
