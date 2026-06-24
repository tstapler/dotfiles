---
description: ''
prompt: "# Expand Missing Topics Command\n\nSystematically discover and create comprehensive\
  \ zettels for topics referenced but not documented in your knowledge graph.\n\n\
  ## Arguments\n\n- `$1` (optional): **scope** - What to scan for missing topics\n\
  \  - `today` (default): Today's synthesis file only\n  - `week`: Last 7 days of\
  \ synthesis files\n  - `all`: All synthesis files\n  - `file:<path>`: Specific file\
  \ path\n\n- `$2` (optional): **max_topics** - Maximum topics to expand (default:\
  \ 5, max: 20)\n\n- `$3` (optional): **min_priority** - Minimum priority level (default:\
  \ medium)\n  - `high`: Only 3+ references or importance tags\n  - `medium`: 2+ references\
  \ or special context\n  - `low`: All missing topics\n\n- Flags:\n  - `--detect-unlinked`:\
  \ Enable unlinked concept detection\n  - `--comprehensive`: Use both wiki links\
  \ and unlinked concept detection\n\n## Examples\n\n```bash\n# Default: Today's synthesis,\
  \ 5 topics, medium+ priority\n/knowledge:expand-missing-topics\n\n# Weekly expansion,\
  \ 10 topics\n/knowledge:expand-missing-topics week 10\n\n# All high-priority topics\n\
  /knowledge:expand-missing-topics all 20 high\n\n# Comprehensive discovery (both\
  \ methods)\n/knowledge:expand-missing-topics week --comprehensive\n```\n\n## What\
  \ This Does\n\nThis command orchestrates a 4-phase workflow to close gaps in your\
  \ knowledge graph:\n\n**Phase 1: Discovery** - Identifies missing topics by extracting\
  \ `[[Wiki Links]]` from synthesis files and checking if pages exist and are comprehensive\
  \ (500+ words).\n\n**Phase 2: Prioritization** - Ranks topics by reference count,\
  \ context, and importance tags. Filters by priority threshold and selects top N.\n\
  \n**Phase 3: Expansion** - Creates comprehensive zettels for selected topics by\
  \ delegating to `/knowledge:synthesize-knowledge` with gathered context.\n\n**Phase\
  \ 4: Verification** - Validates quality (word counts, sections, sources) and generates\
  \ comprehensive before/after report.\n\n---\n\n@task knowledge-synthesis\n\n# Task:\
  \ Expand Missing Topics in Knowledge Graph\n\nExecute the 4-phase workflow to discover\
  \ and create comprehensive zettels for missing topics referenced in synthesis files.\n\
  \n## Configuration\n\n**Arguments Provided**:\n- Scope: $1 (default: \"today\")\n\
  - Max Topics: $2 (default: 5)\n- Min Priority: $3 (default: \"medium\")\n- Flags:\
  \ $* (check for --detect-unlinked, --comprehensive)\n\n**Repository Path**: `/Users/tylerstapler/Documents/personal-wiki`\n\
  \n**Key Directories**:\n- Synthesis files: `logseq/pages/Knowledge Synthesis - *.md`\n\
  - Topic pages: `logseq/pages/*.md`\n- Journals: `logseq/journals/YYYY_MM_DD.md`\n\
  \n---\n\n## Phase 1: Discovery\n\n### Step 1: Run Comprehensive Analysis\n\n**First,\
  \ get wiki-wide analysis** using the new analysis tools:\n\n```bash\ncd /Users/tylerstapler/Documents/personal-wiki\n\
  uv run logseq-analyze dashboard logseq/\n```\n\nThis provides:\n- Complete list\
  \ of stub pages (< 500 words)\n- Orphaned and poorly connected pages\n- Quality\
  \ scores for all pages\n- Priority rankings based on multiple factors\n\nParse the\
  \ dashboard output to extract:\n- Pages marked as STUB or INCOMPLETE\n- Priority\
  \ scores for each page\n- Connection counts and quality metrics\n\n### Step 2: Determine\
  \ Scan Scope\n\nBased on scope argument:\n\n**If \"today\"**:\n- File: `logseq/pages/Knowledge\
  \ Synthesis - {TODAY}.md`\n- Where {TODAY} = current date in format `YYYY-MM-DD`\n\
  \n**If \"week\"**:\n- Files: `Knowledge Synthesis - *.md` for last 7 days\n- Include\
  \ topic zettels linked from these daily hubs\n\n**If \"all\"**:\n- Pattern: `logseq/pages/Knowledge\
  \ Synthesis - *.md`\n- All synthesis files\n\n**If \"file:<path>\"**:\n- Single\
  \ file at provided path\n- Extract path from argument\n\n### Step 3: Extract Wiki\
  \ Links\n\nFor each file in scope:\n\n1. Use Read tool to get file contents\n2.\
  \ Extract all `[[Wiki Links]]` and `#[[Tag Links]]` using regex pattern: `(?:#?\\\
  [\\[([^\\]]+)\\]\\])`\n3. Normalize: Trim whitespace, preserve capitalization\n\
  4. Build unique set of referenced topics\n\n### Step 4: Enhance with Analysis Data\n\
  \n**Merge traditional discovery with analysis insights**:\n\nFor each extracted\
  \ link:\n\n1. Convert to expected filename:\n   - Link: `[[Topic Name]]`\n   - File:\
  \ `logseq/pages/Topic Name.md`\n\n2. Check analysis results for this page:\n   -\
  \ Get quality score from `uv run logseq-analyze quality`\n   - Get connection count\
  \ from `uv run logseq-analyze connections`\n   - Get priority score from dashboard\n\
  \n3. **Enhanced categorization**:\n   - Use analysis tool's quality metrics\n  \
  \ - Consider connection count in priority\n   - Include section completeness data\n\
  \n4. Build enhanced candidate structure:\n   ```python\n   {\n       \"topic\":\
  \ \"Topic Name\",\n       \"status\": \"MISSING\" | \"STUB\" | \"PARTIAL\",\n  \
  \     \"word_count\": 0,\n       \"quality_score\": 0.0,  # From analysis\n    \
  \   \"connection_count\": 0,  # From analysis\n       \"missing_sections\": [],\
  \  # From analysis\n       \"analysis_priority\": 0,  # From dashboard\n       \"\
  referenced_in\": [\"file1.md\", \"file2.md\"],\n       \"reference_count\": 2,\n\
  \       \"contexts\": [\"...surrounding text...\"]\n   }\n   ```\n\n### Success\
  \ Criteria - Phase 1\n\n- All files in scope scanned\n- All wiki links extracted\n\
  - Page existence verified\n- Word counts calculated\n- Candidate list built with\
  \ metadata\n\n---\n\n## Phase 2: Prioritization\n\n### Enhanced Priority Score Calculation\n\
  \n**Combine analysis tool scores with reference-based scoring**:\n\nFor each candidate:\n\
  \n```python\n# Start with analysis tool's priority score if available\nscore = analysis_priority\
  \ * 10  # Scale analysis priority\n\n# Factor 1: Reference Count (traditional)\n\
  if reference_count >= 3:\n    score += 100  # High\nelif reference_count == 2:\n\
  \    score += 50   # Medium\nelse:\n    score += 10   # Low\n\n# Factor 2: Quality\
  \ Score (from analysis)\nif quality_score < 0.3:  # Very poor quality\n    score\
  \ += 50\nelif quality_score < 0.5:  # Poor quality\n    score += 30\nelif quality_score\
  \ < 0.7:  # Moderate quality\n    score += 10\n\n# Factor 3: Connection Count (from\
  \ analysis)\nif connection_count == 0:  # Orphaned\n    score += 40\nelif connection_count\
  \ < 3:  # Poorly connected\n    score += 20\nelif connection_count > 10:  # Hub\
  \ page needing expansion\n    score += 15\n\n# Factor 4: Missing Sections (from\
  \ analysis)\nscore += len(missing_sections) * 5  # Each missing section adds priority\n\
  \n# Factor 5: Cross-referenced across content types\nsource_types = set()\nfor file\
  \ in referenced_in:\n    if \"Knowledge Synthesis\" in file:\n        source_types.add(\"\
  synthesis\")\n    elif \"journal\" in file.lower():\n        source_types.add(\"\
  journal\")\n    else:\n        source_types.add(\"zettel\")\n\nif len(source_types)\
  \ >= 2:\n    score += 25\n\n# Factor 6: Importance tags in contexts\nfor context\
  \ in contexts:\n    if \"#[[important]]\" in context.lower():\n        score +=\
  \ 30\n    if \"#[[core concept]]\" in context.lower():\n        score += 25\n  \
  \  if \"#[[research needed]]\" in context.lower():\n        score += 20\n\n# Factor\
  \ 7: Current status\nif status == \"MISSING\":\n    score += 5\nelif status == \"\
  STUB\":\n    score += 3\n```\n\n### Apply Filters\n\n1. **Filter by min_priority**:\n\
  \   - `high`: Keep score ≥ 100\n   - `medium`: Keep score ≥ 50\n   - `low`: Keep\
  \ all\n\n2. **Sort by score** (descending)\n\n3. **Limit to max_topics**: Take top\
  \ N\n\n### Output Phase 2 Results\n\nReport:\n- Total candidates analyzed\n- Priority\
  \ breakdown (high/medium/low counts)\n- Selected topics with scores and rationale\n\
  - Skipped topics (below threshold or exceeds limit)\n\n---\n\n## Phase 3: Topic\
  \ Expansion\n\n### For Each Selected Topic\n\n**Step 1: Gather Context**\n\nExtract\
  \ from candidate metadata:\n- Files where referenced\n- Surrounding text (contexts)\n\
  - Related concepts mentioned alongside\n- Any specific features or capabilities\
  \ mentioned\n\nBuild context summary:\n```\nContext for [[Topic Name]]:\n\nReferenced\
  \ in 2 files:\n1. File A: \"...context text...\"\n2. File B: \"...context text...\"\
  \n\nRelated concepts mentioned: [[Concept 1]], [[Concept 2]]\nFeatures mentioned:\
  \ feature X, capability Y\n```\n\n**Step 2: Invoke Synthesis**\n\nUse the Skill\
  \ tool to invoke `/knowledge:synthesize-knowledge`:\n\n```\n/knowledge:synthesize-knowledge\
  \ \"{topic_name}\"\n\nAdditional context for synthesis:\n- Referenced in: {file_list}\n\
  - Related concepts: {related_concepts}\n- Mentioned features: {features}\n- Use\
  \ cases: {use_cases}\n\nCreate comprehensive zettel (500+ words) covering:\n1. What\
  \ {topic} is and core functionality\n2. Technical details\n3. Use cases and applications\n\
  4. Comparison to alternatives\n5. Related concepts: {links}\n```\n\n**Step 3: Track\
  \ Results**\n\nFor each topic:\n- Monitor synthesis completion\n- Capture success/failure\n\
  - Record created file path, word count\n- Handle errors gracefully (continue with\
  \ remaining topics)\n\n**Step 4: Update Daily Synthesis Summary**\n\nFor each successful\
  \ creation:\n\n1. Read today's daily hub: `logseq/journals/{TODAY}.md`\n   - Where\
  \ {TODAY} = YYYY_MM_DD format\n\n2. Check if topic already well-documented in daily\
  \ hub\n   - If yes: Skip update\n   - If no or bare link: Add brief section\n\n\
  3. Add summary section (one concise bullet):\n   ```markdown\n   - **{Topic Name}**:\
  \ Brief 2-3 sentence summary. See [[Topic Name]] and [[Related 1]], [[Related 2]]\
  \ for details.\n   ```\n\n4. Keep daily hub brief (no comprehensive content)\n\n\
  ---\n\n## Phase 4: Verification and Reporting\n\n### Validate Created Zettels\n\n\
  For each successfully created topic:\n\n1. **File existence**: Verify file exists\
  \ at expected path\n\n2. **Word count**: Check ≥ 500 words\n\n3. **Required sections**:\
  \ Verify presence of:\n   - `## Overview`\n   - `## Key Concepts`\n   - `## Sources`\n\
  \n4. **Sources count**: Check ≥ 3 sources\n\n5. **Related concepts**: Check ≥ 3\
  \ links in Related Concepts section\n\n6. **Assign quality score**:\n   - **EXCELLENT**:\
  \ 1000+ words, 5+ sources\n   - **GOOD**: 750+ words, 4+ sources\n   - **ACCEPTABLE**:\
  \ 500+ words, 3+ sources\n   - **NEEDS_WORK**: Below minimums\n\n### Generate Completion\
  \ Report\n\nCreate comprehensive markdown report with sections for:\n- Execution\
  \ Summary (scope, timing, parameters)\n- Discovery Phase (files scanned, candidates\
  \ found)\n- Prioritization Phase (priority breakdown, selected topics)\n- Expansion\
  \ Phase (successful/failed/skipped topics with details)\n- Verification Phase (validation\
  \ results, link health)\n- Impact Summary (before/after comparison, growth metrics)\n\
  - Next Steps (remaining candidates, suggestions)\n\n---\n\n## Error Handling\n\n\
  ### No Missing Topics Found\n\nIf no candidates after filtering:\n```\n✅ No Missing\
  \ Topics Found\n\n**Scan Results**:\n- Files scanned: {count}\n- Total links: {count}\n\
  - All referenced topics have comprehensive pages\n\n**Knowledge Graph Status**:\
  \ Complete ✓\n```\n\n### All Candidates Below Priority Threshold\n\nIf candidates\
  \ exist but all filtered out:\n```\n⚠ No Topics Meet Priority Threshold\n\n**Discovery**:\
  \ Found {count} missing topics\n**Priority Threshold**: {threshold}\n**Result**:\
  \ 0 topics meet threshold\n\n**Suggestion**:\nLower priority threshold: /knowledge:expand-missing-topics\
  \ {scope} {max} {lower_threshold}\n```\n\n### Synthesis Fails for Topic\n\nIf synthesis\
  \ fails:\n- Log error\n- Mark as FAILED in results\n- Continue with remaining topics\n\
  - Include retry instructions in report\n\n### Max Topics Limit Reached\n\nIf more\
  \ candidates than limit:\n- Select top N by priority score\n- Process normally\n\
  - Report remaining candidates with suggestion to re-run\n\n---\n\n## Quality Standards\n\
  \n**Zettel Quality**:\n- ✅ Minimum 500 words\n- ✅ Required sections present\n- ✅\
  \ 3+ sources with URLs\n- ✅ 3+ related concept links\n- ✅ Concrete examples and\
  \ details\n\n**Daily Hub Integration**:\n- ✅ Brief summaries (30-80 words)\n- ✅\
  \ 2-3 sentences per topic\n- ✅ 2+ wiki links\n- ✅ No comprehensive content inlined\n\
  \n**Discovery Accuracy**:\n- ✅ 100% link extraction\n- ✅ Correct status determination\n\
  - ✅ Accurate word counts\n- ✅ No false positives/negatives\n\n**Reporting**:\n-\
  \ ✅ Before/after comparison\n- ✅ Clear success/failure counts\n- ✅ Quality scores\
  \ for each zettel\n- ✅ File paths documented\n- ✅ Actionable next steps\n\n---\n\
  \n## Implementation Notes\n\n**Use TodoWrite** to track progress through phases:\n\
  1. Discovery phase\n2. Prioritization phase\n3. Expansion phase (sub-task per topic)\n\
  4. Verification phase\n5. Report generation\n\n**File Operations**:\n- Use Glob\
  \ to find files matching patterns\n- Use Read to extract content and check existence\n\
  - Use Edit to append to journal (or Write if creating new)\n\n**Delegation**:\n\
  - Use Skill tool to invoke `/knowledge:synthesize-knowledge`\n- Wait for completion\
  \ before proceeding to next topic\n\n**Success Criteria**:\n- ✅ All phases complete\
  \ without errors\n- ✅ Selected topics expanded or failure reasons documented\n-\
  \ ✅ All created zettels meet 500+ word minimum\n- ✅ Daily synthesis summaries updated\
  \ appropriately\n- ✅ Comprehensive report generated with actionable next steps\n\
  \nExecute this workflow systematically, reporting progress at each phase.\n\n"
