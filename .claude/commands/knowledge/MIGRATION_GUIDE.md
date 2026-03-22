# Migration Guide: Unified [[Needs Processing]] Tag

## Overview

This guide explains the new unified `[[Needs Processing]]` tag and how to migrate from the old separate tags.

**TL;DR**: Just use `[[Needs Processing]]` for everything. The system will figure out whether it needs research, synthesis, or both.

---

## What Changed?

### Old System (Still Works!)
```markdown
[[Needs Research]]    # For discovering new information
[[Needs Synthesis]]   # For processing consumed content
```

**Problem**: You had to decide upfront which approach to use.

### New System (Recommended)
```markdown
[[Needs Processing]]  # System auto-detects best approach
```

**Solution**: The system analyzes your entry and chooses the optimal strategy automatically.

---

## How It Works

The `processing-handler` analyzes your entry for **context indicators**:

| Indicator | Example | Weight |
|-----------|---------|--------|
| URLs | `https://example.com` | 0.3 |
| Quotes | `"key insight here"` | 0.2 |
| Detailed notes | >30 words | 0.3 |
| Consumption verbs | "reading", "watched", "discussed" | 0.2 |

**Context Score → Approach**:
- **0.0-0.3** (Low) → **Research**: Discover from scratch
- **0.3-0.6** (Medium) → **Hybrid**: Research + expand context
- **0.6-1.0** (High) → **Synthesis**: Focus on expanding provided content

---

## Migration Strategies

### Strategy 1: Gradual (Recommended)

**No forced migration required.** Start using `[[Needs Processing]]` for new entries:

```markdown
# Old entries - keep as-is
- [[Dating Ball Glass Jars]] [[Needs Research]]
- Reading [[Unix Philosophy]] https://... [[Needs Synthesis]]

# New entries - use unified tag
- [[PostgreSQL MVCC]] [[Needs Processing]]
- Reading [[Docker Volumes]] https://... [[Needs Processing]]
```

Both will work! The enrichment command supports all tags.

---

### Strategy 2: Immediate Switch

Start using `[[Needs Processing]]` today:

**Before**:
```markdown
# Had to think: "Is this research or synthesis?"
- [[Topic X]] [[Needs ???]]  # Which one?
```

**After**:
```markdown
# Just tag it, system decides
- [[Topic X]] [[Needs Processing]]  # Done!
```

---

### Strategy 3: Bulk Migration (Optional)

If you want to migrate existing tags, you can do it manually or with search/replace:

#### Find Old Tags
```bash
# Search for unmigrated entries
grep -rn "\[\[Needs Research\]\]" ~/Documents/personal-wiki/logseq/journals/
grep -rn "\[\[Needs Synthesis\]\]" ~/Documents/personal-wiki/logseq/journals/
```

#### Replace (Optional)
You can keep old tags or replace them:

```bash
# Old → New (entirely optional!)
[[Needs Research]] → [[Needs Processing]]
[[Needs Synthesis]] → [[Needs Processing]]
```

**Note**: This is NOT required. Old tags continue to work perfectly.

---

## Example Conversions

### Example 1: Pure Research
**Old**:
```markdown
- [[Dating Ball Glass Jars]] [[Needs Research]]
```

**New**:
```markdown
- [[Dating Ball Glass Jars]] [[Needs Processing]]
```

**What Happens**:
- Context score: 0.0 (no URLs, quotes, or notes)
- Approach chosen: Research
- Output: Reference page with 3-5 sources
- Journal update: `✓ Processed (Research) - 5 sources`

---

### Example 2: Rich Synthesis
**Old**:
```markdown
- Reading about [[Unix Philosophy]] https://homepage.cs.uri.edu/...

Key insight: "Do one thing well"

Connects to [[Microservices]] and [[Single Responsibility]]

[[Needs Synthesis]]
```

**New**:
```markdown
- Reading about [[Unix Philosophy]] https://homepage.cs.uri.edu/...

Key insight: "Do one thing well"

Connects to [[Microservices]] and [[Single Responsibility]]

[[Needs Processing]]
```

**What Happens**:
- Context score: 1.0 (URL + quote + notes + "reading")
- Approach chosen: Synthesis
- Output: Zettelkasten note with connections
- Journal update: `✓ Processed (Synthesis) - expanded from content, 3 sources`

---

### Example 3: Hybrid
**Old** (would have been ambiguous):
```markdown
- [[PostgreSQL MVCC]] https://wiki.postgresql.org/wiki/MVCC [[Needs ???]]
```

