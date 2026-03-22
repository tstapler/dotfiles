---
title: Validate Links
description: Validates all [[wiki links]] and #[[tag links]] in Logseq repository, reports broken links, optionally creates stub pages
arguments: [mode, auto_fix]
---

# Validate Links

**Command Purpose**: Ensure knowledge base integrity by:
1. Validating all `[[wiki links]]` and `#[[tag links]]` in the Logseq repository
2. Identifying broken references (links to non-existent pages)
3. Reporting validation results with clear actionable insights
4. Optionally creating stub pages for missing links

**When Invoked**: This command executes directly using the `logseq-validate-links` CLI tool (from `stapler_logseq_tools` package).

---

## Core Methodology

### Phase 1: Link Validation

**Objective**: Scan all Logseq files and validate internal link references.

**Actions**:
1. **Scan Logseq directories**:
   - Pages: `~/Documents/personal-wiki/logseq/pages/*.md`
   - Journals: `~/Documents/personal-wiki/logseq/journals/*.md`
   - Extract all `[[Page Name]]` and `#[[Tag Name]]` references

2. **Validate each link**:
   - Check if target page exists in pages directory
   - Handle filename variations (spaces, underscores, case)
   - Track which files contain each broken link

3. **Execute validation tool**:
   ```bash
   cd ~/Documents/personal-wiki
   logseq-validate-links validate
   ```

**Success Criteria**:
- All markdown files scanned successfully
- All links extracted and checked
- Broken links identified and categorized
- Validation summary generated

**Validation Output Format**:
```
🔗 Broken Links Found
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Missing Page       ┃ Referenced In                ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ New Concept        │ 2025_10_13.md               │
│ Technical Topic    │ Some Page.md, Another.md    │
└────────────────────┴──────────────────────────────┘

📊 Link Validation Summary
┏━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric         ┃ Count ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Pages    │   156 │
│ Files Validated│    89 │
│ Valid Links    │   423 │
│ Broken Links   │     2 │
│ Tag Links      │    78 │
└────────────────┴───────┘
```

---

### Phase 2: Results Analysis and Reporting

**Objective**: Interpret validation results and provide actionable recommendations.

**Actions**:
1. **Categorize broken links**:
   - **High priority**: Referenced in multiple files (core concepts)
   - **Medium priority**: Referenced in journal entries (recent work)
   - **Low priority**: Single reference in older content
   - **Potential typos**: Similar to existing pages (Levenshtein distance < 3)

2. **Analyze patterns**:
   - Identify common missing concepts (themes across broken links)
   - Detect potential typos or case mismatches
   - Find orphaned references (links to pages that never existed)

3. **Generate recommendations**:
   ```
   ## Link Validation Report

   **Status**: [✓ All links valid] OR [⚠ Broken links found]

   **Broken Links Summary**:
   - High priority (multiple references): [count]
   - Medium priority (journals): [count]
   - Low priority (single reference): [count]
   - Potential typos: [count]

   **Recommendations**:
   1. Create pages for high-priority concepts: [[Concept 1]], [[Concept 2]]
   2. Fix potential typos:
      - [[Kuberntes]] → [[Kubernetes]] (referenced in file.md)
   3. Review orphaned references: [[Old Topic]] (may no longer be relevant)
   ```

**Success Criteria**:
- All broken links categorized by priority
- Patterns and typos identified
- Clear recommendations provided
- User can immediately take action

---

### Phase 3: Stub Page Creation (Optional)

**Objective**: Create placeholder pages for missing links to restore reference integrity.

**When to Use**:
- **Mode 1 (auto_fix=true)**: Create stubs automatically for all broken links
- **Mode 2 (auto_fix=false)**: Report broken links, await user confirmation before creating stubs
- **Mode 3 (selective)**: Create stubs only for high-priority links (multiple references)

**Actions**:
1. **Determine stub creation strategy**:
   - If `${2}` (auto_fix) is "true" or "all": Create stubs for all broken links
   - If `${2}` is "selective": Create stubs only for high-priority (multi-referenced)
   - If `${2}` is unset or "false": Report only, don't create stubs

2. **Execute stub creation**:

   **Automatic mode**:
   ```bash
   logseq-validate-links validate --create-missing
   ```

   **Manual mode** (create specific stubs):
   For each missing page:
   - Create file at `~/Documents/personal-wiki/logseq/pages/[Page Name].md`
   - Use structured stub template (see below)
   - Preserve exact page name from link

3. **Stub template structure**:
   ```markdown
   - **Core Definition**: [Page Name]

   ## Background/Context
   - TODO: Add context and background information

   ## Key Characteristics/Principles
   - TODO: Add key characteristics

   ## Related Concepts
   - TODO: Add related concept links

   ## Significance
   - TODO: Add significance and importance

   **Related Topics**: #[[TODO]]
   ```

