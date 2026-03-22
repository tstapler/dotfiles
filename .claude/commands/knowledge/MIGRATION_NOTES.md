# Knowledge Processing Architecture Migration Notes

## Migration from: One Command Per Tag
## Migration to: Single Orchestrator + Handler Skills

**Migration Date**: 2026-01-07

---

## Summary of Changes

### Before (Legacy Architecture)
```
.claude/commands/knowledge/
├── process-needs-synthesis.md      # Full command
├── process-needs-research.md       # Full command
├── process-needs-handy-plan.md     # Full command
└── process-book-recommendations.md # Full command
```

Each command was:
- Independently invocable
- Self-contained (discovery, processing, cleanup, reporting)
- No shared logic between commands
- Separate progress reporting

### After (New Architecture)
```
.claude/commands/knowledge/
└── enrich.md                       # Single orchestrator command

.claude/skills/knowledge/handlers/
├── synthesis-handler.md            # Domain-specific processing
├── research-handler.md             # Domain-specific processing
├── handy-plan-handler.md           # Domain-specific processing
└── book-recommendation-handler.md  # Domain-specific processing
```

The new architecture provides:
- Single entry point for all tag processing
- Shared discovery, cleanup, and reporting logic
- Specialized handlers for domain-specific processing
- Consistent behavior across all tag types

---

## Command Mapping

| Old Command | New Command |
|-------------|-------------|
| `/knowledge/process-needs-synthesis` | `/knowledge/enrich --only synthesis` |
| `/knowledge/process-needs-research` | `/knowledge/enrich --only research` |
| `/knowledge/process-needs-handy-plan` | `/knowledge/enrich --only handy-plan` |
| `/knowledge/process-book-recommendations` | `/knowledge/enrich --only book` |
| (all four sequentially) | `/knowledge/enrich` |

---

## Migration Steps

### Immediate Actions (Already Complete)

1. **Created orchestrator command**: `/knowledge/enrich.md`
2. **Created handler skills**: Four handler files in `.claude/skills/knowledge/handlers/`
3. **Updated architecture documentation**: `KNOWLEDGE_PROCESSING_ARCHITECTURE.md`
4. **Legacy commands preserved**: Old commands still work for backward compatibility

### User Actions Required

**None required** - the migration is backward compatible. Both old and new commands work.

### Recommended Transition

1. **Start using `/knowledge/enrich`** for new processing
2. **Keep legacy commands available** during transition period
3. **After 30 days of successful usage**, consider deprecating legacy commands
4. **Update any scripts or aliases** that reference old commands

---

## Behavior Differences

### Discovery Phase
- **Before**: Each command scanned only for its specific tag
- **After**: Orchestrator scans for ALL tags in one pass

### Tag Cleanup
- **Before**: Each command had slightly different transformation patterns
- **After**: Consistent transformation format across all tag types

### Error Handling
- **Before**: Errors in one command didn't affect others
- **After**: Errors are accumulated, processing continues, unified error report

### Reporting
- **Before**: Each command produced its own report
- **After**: Single comprehensive report covering all processed tags

---

## Files Created

### New Files
```
.claude/commands/knowledge/enrich.md
.claude/skills/knowledge/handlers/synthesis-handler.md
.claude/skills/knowledge/handlers/research-handler.md
.claude/skills/knowledge/handlers/handy-plan-handler.md
.claude/skills/knowledge/handlers/book-recommendation-handler.md
.claude/commands/knowledge/MIGRATION_NOTES.md  (this file)
```

### Updated Files
```
.claude/commands/knowledge/KNOWLEDGE_PROCESSING_ARCHITECTURE.md
```

### Unchanged Files (Legacy Commands)
```
.claude/commands/knowledge/process-needs-synthesis.md
.claude/commands/knowledge/process-needs-research.md
.claude/commands/knowledge/process-needs-handy-plan.md
.claude/commands/knowledge/process-book-recommendations.md
```

---

## Rollback Plan

If issues are encountered with the new architecture:

1. **Continue using legacy commands** - they still work
2. **Report issues** for fixing
3. **Legacy commands will remain** until new architecture is proven

No data migration is required - both architectures work with the same:
- Journal entries and tags
- Wiki page structure
- Book-sync storage format

---

## Future Deprecation Timeline

| Date | Action |
|------|--------|
| 2026-01-07 | New architecture deployed |
| 2026-02-07 | Evaluate usage patterns |
| 2026-03-07 | Add deprecation notices to legacy commands |
| 2026-04-07 | Consider removal of legacy commands |

---

## FAQ

### Can I still use the old commands?
**Yes.** Legacy commands are preserved and functional. Use them if you prefer or encounter issues with the new orchestrator.

### Do I need to change my workflows?
**No.** Existing workflows using legacy commands continue to work. Transition to `/knowledge/enrich` at your convenience.

### What if I have custom scripts calling old commands?
**They still work.** Update scripts at your convenience. The old commands remain available.

### How do I process just one tag type with the new system?
Use the `--only` filter:
```bash
/knowledge/enrich --only synthesis
/knowledge/enrich --only research
/knowledge/enrich --only handy-plan
/knowledge/enrich --only book
```

### What about the `/knowledge/maintain` command?
It remains unchanged and can be updated to use `/knowledge/enrich` internally if desired.

---

## Technical Notes

### Handler Skill Loading
Handler skills are read by the orchestrator and applied to entries. They are NOT directly invocable commands - they provide domain knowledge that the orchestrator uses.

### Handler Contract
Each handler receives:
- Entry content and context
- Journal date and line number
- Priority assessment

Each handler returns:
- Processing status
- Pages created/updated
- Issues encountered

### Orchestrator Responsibilities
- Tag discovery across all types
- Handler invocation for processing
- Consistent tag cleanup
- Unified progress reporting
- Error accumulation and reporting

---

## Questions or Issues?

If you encounter problems with the migration:

1. **Use legacy commands** as a fallback
2. **Document the issue** with specific error messages
3. **Check handler skills** for missing or incorrect logic
4. **Verify file paths** in handlers match your system
