# Troubleshooting and Common Patterns

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