4. **Verify stub creation**:
   - Confirm files created successfully
   - Re-run validation to verify broken links resolved
   - Report number of stubs created

**Success Criteria**:
- Stubs created for all intended pages
- Structured template used consistently
- Links now resolve successfully
- Re-validation confirms resolution

---

### Phase 4: Verification and Next Steps

**Objective**: Confirm validation results and guide user on follow-up actions.

**Actions**:
1. **Re-validate if stubs created**:
   ```bash
   logseq-validate-links validate
   ```
   - Confirm broken link count reduced to zero (or only intentional omissions)
   - Report any remaining issues

2. **Provide next steps**:

   **If stubs created**:
   ```
   ✓ Created [count] stub pages for broken links.

   **Next Steps**:
   1. Review stub pages and add comprehensive content:
      - [[Page 1]] - Referenced in [file1.md, file2.md]
      - [[Page 2]] - Referenced in [file3.md]

   2. Consider using /knowledge/process-journal-zettels to generate
      research-backed content for these pages.

   3. Run validation again after content updates to ensure quality.
   ```

   **If only reporting**:
   ```
   ⚠ Found [count] broken links.

   **Next Steps**:
   1. Decide whether to create stub pages:
      - Run: `/knowledge/validate-links all true` to auto-create all stubs
      - Run: `/knowledge/validate-links selective true` for high-priority only

   2. Fix potential typos manually:
      - [[Typo]] → [[Correct Name]] in [file.md]

   3. Remove obsolete references if concepts are no longer relevant.
   ```

3. **Generate completion summary**:
   ```
   ## Validation Complete

   **Initial State**:
   - Broken links: [count]
   - Files affected: [count]

   **Actions Taken**:
   - Stubs created: [count] (or "None - report only")
   - Typos identified: [count]

   **Final State**:
   - Broken links remaining: [count]
   - Validation status: [✓ Pass / ⚠ Review needed]

   **Files Created**:
   - ~/Documents/personal-wiki/logseq/pages/[Page1].md
   - ~/Documents/personal-wiki/logseq/pages/[Page2].md
   ```

**Success Criteria**:
- Final validation status confirmed
- Clear next steps provided
- User understands what was done and what remains
- All created files documented

---

## Advanced Features

### Statistics Mode

**Purpose**: Get high-level wiki health metrics without detailed validation.

**Usage**:
```bash
logseq-validate-links stats
```

**Output**:
```
📊 Wiki Statistics

Overall Health:
- Total pages: 156
- Total journals: 245
- Unique links: 423
- Unique tags: 78
- Broken links: 2 (0.5%)

Most Connected Pages (outbound links):
1. [[Platform Engineering]] - 45 links
2. [[Database Design]] - 32 links
3. [[Incident Management]] - 28 links

Link Health Status: ✓ Excellent (99.5% valid)
```

**When to Use**:
- Periodic health checks (weekly/monthly)
- Before major wiki restructuring
- Assessing wiki growth and connectivity

---

### Missing Links Only Mode

**Purpose**: Quick scan for broken links without full validation output.

**Usage**:
```bash
logseq-validate-links missing
```

**Output**:
```
Missing Pages:
- [[New Concept]]
- [[Technical Topic]]
- [[Research Area]]
```

**When to Use**:
- Quick check after bulk edits
- Pre-commit validation
- Scripting/automation

---

## Edge Cases and Error Handling

### Tool Not Found
**Issue**: `logseq-validate-links` command not available
**Action**:
1. Check if package installed: `which logseq-validate-links`
2. If not found, install: `cd ~/Documents/personal-wiki && uv install -e .`
3. Verify: `logseq-validate-links --help`
4. Report if installation fails

### Empty Wiki
**Issue**: No markdown files found in pages/journals
**Action**:
1. Verify paths: `ls ~/Documents/personal-wiki/logseq/pages/`
2. Report: "No markdown files found. Wiki appears empty or path incorrect."
3. Ask user to confirm wiki location

### Permission Errors
**Issue**: Cannot read files or create stubs
**Action**:
1. Check permissions: `ls -la ~/Documents/personal-wiki/logseq/pages/`
2. Report specific permission issues
3. Suggest: `chmod` commands or running with appropriate permissions

### Filename Conflicts
**Issue**: Stub would overwrite existing file (rare edge case)
**Action**:
1. Skip stub creation for conflicting file
2. Report: "Skipped [[Page Name]] - file exists but link not resolving (filename mismatch?)"
3. Suggest manual review

### Special Characters in Page Names
**Issue**: Links contain characters invalid for filenames
**Action**:
1. Sanitize filename (replace invalid characters)
2. Create stub with sanitized name
3. Report mapping: `[[Page/Name]] → Page_Name.md`