**New**:
```markdown
- [[PostgreSQL MVCC]] https://wiki.postgresql.org/wiki/MVCC [[Needs Processing]]
```

**What Happens**:
- Context score: 0.3 (URL but no quotes/notes)
- Approach chosen: Hybrid
- Output: Comprehensive guide (URL + research)
- Journal update: `✓ Processed (Hybrid) - comprehensive guide, 4 sources`

---

## When to Use Old Tags

You might want to explicitly use old tags if:

1. **Force Research**: You want pure research even with context
   ```markdown
   - Reading [[Topic]] https://url [[Needs Research]]
   # Forces research approach despite URL
   ```

2. **Force Synthesis**: You want synthesis-only, no extra research
   ```markdown
   - [[Topic]] [[Needs Synthesis]]
   # Forces synthesis approach only
   ```

3. **Explicit Control**: You have a specific workflow preference

**But most users should just use `[[Needs Processing]]` and let the system decide.**

---

## Command Usage

### Process New Unified Tags
```bash
# Process only [[Needs Processing]] tags
/knowledge/enrich --only processing

# Process all tags (including unified)
/knowledge/enrich
```

### Process Old Tags
```bash
# Process only old-style research tags
/knowledge/enrich --only research

# Process only old-style synthesis tags
/knowledge/enrich --only synthesis
```

### Process Everything
```bash
# Process all tag types at once
/knowledge/enrich week
```

---

## Backward Compatibility

**100% backward compatible.** All old tags continue to work:

| Tag | Handler | Status |
|-----|---------|--------|
| `[[Needs Processing]]` | processing-handler.md | ✅ Recommended |
| `[[Needs Research]]` | research-handler.md | ✅ Supported (legacy) |
| `[[Needs Synthesis]]` | synthesis-handler.md | ✅ Supported (legacy) |
| `[[Needs Handy Plan]]` | handy-plan-handler.md | ✅ Active |
| `[[Book Recommendation]]` | book-recommendation-handler.md | ✅ Active |

---

## FAQ

### Q: Do I have to migrate?
**A: No.** Old tags work forever. Migrate when convenient.

### Q: What if the system chooses wrong?
**A: Use explicit tags.** If `[[Needs Processing]]` chooses research but you wanted synthesis, just use `[[Needs Synthesis]]` explicitly.

### Q: Can I mix tags?
**A: Yes.** Use `[[Needs Processing]]` for new entries, keep old tags on historical entries.

### Q: Will my existing processed entries break?
**A: No.** This only affects unprocessed tags. Already-processed entries are unchanged.

### Q: Do I get the same quality with unified tag?
**A: Yes.** All approaches require ≥2 sources and validation. Quality is identical.

### Q: Can I see which approach was chosen?
**A: Yes.** The journal update shows: `✓ Processed (Research/Synthesis/Hybrid)`.

---

## Migration Checklist

- [ ] Read this guide
- [ ] Understand context detection
- [ ] Try `[[Needs Processing]]` on a test entry
- [ ] Run `/knowledge/enrich --only processing`
- [ ] Review generated page quality
- [ ] Decide: keep old tags or adopt new tag
- [ ] Update personal workflow (optional)
- [ ] Optionally bulk-replace old tags (not required)

---

## Recommended Workflow

**Going Forward**:
1. When capturing knowledge, just tag with `[[Needs Processing]]`
2. Don't think about whether it's "research" or "synthesis"
3. Let the system analyze and choose
4. Review the result and see which approach was used
5. If wrong, provide feedback or use explicit tag next time

**Simple Rule**: When in doubt, use `[[Needs Processing]]`. ✅

---

## Support

- **Handler location**: `~/.claude/skills/knowledge/handlers/processing-handler.md`
- **Command location**: `~/.claude/commands/knowledge/enrich.md`
- **Old handlers**: Still available in same directory (research-handler.md, synthesis-handler.md)

---

## Summary

**Old Way**:
- Choose between `[[Needs Research]]` or `[[Needs Synthesis]]`
- Cognitive overhead deciding which
- Sometimes wrong choice

**New Way** (Recommended):
- Just use `[[Needs Processing]]`
- System analyzes context automatically
- Chooses optimal approach: research, synthesis, or hybrid
- Same high quality, less thinking

**Migration**: Not required. Start using when ready. Both systems coexist perfectly.