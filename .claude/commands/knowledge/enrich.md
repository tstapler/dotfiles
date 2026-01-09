# Knowledge Enrichment Orchestrator

**Single entry point** for processing all knowledge enrichment tags in journal entries across Tyler's personal wiki.

**Status**: Production-ready command

**Repository**: `~/Documents/personal-wiki` or `~/personal-wiki`

---

## Purpose

Discover and process enrichment tags (`[[Needs Research]]`, `[[Needs Synthesis]]`, `[[Needs Handy Plan]]`, `[[Book Recommendation]]`) from journal entries, delegating to specialized handlers.

**CRITICAL**: All handlers MUST include source attribution. Pages without sources will fail validation.

---

## Arguments

| Argument | Values | Default | Description |
|----------|--------|---------|-------------|
| `scope` | today, week, month, all | week | Time range to scan for tags |
| `--only` | all, processing, synthesis, research, handy-plan, book | all | Filter to specific tag type |
| `--validate` | - | false | Run source validation after processing |

**Note**: `processing` is the recommended unified tag. `research` and `synthesis` are kept for backward compatibility.

---

## Core Workflow

### Phase 1: Discovery

**Objective**: Scan journals and discover ALL enrichment tags within scope.

```xml
<instructions>
1. Determine repository location:
   - Check ~/Documents/personal-wiki first
   - Fallback to ~/personal-wiki
   - Error if neither exists

2. Calculate date range based on scope:
   - today: Current date only
   - week: Last 7 days
   - month: Last 30 days
   - all: Entire history

3. Search for all tags in parallel:
   ```bash
   grep -rn "\[\[Needs Processing\]\]" ~/Documents/personal-wiki/logseq/journals/
   grep -rn "\[\[Needs Synthesis\]\]" ~/Documents/personal-wiki/logseq/journals/
   grep -rn "\[\[Needs Research\]\]" ~/Documents/personal-wiki/logseq/journals/
   grep -rn "\[\[Needs Handy Plan\]\]" ~/Documents/personal-wiki/logseq/journals/
   grep -rn "\[\[Book Recommendation\]\]" ~/Documents/personal-wiki/logseq/journals/
   ```

4. Filter results:
   - Parse journal filenames (YYYY_MM_DD.md)
   - Include only dates within scope
   - Skip already-processed entries (~~[[Tag]]~~)
   - Skip section headers (## Title [[Tag]])
   - **CRITICAL**: Sort entries in REVERSE CHRONOLOGICAL order (newest first)

5. Apply --only filter if specified

6. Generate discovery report showing counts by tag type

**IMPORTANT**: All entries must be processed in REVERSE CHRONOLOGICAL order (newest journal dates first) to prioritize recent work over old journal entries. This ensures that recently captured knowledge is fleshed out before moving on to historical entries.
</instructions>
```

**Output**: List of entries to process, categorized by tag type

---

### Phase 2: Handler Dispatch

**Objective**: Process each tag type through its specialized handler.

**CRITICAL REQUIREMENT**: Handlers MUST be invoked using the Read tool to load handler instructions, then following those instructions directly. DO NOT duplicate handler logic.

**Processing Order** (by tag type):
1. **Book Recommendations** - Fastest, independent
2. **Handy Plans** - Self-contained
3. **Research** - May inform synthesis
4. **Synthesis** - Most comprehensive

**For Each Tag Type** with entries:

```xml
<instructions>
1. Read handler skill file:
   ```bash
   # Handler locations
   ~/.claude/skills/knowledge/handlers/processing-handler.md      # [[Needs Processing]] (RECOMMENDED)
   ~/.claude/skills/knowledge/handlers/research-handler.md        # [[Needs Research]] (legacy)
   ~/.claude/skills/knowledge/handlers/synthesis-handler.md       # [[Needs Synthesis]] (legacy)
   ~/.claude/skills/knowledge/handlers/handy-plan-handler.md
   ~/.claude/skills/knowledge/handlers/book-recommendation-handler.md
   ```

2. Process entries sequentially following handler methodology

3. Track results for each entry:
   ```yaml
   entry: "[preview]"
   tag_type: "[[Needs Research]]"
   status: "success|partial|failed"
   pages_created:
     - "[[Page Name]]"
   pages_updated: []
   issues: []
   sources_documented: int  # NEW: Track source count
   ```

4. Validate source attribution (see Phase 4)

5. Handle errors gracefully:
   - Log error details
   - Mark entry status appropriately
   - Continue with next entry
   - Accumulate failures for report
</instructions>
```