---

## Usage Examples

### Example 1: Basic Validation (Report Only)
**Command**: `/knowledge/validate-links`

**Execution**:
```bash
cd ~/Documents/personal-wiki
logseq-validate-links validate
```

**Output**:
```
Scanning 245 files...

🔗 Broken Links Found (3):

High Priority (multiple references):
- [[Database Sharding]] → Referenced in: Performance.md, Scaling.md, 2025_10_15.md

Medium Priority (journals):
- [[Incident Response Playbook]] → Referenced in: 2025_10_20.md

Low Priority (single reference):
- [[Old Framework]] → Referenced in: Archive.md

Potential Typos:
- [[Kuberntes]] → Did you mean [[Kubernetes]]? (in Infrastructure.md)

📊 Summary:
- Total links: 423
- Valid: 420 (99.3%)
- Broken: 3 (0.7%)
- Potential typos: 1

✓ Validation complete. Run with auto_fix to create stubs.
```

**Claude Response**:
```
## Link Validation Results

Found 3 broken links in your wiki:

**High Priority**:
- [[Database Sharding]] - Create this page (referenced in 3 files)

**Medium Priority**:
- [[Incident Response Playbook]] - Recent journal reference

**Low Priority**:
- [[Old Framework]] - Appears in archived content

**Potential Typo**:
- [[Kuberntes]] → [[Kubernetes]] in Infrastructure.md

**Recommendations**:
1. Create [[Database Sharding]] page (high value, multiple references)
2. Fix [[Kuberntes]] typo manually
3. Consider if [[Old Framework]] is still relevant

Run `/knowledge/validate-links all true` to auto-create stubs for all broken links.
```

---

### Example 2: Automatic Stub Creation
**Command**: `/knowledge/validate-links all true`

**Execution**:
```bash
cd ~/Documents/personal-wiki
logseq-validate-links validate --create-missing
```

**Output**:
```
Scanning 245 files...
Found 3 broken links.

Creating stub pages...
✓ Created: Database Sharding.md
✓ Created: Incident Response Playbook.md
✓ Created: Old Framework.md

Re-validating...
✓ All links now valid!

📊 Summary:
- Stubs created: 3
- Broken links resolved: 3
- Remaining issues: 0

Next steps:
- Review stub pages and add content
- Consider using /process-journal-zettels for research-backed content
```

**Claude Response**:
```
## Stubs Created Successfully

Created 3 stub pages to resolve broken links:

1. **Database Sharding.md**
   - Referenced in: Performance.md, Scaling.md, 2025_10_15.md
   - High priority - add comprehensive content

2. **Incident Response Playbook.md**
   - Referenced in: 2025_10_20.md
   - Recent work - fill in details

3. **Old Framework.md**
   - Referenced in: Archive.md
   - Low priority - review if still relevant

**Next Steps**:
1. Review these stubs and add meaningful content
2. Use `/knowledge/process-journal-zettels 2025_10_15` to research Database Sharding
3. Consider creating Incident Response Playbook based on recent experiences

All links now validate successfully ✓
```

---

### Example 3: Selective Stub Creation (High Priority Only)
**Command**: `/knowledge/validate-links selective true`

**Execution**:
```bash
# Run validation first
logseq-validate-links validate

# Manually create only high-priority stubs (multi-referenced)
# Create stub for Database Sharding (3 references)
```

**Output**:
```
Scanning 245 files...
Found 3 broken links.

Creating selective stubs (high-priority only)...
✓ Created: Database Sharding.md (3 references)
⊘ Skipped: Incident Response Playbook.md (1 reference)
⊘ Skipped: Old Framework.md (1 reference)

Re-validating...
⚠ 2 broken links remain (low-priority)

📊 Summary:
- High-priority stubs created: 1
- Remaining broken links: 2 (low priority)
```

**Claude Response**:
```
## Selective Stubs Created

Created stubs for high-priority links only:

**Created**:
- [[Database Sharding]] (3 references) - Priority: High

**Remaining Broken Links** (low priority):
- [[Incident Response Playbook]] (1 reference) - Journal entry
- [[Old Framework]] (1 reference) - Archived content

**Recommendation**:
Focus on completing [[Database Sharding]] content first (multiple references indicate importance).
Address remaining links as needed or run `/knowledge/validate-links all true` to create all stubs.
```

---

### Example 4: Statistics Check
**Command**: `/knowledge/validate-links stats`

**Execution**:
```bash
logseq-validate-links stats
```

