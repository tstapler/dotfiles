# Bedrock Tool Result Validation Fix

**Status**: ✅ Fixed (2026-04-16)
**Issue**: Orphaned `tool_result` blocks causing Bedrock ValidationException

---

## Root Cause Analysis

### The Problem

Claude Code's own conversation compaction removes old messages to save tokens, which can create orphaned `tool_result` blocks:

1. Claude Code compacts conversation → removes messages containing `tool_use` blocks
2. Later messages still reference those `tool_use_ids` in `tool_result` blocks
3. Claude Code sends these broken messages to the proxy
4. Bedrock rejects with: `ValidationException: unexpected tool_use_id found in tool_result blocks`

### Why Two Validation Layers

**Layer 1: Compaction Validation** (compactor.py:268-277)
- Runs after FusionEngine compression
- **Status**: ✅ Working correctly
- Logs showed: `Compression broke 2 tool_use/tool_result pair(s) — reverting to original messages`
- Successfully reverts when orphaned tool_results detected

**Layer 2: Provider Validation** (bedrock.py:615-651)
- Runs before sending to Bedrock
- **Status**: ⚠️ Had a bug (now fixed)
- Removes orphaned tool_results from messages
- **Bug**: Didn't remove tool_results missing the `tool_use_id` field entirely

---

## The Fix

### Before (Bug)

```python
# Only removed tool_results with orphaned IDs, but kept ones missing tool_use_id entirely
if tool_use_id and tool_use_id not in valid_tool_use_ids:
    logger.debug(f"Removing orphaned tool_result...")
    continue
cleaned_content.append(content_item)  # ❌ Kept tool_results without tool_use_id
```

**Problem**: Bedrock requires the `tool_use_id` field. Tool results without it would cause:
```
ValidationException: tool_use_id: Field required
```

### After (Fixed)

```python
# Remove tool_results that are EITHER missing tool_use_id OR have orphaned references
if not tool_use_id:
    logger.debug(f"Removing tool_result with missing tool_use_id field (required by Bedrock)")
    continue
if tool_use_id not in valid_tool_use_ids:
    logger.debug(f"Removing orphaned tool_result with tool_use_id={tool_use_id}")
    continue
cleaned_content.append(content_item)  # ✅ Only keeps valid tool_results
```

---

## Validation

### Integration Tests Added

`tests/integration/test_bedrock_api_spec.py`:

1. ✅ Valid tool_use/result pairs preserved
2. ✅ Orphaned tool_results removed (no matching tool_use)
3. ✅ Partial orphaned scenarios (some valid, some orphaned)
4. ✅ **Missing tool_use_id field removed** (new test)
5. ✅ Post-compaction validation
6. ✅ Beta feature handling
7. ✅ Field validation

**Result**: All 12 tests pass

### Service Status

```bash
make restart
# ✅ Zero-downtime reload successful
# ✅ Smoke test passed
# ✅ Proxy healthy
```

---

## Why Keep Provider Validation?

Even though compaction validation works, provider validation is still necessary because:

1. **Different contexts**: Compaction catches FusionEngine issues; provider catches upstream Claude Code issues
2. **Defense in depth**: Belt and suspenders approach prevents Bedrock rejections
3. **Different failure modes**: Compaction reverts (keeps everything); provider removes (surgical fix)
4. **Upstream issue**: The root cause is in Claude Code's compaction, which we can't control

---

## Logs to Monitor

After fix, these debug logs indicate the validation is working:

```
DEBUG - Removing tool_result with missing tool_use_id field (required by Bedrock)
DEBUG - Removing orphaned tool_result with tool_use_id=toolu_bdrk_01XXX (no matching tool_use found)
```

If you see these, it means Claude Code sent broken messages and the validation layer caught them.

---

## Related Files

- `providers/bedrock.py:615-651` - Provider validation logic
- `compactor.py:268-277` - Compaction validation logic
- `tests/integration/test_bedrock_api_spec.py` - Comprehensive integration tests

---

## Next Steps

✅ **Phase 1: Comprehensive tests** - Complete (12 tests pass)
✅ **Phase 2: Root cause investigation** - Complete (documented above)
✅ **Phase 3: Validation layer fix** - Complete (handles both cases)

### Remaining Work

- Task 12: Implement CLI query commands for error diagnostics
- Task 13: Add export functionality for error data
