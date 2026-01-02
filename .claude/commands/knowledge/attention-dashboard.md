---
title: Wiki Attention Dashboard
description: Comprehensive analysis of your Logseq wiki to identify what needs attention, prioritized by importance
arguments: [scope, focus]
tools: Bash, Read, Glob, TodoWrite
model: sonnet
---

# Wiki Attention Dashboard

Analyze your Logseq knowledge base to identify pages needing attention, ranked by multi-factor priority scoring.

## Arguments

- `$1` (optional): **scope** - What to analyze
  - `all` (default): Complete wiki analysis
  - `pages`: Only pages directory
  - `journals`: Only journal entries
  - `recent`: Last 30 days of content

- `$2` (optional): **focus** - Specific analysis focus
  - `dashboard` (default): Unified attention dashboard with all metrics
  - `quality`: Focus on content quality issues
  - `connections`: Focus on link/connection issues
  - `quick`: Fast summary of top issues only

## Examples

```bash
# Full dashboard analysis
/knowledge:attention-dashboard

# Quality-focused analysis of pages
/knowledge:attention-dashboard pages quality

# Quick check of recent content
/knowledge:attention-dashboard recent quick

# Connection analysis for entire wiki
/knowledge:attention-dashboard all connections
```

## What This Does

This command provides a comprehensive view of your wiki's health by:

1. **Running Multi-Factor Analysis** - Quality metrics, connection analysis, and priority scoring
2. **Identifying Issues** - Stub pages, orphaned content, missing sections, poor connections
3. **Prioritizing Attention** - Multi-factor scoring to rank what needs work most urgently
4. **Providing Actionable Guidance** - Specific recommendations for each identified issue
5. **Tracking Progress** - Statistics showing wiki health over time

The analysis considers:
- **Content Quality**: Word count, section completeness, source citations
- **Connectivity**: Orphaned pages, poorly connected pages, hub identification
- **Importance**: Reference frequency, recent activity, semantic importance
- **Completeness**: Missing sections, stub detection, expansion opportunities

---

@task knowledge-analysis

# Task: Generate Wiki Attention Dashboard

Execute comprehensive analysis of the Logseq wiki to identify and prioritize content needing attention.

## Configuration

**Arguments Provided**:
- Scope: ${1:-all}
- Focus: ${2:-dashboard}

**Repository Path**: `/Users/tylerstapler/Documents/personal-wiki`

**Analysis Commands**:
- Dashboard: `uv run logseq-analyze dashboard`
- Quality: `uv run logseq-analyze quality`
- Connections: `uv run logseq-analyze connections`

---

## Phase 1: Environment Setup

### Verify Tool Availability

```bash
cd /Users/tylerstapler/Documents/personal-wiki
uv run logseq-analyze --help
```

If the command is not available:
1. Check installation: `uv pip list | grep stapler-logseq-tools`
2. If missing, install: `uv install -e .`
3. Verify again: `uv run logseq-analyze --help`

### Determine Analysis Scope

Based on scope argument:

**If "all"**:
- Path: `/Users/tylerstapler/Documents/personal-wiki/logseq`
- Include both pages and journals

**If "pages"**:
- Path: `/Users/tylerstapler/Documents/personal-wiki/logseq/pages`
- Exclude journal entries

**If "journals"**:
- Path: `/Users/tylerstapler/Documents/personal-wiki/logseq/journals`
- Focus on daily entries only

**If "recent"**:
- Use dashboard with date filtering
- Last 30 days of content

---

## Phase 2: Run Analysis

### Based on Focus Parameter

**If "dashboard" (default)**:

Run unified dashboard analysis:
```bash
cd /Users/tylerstapler/Documents/personal-wiki
uv run logseq-analyze dashboard [PATH]
```

Expected output structure:
- Priority-ranked list of pages needing attention
- Issues categorized by type (stub, incomplete, orphaned, etc.)
- Specific recommendations for each page
- Overall statistics

**If "quality"**:

Focus on content quality metrics:
```bash
cd /Users/tylerstapler/Documents/personal-wiki
uv run logseq-analyze quality [PATH]
```

Expected output:
- Pages sorted by quality score
- Word counts and completeness metrics
- Missing sections identification
- Source citation analysis

**If "connections"**:

Focus on link and connection analysis:
```bash
cd /Users/tylerstapler/Documents/personal-wiki
uv run logseq-analyze connections [PATH]
```

Expected output:
- Orphaned pages (no incoming links)
- Poorly connected pages (< 3 connections)
- Hub pages (highly connected)
- Link distribution statistics

**If "quick"**:

Run dashboard but limit output:
```bash
cd /Users/tylerstapler/Documents/personal-wiki
uv run logseq-analyze dashboard [PATH] | head -20
```

Show only top priority items for quick review.

---

## Phase 3: Parse and Interpret Results

### Extract Key Information

From the analysis output, identify:

1. **Critical Issues** (Priority > 15):
   - Orphaned important pages
   - Stub pages with high reference count
   - Incomplete core concepts

2. **Quality Problems** (Priority 10-15):
   - Pages missing key sections
   - Low word count on referenced pages
   - Missing source citations

3. **Connection Issues** (Priority 5-10):
   - Poorly connected pages
   - Missing bidirectional links
   - Isolated topic clusters

4. **Minor Issues** (Priority < 5):
   - Style inconsistencies
   - Tag standardization needs
   - Format improvements

### Generate Actionable Recommendations

For each identified issue, provide specific actions:

**For Stub Pages**:
- Recommend: `/knowledge:expand-missing-topics file:[page_path]`
- Or: `/knowledge:synthesize-knowledge "[topic_name]"`

**For Orphaned Pages**:
- Identify potential parent pages
- Suggest links to add in related content
- Consider if page should be merged

**For Missing Sections**:
- List specific sections to add
- Provide section templates
- Suggest content sources

**For Poor Connections**:
- Identify related pages to link
- Suggest bidirectional linking
- Recommend tag additions

---

## Phase 4: Generate Report

### Structure Output Report

Create comprehensive markdown report with:

```markdown
# 📊 Wiki Attention Dashboard

**Analysis Date**: [current_date]
**Scope**: [scope_parameter]
**Total Pages Analyzed**: [count]

## 🎯 Top Priority Items

### Critical (Immediate Attention)
1. **[Page Name]** - [Issue Type]
   - Priority Score: [score]
   - Issue: [description]
   - Action: [specific_recommendation]
   - Command: `[suggested_command]`

### High Priority (This Week)
[List items with priority 10-15]

### Medium Priority (This Month)
[List items with priority 5-10]

## 📈 Wiki Health Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Total Pages | [count] | ✅/⚠️/❌ |
| Average Quality Score | [score] | ✅/⚠️/❌ |
| Orphaned Pages | [count] | ✅/⚠️/❌ |
| Stub Pages | [count] | ✅/⚠️/❌ |
| Average Connections | [avg] | ✅/⚠️/❌ |

## 🔍 Detailed Analysis

### Quality Issues
[Detailed quality analysis results]

### Connection Problems
[Detailed connection analysis results]

### Content Gaps
[Missing topics and sections]

## 💡 Recommended Actions

1. **Immediate**: [Top 3 actions to take now]
2. **This Week**: [5-7 improvements to make]
3. **Ongoing**: [Maintenance recommendations]

## 📝 Next Steps

Based on this analysis, consider:
- Running `/knowledge:expand-missing-topics` for stub pages
- Using `/knowledge:synthesize-knowledge` for missing topics
- Executing `/knowledge:validate_links` for broken links
- Creating new content for orphaned topics
```

---

## Phase 5: Provide Interactive Guidance

### Offer Follow-Up Commands

Based on analysis results, suggest specific commands:

```markdown
## 🚀 Quick Actions Available

Based on the analysis, you can:

1. **Expand top stub pages**:
   ```
   /knowledge:expand-missing-topics file:[top_stub_page] 1
   ```

2. **Fix orphaned pages** (add to daily synthesis):
   ```
   /knowledge:synthesize-knowledge "[orphaned_topic]"
   ```

3. **Validate and fix links**:
   ```
   /knowledge:validate_links --create-missing
   ```

4. **Review quality issues**:
   ```
   uv run logseq-analyze quality --verbose [specific_page]
   ```
```

### Track Progress

Use TodoWrite to create action items:

```python
todos = [
    {"content": f"Expand stub page: {page}", "status": "pending"},
    {"content": f"Add connections to: {orphaned}", "status": "pending"},
    {"content": f"Add missing sections to: {incomplete}", "status": "pending"},
]
```

---

## Error Handling

### Tool Not Available

If `logseq-analyze` is not installed:
```markdown
⚠️ Analysis tool not available. Installing...

Run these commands:
1. cd /Users/tylerstapler/Documents/personal-wiki
2. uv install -e .
3. uv run logseq-analyze dashboard

Then re-run this command.
```

### No Issues Found

If analysis returns no issues:
```markdown
✅ Wiki Health: Excellent!

No critical issues found. Your knowledge base is well-maintained.

Consider:
- Adding new content on emerging topics
- Deepening existing pages with more details
- Creating synthesis of related topics
```

### Path Issues

If path doesn't exist or has no markdown files:
```markdown
❌ Path Issue

The specified path doesn't exist or contains no markdown files.
Please check:
- Path exists: [path]
- Contains .md files
- Correct scope parameter used
```

---

## Quality Standards

**Analysis Accuracy**:
- ✅ All markdown files in scope analyzed
- ✅ Correct issue categorization
- ✅ Accurate priority scoring
- ✅ No false positives

**Report Quality**:
- ✅ Clear, actionable recommendations
- ✅ Specific commands provided
- ✅ Priority-based organization
- ✅ Progress tracking included

**User Experience**:
- ✅ Fast execution (< 5 seconds for most wikis)
- ✅ Clear visual hierarchy in output
- ✅ Emoji indicators for quick scanning
- ✅ Copy-paste ready commands

---

## Integration with Other Commands

This dashboard integrates with:

1. **expand-missing-topics**: Use dashboard to identify high-priority stubs
2. **synthesize-knowledge**: Create content for missing topics
3. **validate_links**: Fix connection issues
4. **create_zettle**: Create new pages for orphaned topics

The dashboard acts as a central hub for wiki maintenance, providing data-driven insights to guide your knowledge management workflow.

---

## Advanced Usage

### Automated Daily Report

Create a daily wiki health check:
```bash
# Add to cron or automation
/knowledge:attention-dashboard recent quick > ~/wiki-health-$(date +%Y-%m-%d).md
```

### Focus on Problem Areas

Drill down into specific issues:
```bash
# Just quality problems
/knowledge:attention-dashboard pages quality

# Just connection issues
/knowledge:attention-dashboard all connections
```

### Progressive Improvement

Work through issues systematically:
1. Run dashboard to get full picture
2. Address critical issues first
3. Re-run to verify improvements
4. Move to next priority level

Execute this analysis workflow to maintain a healthy, well-connected knowledge base.