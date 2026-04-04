---
description: Comprehensive analysis of your Logseq wiki to identify what needs attention,
  prioritized by importance
prompt: "# Wiki Attention Dashboard\n\nAnalyze your Logseq knowledge base to identify\
  \ pages needing attention, ranked by multi-factor priority scoring.\n\n## Arguments\n\
  \n- `$1` (optional): **scope** - What to analyze\n  - `all` (default): Complete\
  \ wiki analysis\n  - `pages`: Only pages directory\n  - `journals`: Only journal\
  \ entries\n  - `recent`: Last 30 days of content\n\n- `$2` (optional): **focus**\
  \ - Specific analysis focus\n  - `dashboard` (default): Unified attention dashboard\
  \ with all metrics\n  - `quality`: Focus on content quality issues\n  - `connections`:\
  \ Focus on link/connection issues\n  - `quick`: Fast summary of top issues only\n\
  \n## Examples\n\n```bash\n# Full dashboard analysis\n/knowledge:attention-dashboard\n\
  \n# Quality-focused analysis of pages\n/knowledge:attention-dashboard pages quality\n\
  \n# Quick check of recent content\n/knowledge:attention-dashboard recent quick\n\
  \n# Connection analysis for entire wiki\n/knowledge:attention-dashboard all connections\n\
  ```\n\n## What This Does\n\nThis command provides a comprehensive view of your wiki's\
  \ health by:\n\n1. **Running Multi-Factor Analysis** - Quality metrics, connection\
  \ analysis, and priority scoring\n2. **Identifying Issues** - Stub pages, orphaned\
  \ content, missing sections, poor connections\n3. **Prioritizing Attention** - Multi-factor\
  \ scoring to rank what needs work most urgently\n4. **Providing Actionable Guidance**\
  \ - Specific recommendations for each identified issue\n5. **Tracking Progress**\
  \ - Statistics showing wiki health over time\n\nThe analysis considers:\n- **Content\
  \ Quality**: Word count, section completeness, source citations\n- **Connectivity**:\
  \ Orphaned pages, poorly connected pages, hub identification\n- **Importance**:\
  \ Reference frequency, recent activity, semantic importance\n- **Completeness**:\
  \ Missing sections, stub detection, expansion opportunities\n\n---\n\n@task knowledge-analysis\n\
  \n# Task: Generate Wiki Attention Dashboard\n\nExecute comprehensive analysis of\
  \ the Logseq wiki to identify and prioritize content needing attention.\n\n## Configuration\n\
  \n**Arguments Provided**:\n- Scope: ${1:-all}\n- Focus: ${2:-dashboard}\n\n**Repository\
  \ Path**: `/Users/tylerstapler/Documents/personal-wiki`\n\n**Analysis Commands**:\n\
  - Dashboard: `uv run logseq-analyze dashboard`\n- Quality: `uv run logseq-analyze\
  \ quality`\n- Connections: `uv run logseq-analyze connections`\n\n---\n\n## Phase\
  \ 1: Environment Setup\n\n### Verify Tool Availability\n\n```bash\ncd /Users/tylerstapler/Documents/personal-wiki\n\
  uv run logseq-analyze --help\n```\n\nIf the command is not available:\n1. Check\
  \ installation: `uv pip list | grep stapler-logseq-tools`\n2. If missing, install:\
  \ `uv install -e .`\n3. Verify again: `uv run logseq-analyze --help`\n\n### Determine\
  \ Analysis Scope\n\nBased on scope argument:\n\n**If \"all\"**:\n- Path: `/Users/tylerstapler/Documents/personal-wiki/logseq`\n\
  - Include both pages and journals\n\n**If \"pages\"**:\n- Path: `/Users/tylerstapler/Documents/personal-wiki/logseq/pages`\n\
  - Exclude journal entries\n\n**If \"journals\"**:\n- Path: `/Users/tylerstapler/Documents/personal-wiki/logseq/journals`\n\
  - Focus on daily entries only\n\n**If \"recent\"**:\n- Use dashboard with date filtering\n\
  - Last 30 days of content\n\n---\n\n## Phase 2: Run Analysis\n\n### Based on Focus\
  \ Parameter\n\n**If \"dashboard\" (default)**:\n\nRun unified dashboard analysis:\n\
  ```bash\ncd /Users/tylerstapler/Documents/personal-wiki\nuv run logseq-analyze dashboard\
  \ [PATH]\n```\n\nExpected output structure:\n- Priority-ranked list of pages needing\
  \ attention\n- Issues categorized by type (stub, incomplete, orphaned, etc.)\n-\
  \ Specific recommendations for each page\n- Overall statistics\n\n**If \"quality\"\
  **:\n\nFocus on content quality metrics:\n```bash\ncd /Users/tylerstapler/Documents/personal-wiki\n\
  uv run logseq-analyze quality [PATH]\n```\n\nExpected output:\n- Pages sorted by\
  \ quality score\n- Word counts and completeness metrics\n- Missing sections identification\n\
  - Source citation analysis\n\n**If \"connections\"**:\n\nFocus on link and connection\
  \ analysis:\n```bash\ncd /Users/tylerstapler/Documents/personal-wiki\nuv run logseq-analyze\
  \ connections [PATH]\n```\n\nExpected output:\n- Orphaned pages (no incoming links)\n\
  - Poorly connected pages (< 3 connections)\n- Hub pages (highly connected)\n- Link\
  \ distribution statistics\n\n**If \"quick\"**:\n\nRun dashboard but limit output:\n\
  ```bash\ncd /Users/tylerstapler/Documents/personal-wiki\nuv run logseq-analyze dashboard\
  \ [PATH] | head -20\n```\n\nShow only top priority items for quick review.\n\n---\n\
  \n## Phase 3: Parse and Interpret Results\n\n### Extract Key Information\n\nFrom\
  \ the analysis output, identify:\n\n1. **Critical Issues** (Priority > 15):\n  \
  \ - Orphaned important pages\n   - Stub pages with high reference count\n   - Incomplete\
  \ core concepts\n\n2. **Quality Problems** (Priority 10-15):\n   - Pages missing\
  \ key sections\n   - Low word count on referenced pages\n   - Missing source citations\n\
  \n3. **Connection Issues** (Priority 5-10):\n   - Poorly connected pages\n   - Missing\
  \ bidirectional links\n   - Isolated topic clusters\n\n4. **Minor Issues** (Priority\
  \ < 5):\n   - Style inconsistencies\n   - Tag standardization needs\n   - Format\
  \ improvements\n\n### Generate Actionable Recommendations\n\nFor each identified\
  \ issue, provide specific actions:\n\n**For Stub Pages**:\n- Recommend: `/knowledge:expand-missing-topics\
  \ file:[page_path]`\n- Or: `/knowledge:synthesize-knowledge \"[topic_name]\"`\n\n\
  **For Orphaned Pages**:\n- Identify potential parent pages\n- Suggest links to add\
  \ in related content\n- Consider if page should be merged\n\n**For Missing Sections**:\n\
  - List specific sections to add\n- Provide section templates\n- Suggest content\
  \ sources\n\n**For Poor Connections**:\n- Identify related pages to link\n- Suggest\
  \ bidirectional linking\n- Recommend tag additions\n\n---\n\n## Phase 4: Generate\
  \ Report\n\n### Structure Output Report\n\nCreate comprehensive markdown report\
  \ with:\n\n```markdown\n# \U0001F4CA Wiki Attention Dashboard\n\n**Analysis Date**:\
  \ [current_date]\n**Scope**: [scope_parameter]\n**Total Pages Analyzed**: [count]\n\
  \n## \U0001F3AF Top Priority Items\n\n### Critical (Immediate Attention)\n1. **[Page\
  \ Name]** - [Issue Type]\n   - Priority Score: [score]\n   - Issue: [description]\n\
  \   - Action: [specific_recommendation]\n   - Command: `[suggested_command]`\n\n\
  ### High Priority (This Week)\n[List items with priority 10-15]\n\n### Medium Priority\
  \ (This Month)\n[List items with priority 5-10]\n\n## \U0001F4C8 Wiki Health Metrics\n\
  \n| Metric | Value | Status |\n|--------|-------|--------|\n| Total Pages | [count]\
  \ | ✅/⚠️/❌ |\n| Average Quality Score | [score] | ✅/⚠️/❌ |\n| Orphaned Pages | [count]\
  \ | ✅/⚠️/❌ |\n| Stub Pages | [count] | ✅/⚠️/❌ |\n| Average Connections | [avg] |\
  \ ✅/⚠️/❌ |\n\n## \U0001F50D Detailed Analysis\n\n### Quality Issues\n[Detailed quality\
  \ analysis results]\n\n### Connection Problems\n[Detailed connection analysis results]\n\
  \n### Content Gaps\n[Missing topics and sections]\n\n## \U0001F4A1 Recommended Actions\n\
  \n1. **Immediate**: [Top 3 actions to take now]\n2. **This Week**: [5-7 improvements\
  \ to make]\n3. **Ongoing**: [Maintenance recommendations]\n\n## \U0001F4DD Next\
  \ Steps\n\nBased on this analysis, consider:\n- Running `/knowledge:expand-missing-topics`\
  \ for stub pages\n- Using `/knowledge:synthesize-knowledge` for missing topics\n\
  - Executing `/knowledge:validate_links` for broken links\n- Creating new content\
  \ for orphaned topics\n```\n\n---\n\n## Phase 5: Provide Interactive Guidance\n\n\
  ### Offer Follow-Up Commands\n\nBased on analysis results, suggest specific commands:\n\
  \n```markdown\n## \U0001F680 Quick Actions Available\n\nBased on the analysis, you\
  \ can:\n\n1. **Expand top stub pages**:\n   ```\n   /knowledge:expand-missing-topics\
  \ file:[top_stub_page] 1\n   ```\n\n2. **Fix orphaned pages** (add to daily synthesis):\n\
  \   ```\n   /knowledge:synthesize-knowledge \"[orphaned_topic]\"\n   ```\n\n3. **Validate\
  \ and fix links**:\n   ```\n   /knowledge:validate_links --create-missing\n   ```\n\
  \n4. **Review quality issues**:\n   ```\n   uv run logseq-analyze quality --verbose\
  \ [specific_page]\n   ```\n```\n\n### Track Progress\n\nUse TodoWrite to create\
  \ action items:\n\n```python\ntodos = [\n    {\"content\": f\"Expand stub page:\
  \ {page}\", \"status\": \"pending\"},\n    {\"content\": f\"Add connections to:\
  \ {orphaned}\", \"status\": \"pending\"},\n    {\"content\": f\"Add missing sections\
  \ to: {incomplete}\", \"status\": \"pending\"},\n]\n```\n\n---\n\n## Error Handling\n\
  \n### Tool Not Available\n\nIf `logseq-analyze` is not installed:\n```markdown\n\
  ⚠️ Analysis tool not available. Installing...\n\nRun these commands:\n1. cd /Users/tylerstapler/Documents/personal-wiki\n\
  2. uv install -e .\n3. uv run logseq-analyze dashboard\n\nThen re-run this command.\n\
  ```\n\n### No Issues Found\n\nIf analysis returns no issues:\n```markdown\n✅ Wiki\
  \ Health: Excellent!\n\nNo critical issues found. Your knowledge base is well-maintained.\n\
  \nConsider:\n- Adding new content on emerging topics\n- Deepening existing pages\
  \ with more details\n- Creating synthesis of related topics\n```\n\n### Path Issues\n\
  \nIf path doesn't exist or has no markdown files:\n```markdown\n❌ Path Issue\n\n\
  The specified path doesn't exist or contains no markdown files.\nPlease check:\n\
  - Path exists: [path]\n- Contains .md files\n- Correct scope parameter used\n```\n\
  \n---\n\n## Quality Standards\n\n**Analysis Accuracy**:\n- ✅ All markdown files\
  \ in scope analyzed\n- ✅ Correct issue categorization\n- ✅ Accurate priority scoring\n\
  - ✅ No false positives\n\n**Report Quality**:\n- ✅ Clear, actionable recommendations\n\
  - ✅ Specific commands provided\n- ✅ Priority-based organization\n- ✅ Progress tracking\
  \ included\n\n**User Experience**:\n- ✅ Fast execution (< 5 seconds for most wikis)\n\
  - ✅ Clear visual hierarchy in output\n- ✅ Emoji indicators for quick scanning\n\
  - ✅ Copy-paste ready commands\n\n---\n\n## Integration with Other Commands\n\nThis\
  \ dashboard integrates with:\n\n1. **expand-missing-topics**: Use dashboard to identify\
  \ high-priority stubs\n2. **synthesize-knowledge**: Create content for missing topics\n\
  3. **validate_links**: Fix connection issues\n4. **create_zettle**: Create new pages\
  \ for orphaned topics\n\nThe dashboard acts as a central hub for wiki maintenance,\
  \ providing data-driven insights to guide your knowledge management workflow.\n\n\
  ---\n\n## Advanced Usage\n\n### Automated Daily Report\n\nCreate a daily wiki health\
  \ check:\n```bash\n# Add to cron or automation\n/knowledge:attention-dashboard recent\
  \ quick > ~/wiki-health-$(date +%Y-%m-%d).md\n```\n\n### Focus on Problem Areas\n\
  \nDrill down into specific issues:\n```bash\n# Just quality problems\n/knowledge:attention-dashboard\
  \ pages quality\n\n# Just connection issues\n/knowledge:attention-dashboard all\
  \ connections\n```\n\n### Progressive Improvement\n\nWork through issues systematically:\n\
  1. Run dashboard to get full picture\n2. Address critical issues first\n3. Re-run\
  \ to verify improvements\n4. Move to next priority level\n\nExecute this analysis\
  \ workflow to maintain a healthy, well-connected knowledge base.\n"
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