**Success Criteria** (per tag type):
- All entries processed
- Results tracked for each
- Sources documented for research/synthesis/handy-plan
- Errors logged but don't halt processing

---

### Phase 3: Tag Cleanup

**Objective**: Remove processed tags consistently across all entries.

**CRITICAL**: This phase is centralized to ensure consistent cleanup.

```xml
<instructions>
For each successfully processed entry:

1. Locate exact line in journal:
   - Use file path and line number from discovery
   - Re-read file to confirm content matches
   - Handle if file was modified during processing

2. Transform based on tag type:

   | Tag Type | Transformation Pattern |
   |----------|----------------------|
   | [[Needs Processing]] | `- Topic [[Needs Processing]]` → `- [[Topic]] ✓ Processed (Research/Synthesis/Hybrid) - N sources [[Processed YYYY-MM-DD]]` |
   | [[Needs Synthesis]] | `- Topic [[Needs Synthesis]]` → `- Synthesized [[Topic Page]] - see [[Knowledge Synthesis - YYYY-MM-DD]]` |
   | [[Needs Research]] | `- Research X [[Needs Research]]` → `- Researched [[X]] - comprehensive guide with N sources [[Researched YYYY-MM-DD]]` |
   | [[Needs Handy Plan]] | `- Fix X [[Needs Handy Plan]]` → `- Created plan for [[X Project]] (Difficulty: Medium, Time: X hrs) [[Planned YYYY-MM-DD]]` |
   | [[Book Recommendation]] | `- "Book" by Author [[Book Recommendation]]` → `- Added [[Book Title]] to library (Audiobook: Yes/No) [[Added YYYY-MM-DD]]` |

3. Cleanup rules (ALL types):
   - REMOVE the enrichment tag entirely
   - ADD wiki link to created page(s)
   - ADD completion date marker [[Tag YYYY-MM-DD]]
   - ADD metadata about result (source count, difficulty, audiobook status, etc.)
   - TRANSFORM verb tense to past
   - PRESERVE nested content below entry

4. Verify each edit:
   - Re-read line after edit
   - Confirm tag is removed
   - Confirm link is present
   - Log any failures
</instructions>
```

---

### Phase 4: Source Validation

**Objective**: Verify all research-based pages have proper source attribution.

**MANDATORY FOR**: `[[Needs Research]]`, `[[Needs Synthesis]]`, `[[Needs Handy Plan]]`

**NOT REQUIRED FOR**: `[[Book Recommendation]]` (uses book-sync system)