**Output**:
```
📊 Wiki Statistics

Overall Health:
- Total pages: 156
- Total journals: 245
- Unique links: 423
- Unique tags: 78
- Broken links: 0 (0%)

Most Connected Pages (outbound links):
1. [[Platform Engineering]] - 45 links
2. [[Database Design]] - 32 links
3. [[Incident Management]] - 28 links
4. [[System Architecture]] - 24 links
5. [[Performance Optimization]] - 21 links

Link Health Status: ✓ Excellent (100% valid)
Connectivity: ✓ Good (avg 2.7 links/page)
```

**Claude Response**:
```
## Wiki Health Report

Your personal wiki is in excellent health!

**Metrics**:
- 156 pages, 245 journal entries
- 423 unique links, 78 tags
- 0 broken links (100% valid) ✓

**Most Connected Topics**:
Your knowledge graph has strong clusters around:
1. Platform Engineering (45 connections)
2. Database Design (32 connections)
3. Incident Management (28 connections)

**Analysis**:
- High connectivity (2.7 links/page average)
- No broken references
- Well-structured knowledge graph

No action needed. Continue building your knowledge base!
```

---

### Example 5: Post-Bulk-Edit Validation
**Scenario**: After renaming several pages or restructuring wiki

**Command**: `/knowledge/validate-links`

**Execution**:
```bash
logseq-validate-links validate
```

**Output**:
```
Scanning 245 files...

🔗 Broken Links Found (8):

Likely due to recent page renames:
- [[Old Page Name]] → Not found (referenced in 5 files)
- [[Another Old Name]] → Not found (referenced in 3 files)

Potential fixes:
- [[Old Page Name]] → [[New Page Name]]? (New Page Name.md exists)
- [[Another Old Name]] → [[Renamed Page]]? (Renamed Page.md exists)

📊 Summary:
- Broken: 8
- Potential renames detected: 2
```

**Claude Response**:
```
## Validation After Restructuring

Detected broken links likely caused by recent page renames:

**Action Needed**:
1. Update links in 5 files: [[Old Page Name]] → [[New Page Name]]
2. Update links in 3 files: [[Another Old Name]] → [[Renamed Page]]

**Options**:
A) Fix manually using search/replace
B) Create redirect stubs (Old Page Name.md with link to new name)
C) Use /knowledge/validate-links to create stubs, then merge content

**Recommendation**: Update links to reflect new page names for clean references.

Would you like me to help update these links across your wiki?
```

---

## Integration Patterns

### Pre-Commit Hook Integration
Add to `.git/hooks/pre-commit` in wiki repository:
```bash
#!/bin/bash
cd ~/Documents/personal-wiki
logseq-validate-links validate --exit-code
if [ $? -eq 1 ]; then
    echo "❌ Commit blocked: Broken links found"
    echo "Fix links or run 'logseq-validate-links validate --create-missing'"
    exit 1
fi
```

### Periodic Health Checks
Add to cron for weekly validation:
```bash
# Every Sunday at 9 AM
0 9 * * 0 cd ~/Documents/personal-wiki && logseq-validate-links stats > /tmp/wiki_health.txt
```

### CI/CD Validation (GitHub Actions)
```yaml
name: Validate Wiki Links
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: uv install -e .
      - name: Validate links
        run: logseq-validate-links validate
```

---

## Quality Standards

All validation must satisfy:

1. **Completeness**:
   - All markdown files scanned (pages + journals)
   - All link types validated ([[links]] and #[[tags]])
   - No false positives or missed broken links

2. **Accuracy**:
   - Filename matching handles case and special characters
   - Typo detection uses reasonable similarity threshold
   - Priority categorization reflects actual reference patterns

3. **Actionability**:
   - Clear recommendations provided
   - Stub templates are comprehensive and consistent
   - Next steps explicitly stated

4. **Safety**:
   - Stub creation never overwrites existing files
   - Original content never modified (only new files created)
   - Validation is non-destructive

5. **Reporting**:
   - Summary includes all key metrics
   - Broken links grouped by priority
   - Files created documented with full paths

---

## Command Invocation

**Format**: `/knowledge/validate-links [mode] [auto_fix]`

**Arguments**:
- `mode` (optional): Validation mode
  - `validate` (default): Full validation with reporting
  - `stats`: High-level statistics only
  - `missing`: Quick list of broken links
  - `selective`: Process high-priority links only
- `auto_fix` (optional): Automatic stub creation
  - `true` or `all`: Create stubs for all broken links
  - `false` (default): Report only, no stub creation
  - `selective`: Create stubs only for multi-referenced pages

**Execution Mode**: Direct execution using `logseq-validate-links` CLI tool

**Expected Duration**: 5-30 seconds depending on wiki size

**Prerequisites**:
- `stapler_logseq_tools` package installed (`uv install -e .`)
- Read access to logseq/pages and logseq/journals directories
- Write access to logseq/pages if creating stubs