---

# Expand Missing Topics Command

Systematically discover and create comprehensive zettels for topics referenced but not documented in your knowledge graph.

## Arguments

- `$1` (optional): **scope** - What to scan for missing topics
  - `today` (default): Today's synthesis file only
  - `week`: Last 7 days of synthesis files
  - `all`: All synthesis files
  - `file:<path>`: Specific file path

- `$2` (optional): **max_topics** - Maximum topics to expand (default: 5, max: 20)

- `$3` (optional): **min_priority** - Minimum priority level (default: medium)
  - `high`: Only 3+ references or importance tags
  - `medium`: 2+ references or special context
  - `low`: All missing topics

- Flags:
  - `--detect-unlinked`: Enable unlinked concept detection
  - `--comprehensive`: Use both wiki links and unlinked concept detection

## Examples

```bash
# Default: Today's synthesis, 5 topics, medium+ priority
/knowledge:expand-missing-topics

# Weekly expansion, 10 topics
/knowledge:expand-missing-topics week 10

# All high-priority topics
/knowledge:expand-missing-topics all 20 high

# Comprehensive discovery (both methods)
/knowledge:expand-missing-topics week --comprehensive
```

## What This Does

This command orchestrates a 4-phase workflow to close gaps in your knowledge graph:

**Phase 1: Discovery** - Identifies missing topics by extracting `[[Wiki Links]]` from synthesis files and checking if pages exist and are comprehensive (500+ words).

