---
description: ''
prompt: "# Migration Guide: Unified [[Needs Processing]] Tag\n\n## Overview\n\nThis\
  \ guide explains the new unified `[[Needs Processing]]` tag and how to migrate from\
  \ the old separate tags.\n\n**TL;DR**: Just use `[[Needs Processing]]` for everything.\
  \ The system will figure out whether it needs research, synthesis, or both.\n\n\
  ---\n\n## What Changed?\n\n### Old System (Still Works!)\n```markdown\n[[Needs Research]]\
  \    # For discovering new information\n[[Needs Synthesis]]   # For processing consumed\
  \ content\n```\n\n**Problem**: You had to decide upfront which approach to use.\n\
  \n### New System (Recommended)\n```markdown\n[[Needs Processing]]  # System auto-detects\
  \ best approach\n```\n\n**Solution**: The system analyzes your entry and chooses\
  \ the optimal strategy automatically.\n\n---\n\n## How It Works\n\nThe `processing-handler`\
  \ analyzes your entry for **context indicators**:\n\n| Indicator | Example | Weight\
  \ |\n|-----------|---------|--------|\n| URLs | `https://example.com` | 0.3 |\n\
  | Quotes | `\"key insight here\"` | 0.2 |\n| Detailed notes | >30 words | 0.3 |\n\
  | Consumption verbs | \"reading\", \"watched\", \"discussed\" | 0.2 |\n\n**Context\
  \ Score → Approach**:\n- **0.0-0.3** (Low) → **Research**: Discover from scratch\n\
  - **0.3-0.6** (Medium) → **Hybrid**: Research + expand context\n- **0.6-1.0** (High)\
  \ → **Synthesis**: Focus on expanding provided content\n\n---\n\n## Migration Strategies\n\
  \n### Strategy 1: Gradual (Recommended)\n\n**No forced migration required.** Start\
  \ using `[[Needs Processing]]` for new entries:\n\n```markdown\n# Old entries -\
  \ keep as-is\n- [[Dating Ball Glass Jars]] [[Needs Research]]\n- Reading [[Unix\
  \ Philosophy]] https://... [[Needs Synthesis]]\n\n# New entries - use unified tag\n\
  - [[PostgreSQL MVCC]] [[Needs Processing]]\n- Reading [[Docker Volumes]] https://...\
  \ [[Needs Processing]]\n```\n\nBoth will work! The enrichment command supports all\
  \ tags.\n\n---\n\n### Strategy 2: Immediate Switch\n\nStart using `[[Needs Processing]]`\
  \ today:\n\n**Before**:\n```markdown\n# Had to think: \"Is this research or synthesis?\"\
  \n- [[Topic X]] [[Needs ???]]  # Which one?\n```\n\n**After**:\n```markdown\n# Just\
  \ tag it, system decides\n- [[Topic X]] [[Needs Processing]]  # Done!\n```\n\n---\n\
  \n### Strategy 3: Bulk Migration (Optional)\n\nIf you want to migrate existing tags,\
  \ you can do it manually or with search/replace:\n\n#### Find Old Tags\n```bash\n\
  # Search for unmigrated entries\ngrep -rn \"\\[\\[Needs Research\\]\\]\" ~/Documents/personal-wiki/logseq/journals/\n\
  grep -rn \"\\[\\[Needs Synthesis\\]\\]\" ~/Documents/personal-wiki/logseq/journals/\n\
  ```\n\n#### Replace (Optional)\nYou can keep old tags or replace them:\n\n```bash\n\
  # Old → New (entirely optional!)\n[[Needs Research]] → [[Needs Processing]]\n[[Needs\
  \ Synthesis]] → [[Needs Processing]]\n```\n\n**Note**: This is NOT required. Old\
  \ tags continue to work perfectly.\n\n---\n\n## Example Conversions\n\n### Example\
  \ 1: Pure Research\n**Old**:\n```markdown\n- [[Dating Ball Glass Jars]] [[Needs\
  \ Research]]\n```\n\n**New**:\n```markdown\n- [[Dating Ball Glass Jars]] [[Needs\
  \ Processing]]\n```\n\n**What Happens**:\n- Context score: 0.0 (no URLs, quotes,\
  \ or notes)\n- Approach chosen: Research\n- Output: Reference page with 3-5 sources\n\
  - Journal update: `✓ Processed (Research) - 5 sources`\n\n---\n\n### Example 2:\
  \ Rich Synthesis\n**Old**:\n```markdown\n- Reading about [[Unix Philosophy]] https://homepage.cs.uri.edu/...\n\
  \nKey insight: \"Do one thing well\"\n\nConnects to [[Microservices]] and [[Single\
  \ Responsibility]]\n\n[[Needs Synthesis]]\n```\n\n**New**:\n```markdown\n- Reading\
  \ about [[Unix Philosophy]] https://homepage.cs.uri.edu/...\n\nKey insight: \"Do\
  \ one thing well\"\n\nConnects to [[Microservices]] and [[Single Responsibility]]\n\
  \n[[Needs Processing]]\n```\n\n**What Happens**:\n- Context score: 1.0 (URL + quote\
  \ + notes + \"reading\")\n- Approach chosen: Synthesis\n- Output: Zettelkasten note\
  \ with connections\n- Journal update: `✓ Processed (Synthesis) - expanded from content,\
  \ 3 sources`\n\n---\n\n### Example 3: Hybrid\n**Old** (would have been ambiguous):\n\
  ```markdown\n- [[PostgreSQL MVCC]] https://wiki.postgresql.org/wiki/MVCC [[Needs\
  \ ???]]\n```\n\n**New**:\n```markdown\n- [[PostgreSQL MVCC]] https://wiki.postgresql.org/wiki/MVCC\
  \ [[Needs Processing]]\n```\n\n**What Happens**:\n- Context score: 0.3 (URL but\
  \ no quotes/notes)\n- Approach chosen: Hybrid\n- Output: Comprehensive guide (URL\
  \ + research)\n- Journal update: `✓ Processed (Hybrid) - comprehensive guide, 4\
  \ sources`\n\n---\n\n## When to Use Old Tags\n\nYou might want to explicitly use\
  \ old tags if:\n\n1. **Force Research**: You want pure research even with context\n\
  \   ```markdown\n   - Reading [[Topic]] https://url [[Needs Research]]\n   # Forces\
  \ research approach despite URL\n   ```\n\n2. **Force Synthesis**: You want synthesis-only,\
  \ no extra research\n   ```markdown\n   - [[Topic]] [[Needs Synthesis]]\n   # Forces\
  \ synthesis approach only\n   ```\n\n3. **Explicit Control**: You have a specific\
  \ workflow preference\n\n**But most users should just use `[[Needs Processing]]`\
  \ and let the system decide.**\n\n---\n\n## Command Usage\n\n### Process New Unified\
  \ Tags\n```bash\n# Process only [[Needs Processing]] tags\n/knowledge/enrich --only\
  \ processing\n\n# Process all tags (including unified)\n/knowledge/enrich\n```\n\
  \n### Process Old Tags\n```bash\n# Process only old-style research tags\n/knowledge/enrich\
  \ --only research\n\n# Process only old-style synthesis tags\n/knowledge/enrich\
  \ --only synthesis\n```\n\n### Process Everything\n```bash\n# Process all tag types\
  \ at once\n/knowledge/enrich week\n```\n\n---\n\n## Backward Compatibility\n\n**100%\
  \ backward compatible.** All old tags continue to work:\n\n| Tag | Handler | Status\
  \ |\n|-----|---------|--------|\n| `[[Needs Processing]]` | processing-handler.md\
  \ | ✅ Recommended |\n| `[[Needs Research]]` | research-handler.md | ✅ Supported\
  \ (legacy) |\n| `[[Needs Synthesis]]` | synthesis-handler.md | ✅ Supported (legacy)\
  \ |\n| `[[Needs Handy Plan]]` | handy-plan-handler.md | ✅ Active |\n| `[[Book Recommendation]]`\
  \ | book-recommendation-handler.md | ✅ Active |\n\n---\n\n## FAQ\n\n### Q: Do I\
  \ have to migrate?\n**A: No.** Old tags work forever. Migrate when convenient.\n\
  \n### Q: What if the system chooses wrong?\n**A: Use explicit tags.** If `[[Needs\
  \ Processing]]` chooses research but you wanted synthesis, just use `[[Needs Synthesis]]`\
  \ explicitly.\n\n### Q: Can I mix tags?\n**A: Yes.** Use `[[Needs Processing]]`\
  \ for new entries, keep old tags on historical entries.\n\n### Q: Will my existing\
  \ processed entries break?\n**A: No.** This only affects unprocessed tags. Already-processed\
  \ entries are unchanged.\n\n### Q: Do I get the same quality with unified tag?\n\
  **A: Yes.** All approaches require ≥2 sources and validation. Quality is identical.\n\
  \n### Q: Can I see which approach was chosen?\n**A: Yes.** The journal update shows:\
  \ `✓ Processed (Research/Synthesis/Hybrid)`.\n\n---\n\n## Migration Checklist\n\n\
  - [ ] Read this guide\n- [ ] Understand context detection\n- [ ] Try `[[Needs Processing]]`\
  \ on a test entry\n- [ ] Run `/knowledge/enrich --only processing`\n- [ ] Review\
  \ generated page quality\n- [ ] Decide: keep old tags or adopt new tag\n- [ ] Update\
  \ personal workflow (optional)\n- [ ] Optionally bulk-replace old tags (not required)\n\
  \n---\n\n## Recommended Workflow\n\n**Going Forward**:\n1. When capturing knowledge,\
  \ just tag with `[[Needs Processing]]`\n2. Don't think about whether it's \"research\"\
  \ or \"synthesis\"\n3. Let the system analyze and choose\n4. Review the result and\
  \ see which approach was used\n5. If wrong, provide feedback or use explicit tag\
  \ next time\n\n**Simple Rule**: When in doubt, use `[[Needs Processing]]`. ✅\n\n\
  ---\n\n## Support\n\n- **Handler location**: `~/.claude/skills/knowledge/handlers/processing-handler.md`\n\
  - **Command location**: `~/.claude/commands/knowledge/enrich.md`\n- **Old handlers**:\
  \ Still available in same directory (research-handler.md, synthesis-handler.md)\n\
  \n---\n\n## Summary\n\n**Old Way**:\n- Choose between `[[Needs Research]]` or `[[Needs\
  \ Synthesis]]`\n- Cognitive overhead deciding which\n- Sometimes wrong choice\n\n\
  **New Way** (Recommended):\n- Just use `[[Needs Processing]]`\n- System analyzes\
  \ context automatically\n- Chooses optimal approach: research, synthesis, or hybrid\n\
  - Same high quality, less thinking\n\n**Migration**: Not required. Start using when\
  \ ready. Both systems coexist perfectly.\n"
---

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