```xml
<validation>
For each page created during processing:

1. Read page content from logseq/pages/

2. Check for "## Sources" section:
   ```python
   has_sources_section = re.search(r'^##\s+Sources', page_content, re.MULTILINE)
   ```

3. Count documented sources:
   ```python
   # Match markdown links or numbered lists with URLs
   sources = re.findall(r'\[.+?\]\(.+?\)', page_content)
   source_count = len(sources)
   ```

4. Validation rules:
   - MINIMUM 2 sources required
   - Sources MUST be in "## Sources" section
   - Sources MUST be actual URLs (not placeholders)
   - Sources MUST use markdown link format: [Title](URL)

5. Validation failure actions:
   - Mark entry status as "failed"
   - DO NOT remove tag from journal
   - Log specific validation error
   - Include in issues list for report

6. Example valid sources section:
   ```markdown
   ## Sources

   1. [How to Date a Ball Jar — Minnetrista](https://www.minnetrista.net/blog/blog/2013/06/27/ball-family-history/how-to-date-a-ball-jar)
   2. [How to Date Old Ball Mason Jars - wikiHow](https://www.wikihow.com/Date-Old-Ball-Mason-Jars)
   3. [Ball Mason Jar Age Chart - Taste of Home](https://www.tasteofhome.com/article/ball-mason-jar-age-chart/)
   ```

7. Example INVALID (will fail validation):
   ```markdown
   ## Sources

   - [Source 1](url)
   - [Source 2](url)
   ```
   OR missing section entirely
</validation>
```

**Validation Report**:
```yaml
validation_results:
  total_pages: int
  passed: int
  failed: int
  failures:
    - page: "[[Page Name]]"
      issue: "No Sources section found"
    - page: "[[Page Name 2]]"
      issue: "Only 1 source documented, minimum 2 required"
```

---

### Phase 5: Completion Report

**Objective**: Generate comprehensive report with validation results.

```markdown
## Knowledge Enrichment Complete

**Processing Summary**:
- Scope: [scope] ([date range])
- Repository: [path]
- Total entries discovered: [count]
- Successfully processed: [count]
- Failed validation: [count]
- Partial success: [count]
- Failed: [count]

---

### [[Needs Synthesis]] Results
- Entries processed: [count]
- Topic pages created: [count]
  - [[Topic 1]] (N sources, X words)
  - [[Topic 2]] (N sources, X words)
- Validation: [X/Y passed]
- Issues: [list or "None"]

---

### [[Needs Research]] Results
- Entries processed: [count]
- Research pages created: [count]
  - [[Research Topic 1]] ([N sources](logseq/pages/Research Topic 1.md:75), X words)
  - [[Comparison: A vs B]] ([N sources](logseq/pages/Comparison A vs B.md:82), X words)
- Validation: [X/Y passed]
- Issues: [list or "None"]

---

### [[Needs Handy Plan]] Results
- Entries processed: [count]
- Project plans created: [count]
  - [[Project Plan 1]] (Difficulty: Medium, [N sources](logseq/pages/Project Plan 1.md:307), Cost: $X-Y)
  - [[Project Plan 2]] (Difficulty: Easy, [N sources](logseq/pages/Project Plan 2.md:312), Cost: $X-Y)
- Validation: [X/Y passed]
- Issues: [list or "None"]

---

### [[Book Recommendation]] Results
- Entries processed: [count]
- Books added to library: [count]
  - [[Book Title 1]] by Author (Audiobook: Yes, Enriched: OpenLibrary + Audible)
  - [[Book Title 2]] by Author (Audiobook: No, Enriched: OpenLibrary only)
- Already in library: [count]
- Validation: Not required (book-sync system)
- Issues: [list or "None"]

---

### Verification Status
- ✅/❌ Tags removed: [status]
- ✅/❌ Pages created: [status]
- ✅/❌ Sources validated: [X/Y pages passed]
- ✅/❌ Links validated: [status]
- ✅/❌ No broken references: [status]

### Pages Requiring Manual Review
[List any entries that failed validation with specific issues]

**Example**:
- [[Dating Ball Glass Jars]] - MISSING SOURCES SECTION
  - Issue: No "## Sources" section found
  - Action: Add sources used during research
  - Research tools used: mcp__brave-search__brave_web_search, mcp__read-website-fast__read_website
  - Entry location: logseq/journals/2026_01_09.md:15

### Recommended Follow-Up
- Run `/knowledge/validate-links` to verify knowledge graph health
- Run `uv run book-sync enrich run` to enhance book metadata
- Review entries marked for clarification
- Fix pages with missing sources (listed above)
</markdown>
```

---

## Error Handling

### Individual Entry Failures
- Log error details with context
- Mark entry as failed
- Continue with remaining entries
- Include in final report with file:line reference

### Handler Invocation Failures
- Log which handler failed and why
- Skip entries for that tag type
- Report which tag types were skipped
- Suggest manual processing

### Validation Failures
- DO NOT mark entry as complete
- DO NOT remove tag from journal
- Log specific validation issue
- Include page path and line number for manual fix

### Multiple Consecutive Failures
- Pause after 5 consecutive failures
- Report current progress
- Suggest troubleshooting:
  - Check handler files exist
  - Verify web search tools accessible
  - Check file permissions
- Allow user to continue or abort

---

## Usage Examples

### Default (Process All, Last Week)
```bash
/knowledge/enrich
```

### Scope-Based
```bash
/knowledge/enrich today
/knowledge/enrich month
/knowledge/enrich all
```

### Filtered by Tag Type
```bash
/knowledge/enrich week --only research
/knowledge/enrich today --only synthesis
/knowledge/enrich --only book
```

### With Validation
```bash
/knowledge/enrich week --validate
```

---

## Repository Location

The command automatically locates Tyler's personal wiki:

```python
def find_wiki_repo() -> Path:
    """Find personal wiki repository."""
    candidates = [
        Path.home() / "Documents" / "personal-wiki",
        Path.home() / "personal-wiki"
    ]

    for path in candidates:
        if path.exists() and (path / "logseq").exists():
            return path

    raise FileNotFoundError(
        "Personal wiki not found. Expected at:\n"
        "  ~/Documents/personal-wiki\n"
        "  ~/personal-wiki"
    )
```

---

## Quality Standards

### Discovery Quality
- All tags found within scope
- No false positives (headers filtered)
- Proper date range filtering
- Accurate counts

### Processing Quality
- Handlers actually invoked (not duplicated)
- Each handler applies domain standards
- Results tracked per entry
- Errors don't cascade

### Validation Quality
- **ALL research pages have ≥2 sources**
- Sources are real URLs, not placeholders
- Validation failures prevent tag removal
- Clear error messages with file locations

### Cleanup Quality
- Tags removed ONLY after validation passes
- Consistent transformation format
- Wiki links validated
- No content corruption

### Reporting Quality
- All metrics accurate
- Source counts visible (with line numbers)
- Clear breakdown by tag type
- Actionable next steps with file paths
- Any issues clearly documented with locations

---

## Integration with Handler Skills

Handler skill locations:
```
~/.claude/skills/knowledge/handlers/
├── processing-handler.md     # [[Needs Processing]] (RECOMMENDED - auto-detects approach)
├── synthesis-handler.md      # [[Needs Synthesis]] (legacy - explicit synthesis)
├── research-handler.md       # [[Needs Research]] (legacy - explicit research)
├── handy-plan-handler.md     # [[Needs Handy Plan]]
└── book-recommendation-handler.md  # [[Book Recommendation]]
```

**Unified Processing** (`processing-handler.md`):
- Automatically detects context richness
- Chooses optimal approach: research, synthesis, or hybrid
- Reduces cognitive load - just tag with `[[Needs Processing]]`
- Produces same high-quality, well-sourced pages

**Handler Contract**:
Each handler receives:
- Entry content and context
- Journal date and line number
- Repository path

Each handler returns:
- Processing status
- Pages created/updated
- Source count (research/synthesis/handy-plan)
- Any issues encountered

The orchestrator handles:
- Discovery across all tags
- Handler invocation (by reading skill files)
- Source validation
- Tag cleanup
- Progress reporting
- Error accumulation

---

## Source Attribution Examples

### Good Example (Research)
```markdown
# Dating Ball Glass Jars

[... content ...]

## Sources

1. [How to Date a Ball Jar — Minnetrista](https://www.minnetrista.net/blog/blog/2013/06/27/ball-family-history/how-to-date-a-ball-jar)
2. [How to Date Old Ball Mason Jars - wikiHow](https://www.wikihow.com/Date-Old-Ball-Mason-Jars)
3. [Ball Mason Jar Age Chart - Taste of Home](https://www.tasteofhome.com/article/ball-mason-jar-age-chart/)
```
✅ **PASSES**: 3 sources with real URLs in proper format

### Bad Example (Will Fail Validation)
```markdown
# Dating Ball Glass Jars

[... content ...]

## Resources
- [[Midwest Antique Fruit Jar and Bottle Club]]
```
❌ **FAILS**: Wrong section name, no URLs, only 1 source

---

## Retroactive Validation

To audit existing pages for missing sources:

```bash
# Run validation on all existing research pages
/knowledge/enrich all --only research --validate
```

This will scan ALL research pages and report any missing source sections.