**Phase 2: Prioritization** - Ranks topics by reference count, context, and importance tags. Filters by priority threshold and selects top N.

**Phase 3: Expansion** - Creates comprehensive zettels for selected topics by delegating to `/knowledge:synthesize-knowledge` with gathered context.

**Phase 4: Verification** - Validates quality (word counts, sections, sources) and generates comprehensive before/after report.

---

@task knowledge-synthesis

# Task: Expand Missing Topics in Knowledge Graph

Execute the 4-phase workflow to discover and create comprehensive zettels for missing topics referenced in synthesis files.

## Configuration

**Arguments Provided**:
- Scope: $1 (default: "today")
- Max Topics: $2 (default: 5)
- Min Priority: $3 (default: "medium")
- Flags: $* (check for --detect-unlinked, --comprehensive)

**Repository Path**: `/Users/tylerstapler/Documents/personal-wiki`

**Key Directories**:
- Synthesis files: `logseq/pages/Knowledge Synthesis - *.md`
- Topic pages: `logseq/pages/*.md`
- Journals: `logseq/journals/YYYY_MM_DD.md`

---

## Phase 1: Discovery

### Step 1: Run Comprehensive Analysis

**First, get wiki-wide analysis** using the new analysis tools:

```bash
cd /Users/tylerstapler/Documents/personal-wiki
uv run logseq-analyze dashboard logseq/
```

This provides:
- Complete list of stub pages (< 500 words)
- Orphaned and poorly connected pages
- Quality scores for all pages
- Priority rankings based on multiple factors

Parse the dashboard output to extract:
- Pages marked as STUB or INCOMPLETE
- Priority scores for each page
- Connection counts and quality metrics

### Step 2: Determine Scan Scope

Based on scope argument:

**If "today"**:
- File: `logseq/pages/Knowledge Synthesis - {TODAY}.md`
- Where {TODAY} = current date in format `YYYY-MM-DD`

**If "week"**:
- Files: `Knowledge Synthesis - *.md` for last 7 days
- Include topic zettels linked from these daily hubs

**If "all"**:
- Pattern: `logseq/pages/Knowledge Synthesis - *.md`
- All synthesis files

**If "file:<path>"**:
- Single file at provided path
- Extract path from argument

### Step 3: Extract Wiki Links

For each file in scope:

1. Use Read tool to get file contents
2. Extract all `[[Wiki Links]]` and `#[[Tag Links]]` using regex pattern: `(?:#?\[\[([^\]]+)\]\])`
3. Normalize: Trim whitespace, preserve capitalization
4. Build unique set of referenced topics

### Step 4: Enhance with Analysis Data

**Merge traditional discovery with analysis insights**:

For each extracted link:

1. Convert to expected filename:
   - Link: `[[Topic Name]]`
   - File: `logseq/pages/Topic Name.md`

2. Check analysis results for this page:
   - Get quality score from `uv run logseq-analyze quality`
   - Get connection count from `uv run logseq-analyze connections`
   - Get priority score from dashboard

3. **Enhanced categorization**:
   - Use analysis tool's quality metrics
   - Consider connection count in priority
   - Include section completeness data

4. Build enhanced candidate structure:
   ```python
   {
       "topic": "Topic Name",
       "status": "MISSING" | "STUB" | "PARTIAL",
       "word_count": 0,
       "quality_score": 0.0,  # From analysis
       "connection_count": 0,  # From analysis
       "missing_sections": [],  # From analysis
       "analysis_priority": 0,  # From dashboard
       "referenced_in": ["file1.md", "file2.md"],
       "reference_count": 2,
       "contexts": ["...surrounding text..."]
   }
   ```

### Success Criteria - Phase 1

- All files in scope scanned
- All wiki links extracted
- Page existence verified
- Word counts calculated
- Candidate list built with metadata

---

## Phase 2: Prioritization

### Enhanced Priority Score Calculation

**Combine analysis tool scores with reference-based scoring**:

For each candidate:

```python
# Start with analysis tool's priority score if available
score = analysis_priority * 10  # Scale analysis priority

# Factor 1: Reference Count (traditional)
if reference_count >= 3:
    score += 100  # High
elif reference_count == 2:
    score += 50   # Medium
else:
    score += 10   # Low

# Factor 2: Quality Score (from analysis)
if quality_score < 0.3:  # Very poor quality
    score += 50
elif quality_score < 0.5:  # Poor quality
    score += 30
elif quality_score < 0.7:  # Moderate quality
    score += 10

# Factor 3: Connection Count (from analysis)
if connection_count == 0:  # Orphaned
    score += 40
elif connection_count < 3:  # Poorly connected
    score += 20
elif connection_count > 10:  # Hub page needing expansion
    score += 15

# Factor 4: Missing Sections (from analysis)
score += len(missing_sections) * 5  # Each missing section adds priority

# Factor 5: Cross-referenced across content types
source_types = set()
for file in referenced_in:
    if "Knowledge Synthesis" in file:
        source_types.add("synthesis")
    elif "journal" in file.lower():
        source_types.add("journal")
    else:
        source_types.add("zettel")

if len(source_types) >= 2:
    score += 25

# Factor 6: Importance tags in contexts
for context in contexts:
    if "#[[important]]" in context.lower():
        score += 30
    if "#[[core concept]]" in context.lower():
        score += 25
    if "#[[research needed]]" in context.lower():
        score += 20

# Factor 7: Current status
if status == "MISSING":
    score += 5
elif status == "STUB":
    score += 3
```

### Apply Filters

1. **Filter by min_priority**:
   - `high`: Keep score ≥ 100
   - `medium`: Keep score ≥ 50
   - `low`: Keep all

2. **Sort by score** (descending)

3. **Limit to max_topics**: Take top N

### Output Phase 2 Results

Report:
- Total candidates analyzed
- Priority breakdown (high/medium/low counts)
- Selected topics with scores and rationale
- Skipped topics (below threshold or exceeds limit)

---

## Phase 3: Topic Expansion

### For Each Selected Topic

**Step 1: Gather Context**

Extract from candidate metadata:
- Files where referenced
- Surrounding text (contexts)
- Related concepts mentioned alongside
- Any specific features or capabilities mentioned

Build context summary:
```
Context for [[Topic Name]]:

Referenced in 2 files:
1. File A: "...context text..."
2. File B: "...context text..."

Related concepts mentioned: [[Concept 1]], [[Concept 2]]
Features mentioned: feature X, capability Y
```

**Step 2: Invoke Synthesis**

Use the Skill tool to invoke `/knowledge:synthesize-knowledge`:

```
/knowledge:synthesize-knowledge "{topic_name}"

Additional context for synthesis:
- Referenced in: {file_list}
- Related concepts: {related_concepts}
- Mentioned features: {features}
- Use cases: {use_cases}

Create comprehensive zettel (500+ words) covering:
1. What {topic} is and core functionality
2. Technical details
3. Use cases and applications
4. Comparison to alternatives
5. Related concepts: {links}
```

**Step 3: Track Results**

For each topic:
- Monitor synthesis completion
- Capture success/failure
- Record created file path, word count
- Handle errors gracefully (continue with remaining topics)

**Step 4: Update Daily Synthesis Summary**

For each successful creation:

1. Read today's daily hub: `logseq/journals/{TODAY}.md`
   - Where {TODAY} = YYYY_MM_DD format

2. Check if topic already well-documented in daily hub
   - If yes: Skip update
   - If no or bare link: Add brief section

3. Add summary section (one concise bullet):
   ```markdown
   - **{Topic Name}**: Brief 2-3 sentence summary. See [[Topic Name]] and [[Related 1]], [[Related 2]] for details.
   ```

4. Keep daily hub brief (no comprehensive content)

---

## Phase 4: Verification and Reporting

### Validate Created Zettels

For each successfully created topic:

1. **File existence**: Verify file exists at expected path

2. **Word count**: Check ≥ 500 words

3. **Required sections**: Verify presence of:
   - `## Overview`
   - `## Key Concepts`
   - `## Sources`

4. **Sources count**: Check ≥ 3 sources

5. **Related concepts**: Check ≥ 3 links in Related Concepts section

6. **Assign quality score**:
   - **EXCELLENT**: 1000+ words, 5+ sources
   - **GOOD**: 750+ words, 4+ sources
   - **ACCEPTABLE**: 500+ words, 3+ sources
   - **NEEDS_WORK**: Below minimums

### Generate Completion Report

Create comprehensive markdown report with sections for:
- Execution Summary (scope, timing, parameters)
- Discovery Phase (files scanned, candidates found)
- Prioritization Phase (priority breakdown, selected topics)
- Expansion Phase (successful/failed/skipped topics with details)
- Verification Phase (validation results, link health)
- Impact Summary (before/after comparison, growth metrics)
- Next Steps (remaining candidates, suggestions)

---

## Error Handling

### No Missing Topics Found

If no candidates after filtering:
```
✅ No Missing Topics Found

**Scan Results**:
- Files scanned: {count}
- Total links: {count}
- All referenced topics have comprehensive pages

**Knowledge Graph Status**: Complete ✓
```

### All Candidates Below Priority Threshold

If candidates exist but all filtered out:
```
⚠ No Topics Meet Priority Threshold

**Discovery**: Found {count} missing topics
**Priority Threshold**: {threshold}
**Result**: 0 topics meet threshold

**Suggestion**:
Lower priority threshold: /knowledge:expand-missing-topics {scope} {max} {lower_threshold}
```

### Synthesis Fails for Topic

If synthesis fails:
- Log error
- Mark as FAILED in results
- Continue with remaining topics
- Include retry instructions in report

### Max Topics Limit Reached

If more candidates than limit:
- Select top N by priority score
- Process normally
- Report remaining candidates with suggestion to re-run

---

## Quality Standards

**Zettel Quality**:
- ✅ Minimum 500 words
- ✅ Required sections present
- ✅ 3+ sources with URLs
- ✅ 3+ related concept links
- ✅ Concrete examples and details

**Daily Hub Integration**:
- ✅ Brief summaries (30-80 words)
- ✅ 2-3 sentences per topic
- ✅ 2+ wiki links
- ✅ No comprehensive content inlined

**Discovery Accuracy**:
- ✅ 100% link extraction
- ✅ Correct status determination
- ✅ Accurate word counts
- ✅ No false positives/negatives

**Reporting**:
- ✅ Before/after comparison
- ✅ Clear success/failure counts
- ✅ Quality scores for each zettel
- ✅ File paths documented
- ✅ Actionable next steps

---

## Implementation Notes

**Use TodoWrite** to track progress through phases:
1. Discovery phase
2. Prioritization phase
3. Expansion phase (sub-task per topic)
4. Verification phase
5. Report generation

**File Operations**:
- Use Glob to find files matching patterns
- Use Read to extract content and check existence
- Use Edit to append to journal (or Write if creating new)

**Delegation**:
- Use Skill tool to invoke `/knowledge:synthesize-knowledge`
- Wait for completion before proceeding to next topic

**Success Criteria**:
- ✅ All phases complete without errors
- ✅ Selected topics expanded or failure reasons documented
- ✅ All created zettels meet 500+ word minimum
- ✅ Daily synthesis summaries updated appropriately
- ✅ Comprehensive report generated with actionable next steps

Execute this workflow systematically, reporting progress at each phase.

