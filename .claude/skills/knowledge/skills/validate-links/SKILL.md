---
description: Validates all [[wiki links]] and
prompt: "# Validate Links\n\n**Command Purpose**: Ensure knowledge base integrity\
  \ by:\n1. Validating all `[[wiki links]]` and `#[[tag links]]` in the Logseq repository\n\
  2. Identifying broken references (links to non-existent pages)\n3. Reporting validation\
  \ results with clear actionable insights\n4. Optionally creating stub pages for\
  \ missing links\n\n**When Invoked**: This command executes directly using the `logseq-validate-links`\
  \ CLI tool (from `stapler_logseq_tools` package).\n\n---\n\n## Core Methodology\n\
  \n### Phase 1: Link Validation\n\n**Objective**: Scan all Logseq files and validate\
  \ internal link references.\n\n**Actions**:\n1. **Scan Logseq directories**:\n \
  \  - Pages: `~/Documents/personal-wiki/logseq/pages/*.md`\n   - Journals: `~/Documents/personal-wiki/logseq/journals/*.md`\n\
  \   - Extract all `[[Page Name]]` and `#[[Tag Name]]` references\n\n2. **Validate\
  \ each link**:\n   - Check if target page exists in pages directory\n   - Handle\
  \ filename variations (spaces, underscores, case)\n   - Track which files contain\
  \ each broken link\n\n3. **Execute validation tool**:\n   ```bash\n   cd ~/Documents/personal-wiki\n\
  \   logseq-validate-links validate\n   ```\n\n**Success Criteria**:\n- All markdown\
  \ files scanned successfully\n- All links extracted and checked\n- Broken links\
  \ identified and categorized\n- Validation summary generated\n\n**Validation Output\
  \ Format**:\n```\n\U0001F517 Broken Links Found\n┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n\
  ┃ Missing Page       ┃ Referenced In                ┃\n┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩\n\
  │ New Concept        │ 2025_10_13.md               │\n│ Technical Topic    │ Some\
  \ Page.md, Another.md    │\n└────────────────────┴──────────────────────────────┘\n\
  \n\U0001F4CA Link Validation Summary\n┏━━━━━━━━━━━━━━━━┳━━━━━━━┓\n┃ Metric     \
  \    ┃ Count ┃\n┡━━━━━━━━━━━━━━━━╇━━━━━━━┩\n│ Total Pages    │   156 │\n│ Files\
  \ Validated│    89 │\n│ Valid Links    │   423 │\n│ Broken Links   │     2 │\n│\
  \ Tag Links      │    78 │\n└────────────────┴───────┘\n```\n\n---\n\n### Phase\
  \ 2: Results Analysis and Reporting\n\n**Objective**: Interpret validation results\
  \ and provide actionable recommendations.\n\n**Actions**:\n1. **Categorize broken\
  \ links**:\n   - **High priority**: Referenced in multiple files (core concepts)\n\
  \   - **Medium priority**: Referenced in journal entries (recent work)\n   - **Low\
  \ priority**: Single reference in older content\n   - **Potential typos**: Similar\
  \ to existing pages (Levenshtein distance < 3)\n\n2. **Analyze patterns**:\n   -\
  \ Identify common missing concepts (themes across broken links)\n   - Detect potential\
  \ typos or case mismatches\n   - Find orphaned references (links to pages that never\
  \ existed)\n\n3. **Generate recommendations**:\n   ```\n   ## Link Validation Report\n\
  \n   **Status**: [✓ All links valid] OR [⚠ Broken links found]\n\n   **Broken Links\
  \ Summary**:\n   - High priority (multiple references): [count]\n   - Medium priority\
  \ (journals): [count]\n   - Low priority (single reference): [count]\n   - Potential\
  \ typos: [count]\n\n   **Recommendations**:\n   1. Create pages for high-priority\
  \ concepts: [[Concept 1]], [[Concept 2]]\n   2. Fix potential typos:\n      - [[Kuberntes]]\
  \ → [[Kubernetes]] (referenced in file.md)\n   3. Review orphaned references: [[Old\
  \ Topic]] (may no longer be relevant)\n   ```\n\n**Success Criteria**:\n- All broken\
  \ links categorized by priority\n- Patterns and typos identified\n- Clear recommendations\
  \ provided\n- User can immediately take action\n\n---\n\n### Phase 3: Stub Page\
  \ Creation (Optional)\n\n**Objective**: Create placeholder pages for missing links\
  \ to restore reference integrity.\n\n**When to Use**:\n- **Mode 1 (auto_fix=true)**:\
  \ Create stubs automatically for all broken links\n- **Mode 2 (auto_fix=false)**:\
  \ Report broken links, await user confirmation before creating stubs\n- **Mode 3\
  \ (selective)**: Create stubs only for high-priority links (multiple references)\n\
  \n**Actions**:\n1. **Determine stub creation strategy**:\n   - If `${2}` (auto_fix)\
  \ is \"true\" or \"all\": Create stubs for all broken links\n   - If `${2}` is \"\
  selective\": Create stubs only for high-priority (multi-referenced)\n   - If `${2}`\
  \ is unset or \"false\": Report only, don't create stubs\n\n2. **Execute stub creation**:\n\
  \n   **Automatic mode**:\n   ```bash\n   logseq-validate-links validate --create-missing\n\
  \   ```\n\n   **Manual mode** (create specific stubs):\n   For each missing page:\n\
  \   - Create file at `~/Documents/personal-wiki/logseq/pages/[Page Name].md`\n \
  \  - Use structured stub template (see below)\n   - Preserve exact page name from\
  \ link\n\n3. **Stub template structure**:\n   ```markdown\n   - **Core Definition**:\
  \ [Page Name]\n\n   ## Background/Context\n   - TODO: Add context and background\
  \ information\n\n   ## Key Characteristics/Principles\n   - TODO: Add key characteristics\n\
  \n   ## Related Concepts\n   - TODO: Add related concept links\n\n   ## Significance\n\
  \   - TODO: Add significance and importance\n\n   **Related Topics**: #[[TODO]]\n\
  \   ```\n\n4. **Verify stub creation**:\n   - Confirm files created successfully\n\
  \   - Re-run validation to verify broken links resolved\n   - Report number of stubs\
  \ created\n\n**Success Criteria**:\n- Stubs created for all intended pages\n- Structured\
  \ template used consistently\n- Links now resolve successfully\n- Re-validation\
  \ confirms resolution\n\n---\n\n### Phase 4: Verification and Next Steps\n\n**Objective**:\
  \ Confirm validation results and guide user on follow-up actions.\n\n**Actions**:\n\
  1. **Re-validate if stubs created**:\n   ```bash\n   logseq-validate-links validate\n\
  \   ```\n   - Confirm broken link count reduced to zero (or only intentional omissions)\n\
  \   - Report any remaining issues\n\n2. **Provide next steps**:\n\n   **If stubs\
  \ created**:\n   ```\n   ✓ Created [count] stub pages for broken links.\n\n   **Next\
  \ Steps**:\n   1. Review stub pages and add comprehensive content:\n      - [[Page\
  \ 1]] - Referenced in [file1.md, file2.md]\n      - [[Page 2]] - Referenced in [file3.md]\n\
  \n   2. Consider using /knowledge/process-journal-zettels to generate\n      research-backed\
  \ content for these pages.\n\n   3. Run validation again after content updates to\
  \ ensure quality.\n   ```\n\n   **If only reporting**:\n   ```\n   ⚠ Found [count]\
  \ broken links.\n\n   **Next Steps**:\n   1. Decide whether to create stub pages:\n\
  \      - Run: `/knowledge/validate-links all true` to auto-create all stubs\n  \
  \    - Run: `/knowledge/validate-links selective true` for high-priority only\n\n\
  \   2. Fix potential typos manually:\n      - [[Typo]] → [[Correct Name]] in [file.md]\n\
  \n   3. Remove obsolete references if concepts are no longer relevant.\n   ```\n\
  \n3. **Generate completion summary**:\n   ```\n   ## Validation Complete\n\n   **Initial\
  \ State**:\n   - Broken links: [count]\n   - Files affected: [count]\n\n   **Actions\
  \ Taken**:\n   - Stubs created: [count] (or \"None - report only\")\n   - Typos\
  \ identified: [count]\n\n   **Final State**:\n   - Broken links remaining: [count]\n\
  \   - Validation status: [✓ Pass / ⚠ Review needed]\n\n   **Files Created**:\n \
  \  - ~/Documents/personal-wiki/logseq/pages/[Page1].md\n   - ~/Documents/personal-wiki/logseq/pages/[Page2].md\n\
  \   ```\n\n**Success Criteria**:\n- Final validation status confirmed\n- Clear next\
  \ steps provided\n- User understands what was done and what remains\n- All created\
  \ files documented\n\n---\n\n## Advanced Features\n\n### Statistics Mode\n\n**Purpose**:\
  \ Get high-level wiki health metrics without detailed validation.\n\n**Usage**:\n\
  ```bash\nlogseq-validate-links stats\n```\n\n**Output**:\n```\n\U0001F4CA Wiki Statistics\n\
  \nOverall Health:\n- Total pages: 156\n- Total journals: 245\n- Unique links: 423\n\
  - Unique tags: 78\n- Broken links: 2 (0.5%)\n\nMost Connected Pages (outbound links):\n\
  1. [[Platform Engineering]] - 45 links\n2. [[Database Design]] - 32 links\n3. [[Incident\
  \ Management]] - 28 links\n\nLink Health Status: ✓ Excellent (99.5% valid)\n```\n\
  \n**When to Use**:\n- Periodic health checks (weekly/monthly)\n- Before major wiki\
  \ restructuring\n- Assessing wiki growth and connectivity\n\n---\n\n### Missing\
  \ Links Only Mode\n\n**Purpose**: Quick scan for broken links without full validation\
  \ output.\n\n**Usage**:\n```bash\nlogseq-validate-links missing\n```\n\n**Output**:\n\
  ```\nMissing Pages:\n- [[New Concept]]\n- [[Technical Topic]]\n- [[Research Area]]\n\
  ```\n\n**When to Use**:\n- Quick check after bulk edits\n- Pre-commit validation\n\
  - Scripting/automation\n\n---\n\n## Edge Cases and Error Handling\n\n### Tool Not\
  \ Found\n**Issue**: `logseq-validate-links` command not available\n**Action**:\n\
  1. Check if package installed: `which logseq-validate-links`\n2. If not found, install:\
  \ `cd ~/Documents/personal-wiki && uv install -e .`\n3. Verify: `logseq-validate-links\
  \ --help`\n4. Report if installation fails\n\n### Empty Wiki\n**Issue**: No markdown\
  \ files found in pages/journals\n**Action**:\n1. Verify paths: `ls ~/Documents/personal-wiki/logseq/pages/`\n\
  2. Report: \"No markdown files found. Wiki appears empty or path incorrect.\"\n\
  3. Ask user to confirm wiki location\n\n### Permission Errors\n**Issue**: Cannot\
  \ read files or create stubs\n**Action**:\n1. Check permissions: `ls -la ~/Documents/personal-wiki/logseq/pages/`\n\
  2. Report specific permission issues\n3. Suggest: `chmod` commands or running with\
  \ appropriate permissions\n\n### Filename Conflicts\n**Issue**: Stub would overwrite\
  \ existing file (rare edge case)\n**Action**:\n1. Skip stub creation for conflicting\
  \ file\n2. Report: \"Skipped [[Page Name]] - file exists but link not resolving\
  \ (filename mismatch?)\"\n3. Suggest manual review\n\n### Special Characters in\
  \ Page Names\n**Issue**: Links contain characters invalid for filenames\n**Action**:\n\
  1. Sanitize filename (replace invalid characters)\n2. Create stub with sanitized\
  \ name\n3. Report mapping: `[[Page/Name]] → Page_Name.md`\n\n---\n\n## Usage Examples\n\
  \n### Example 1: Basic Validation (Report Only)\n**Command**: `/knowledge/validate-links`\n\
  \n**Execution**:\n```bash\ncd ~/Documents/personal-wiki\nlogseq-validate-links validate\n\
  ```\n\n**Output**:\n```\nScanning 245 files...\n\n\U0001F517 Broken Links Found\
  \ (3):\n\nHigh Priority (multiple references):\n- [[Database Sharding]] → Referenced\
  \ in: Performance.md, Scaling.md, 2025_10_15.md\n\nMedium Priority (journals):\n\
  - [[Incident Response Playbook]] → Referenced in: 2025_10_20.md\n\nLow Priority\
  \ (single reference):\n- [[Old Framework]] → Referenced in: Archive.md\n\nPotential\
  \ Typos:\n- [[Kuberntes]] → Did you mean [[Kubernetes]]? (in Infrastructure.md)\n\
  \n\U0001F4CA Summary:\n- Total links: 423\n- Valid: 420 (99.3%)\n- Broken: 3 (0.7%)\n\
  - Potential typos: 1\n\n✓ Validation complete. Run with auto_fix to create stubs.\n\
  ```\n\n**Claude Response**:\n```\n## Link Validation Results\n\nFound 3 broken links\
  \ in your wiki:\n\n**High Priority**:\n- [[Database Sharding]] - Create this page\
  \ (referenced in 3 files)\n\n**Medium Priority**:\n- [[Incident Response Playbook]]\
  \ - Recent journal reference\n\n**Low Priority**:\n- [[Old Framework]] - Appears\
  \ in archived content\n\n**Potential Typo**:\n- [[Kuberntes]] → [[Kubernetes]] in\
  \ Infrastructure.md\n\n**Recommendations**:\n1. Create [[Database Sharding]] page\
  \ (high value, multiple references)\n2. Fix [[Kuberntes]] typo manually\n3. Consider\
  \ if [[Old Framework]] is still relevant\n\nRun `/knowledge/validate-links all true`\
  \ to auto-create stubs for all broken links.\n```\n\n---\n\n### Example 2: Automatic\
  \ Stub Creation\n**Command**: `/knowledge/validate-links all true`\n\n**Execution**:\n\
  ```bash\ncd ~/Documents/personal-wiki\nlogseq-validate-links validate --create-missing\n\
  ```\n\n**Output**:\n```\nScanning 245 files...\nFound 3 broken links.\n\nCreating\
  \ stub pages...\n✓ Created: Database Sharding.md\n✓ Created: Incident Response Playbook.md\n\
  ✓ Created: Old Framework.md\n\nRe-validating...\n✓ All links now valid!\n\n\U0001F4CA\
  \ Summary:\n- Stubs created: 3\n- Broken links resolved: 3\n- Remaining issues:\
  \ 0\n\nNext steps:\n- Review stub pages and add content\n- Consider using /process-journal-zettels\
  \ for research-backed content\n```\n\n**Claude Response**:\n```\n## Stubs Created\
  \ Successfully\n\nCreated 3 stub pages to resolve broken links:\n\n1. **Database\
  \ Sharding.md**\n   - Referenced in: Performance.md, Scaling.md, 2025_10_15.md\n\
  \   - High priority - add comprehensive content\n\n2. **Incident Response Playbook.md**\n\
  \   - Referenced in: 2025_10_20.md\n   - Recent work - fill in details\n\n3. **Old\
  \ Framework.md**\n   - Referenced in: Archive.md\n   - Low priority - review if\
  \ still relevant\n\n**Next Steps**:\n1. Review these stubs and add meaningful content\n\
  2. Use `/knowledge/process-journal-zettels 2025_10_15` to research Database Sharding\n\
  3. Consider creating Incident Response Playbook based on recent experiences\n\n\
  All links now validate successfully ✓\n```\n\n---\n\n### Example 3: Selective Stub\
  \ Creation (High Priority Only)\n**Command**: `/knowledge/validate-links selective\
  \ true`\n\n**Execution**:\n```bash\n# Run validation first\nlogseq-validate-links\
  \ validate\n\n# Manually create only high-priority stubs (multi-referenced)\n# Create\
  \ stub for Database Sharding (3 references)\n```\n\n**Output**:\n```\nScanning 245\
  \ files...\nFound 3 broken links.\n\nCreating selective stubs (high-priority only)...\n\
  ✓ Created: Database Sharding.md (3 references)\n⊘ Skipped: Incident Response Playbook.md\
  \ (1 reference)\n⊘ Skipped: Old Framework.md (1 reference)\n\nRe-validating...\n\
  ⚠ 2 broken links remain (low-priority)\n\n\U0001F4CA Summary:\n- High-priority stubs\
  \ created: 1\n- Remaining broken links: 2 (low priority)\n```\n\n**Claude Response**:\n\
  ```\n## Selective Stubs Created\n\nCreated stubs for high-priority links only:\n\
  \n**Created**:\n- [[Database Sharding]] (3 references) - Priority: High\n\n**Remaining\
  \ Broken Links** (low priority):\n- [[Incident Response Playbook]] (1 reference)\
  \ - Journal entry\n- [[Old Framework]] (1 reference) - Archived content\n\n**Recommendation**:\n\
  Focus on completing [[Database Sharding]] content first (multiple references indicate\
  \ importance).\nAddress remaining links as needed or run `/knowledge/validate-links\
  \ all true` to create all stubs.\n```\n\n---\n\n### Example 4: Statistics Check\n\
  **Command**: `/knowledge/validate-links stats`\n\n**Execution**:\n```bash\nlogseq-validate-links\
  \ stats\n```\n\n**Output**:\n```\n\U0001F4CA Wiki Statistics\n\nOverall Health:\n\
  - Total pages: 156\n- Total journals: 245\n- Unique links: 423\n- Unique tags: 78\n\
  - Broken links: 0 (0%)\n\nMost Connected Pages (outbound links):\n1. [[Platform\
  \ Engineering]] - 45 links\n2. [[Database Design]] - 32 links\n3. [[Incident Management]]\
  \ - 28 links\n4. [[System Architecture]] - 24 links\n5. [[Performance Optimization]]\
  \ - 21 links\n\nLink Health Status: ✓ Excellent (100% valid)\nConnectivity: ✓ Good\
  \ (avg 2.7 links/page)\n```\n\n**Claude Response**:\n```\n## Wiki Health Report\n\
  \nYour personal wiki is in excellent health!\n\n**Metrics**:\n- 156 pages, 245 journal\
  \ entries\n- 423 unique links, 78 tags\n- 0 broken links (100% valid) ✓\n\n**Most\
  \ Connected Topics**:\nYour knowledge graph has strong clusters around:\n1. Platform\
  \ Engineering (45 connections)\n2. Database Design (32 connections)\n3. Incident\
  \ Management (28 connections)\n\n**Analysis**:\n- High connectivity (2.7 links/page\
  \ average)\n- No broken references\n- Well-structured knowledge graph\n\nNo action\
  \ needed. Continue building your knowledge base!\n```\n\n---\n\n### Example 5: Post-Bulk-Edit\
  \ Validation\n**Scenario**: After renaming several pages or restructuring wiki\n\
  \n**Command**: `/knowledge/validate-links`\n\n**Execution**:\n```bash\nlogseq-validate-links\
  \ validate\n```\n\n**Output**:\n```\nScanning 245 files...\n\n\U0001F517 Broken\
  \ Links Found (8):\n\nLikely due to recent page renames:\n- [[Old Page Name]] →\
  \ Not found (referenced in 5 files)\n- [[Another Old Name]] → Not found (referenced\
  \ in 3 files)\n\nPotential fixes:\n- [[Old Page Name]] → [[New Page Name]]? (New\
  \ Page Name.md exists)\n- [[Another Old Name]] → [[Renamed Page]]? (Renamed Page.md\
  \ exists)\n\n\U0001F4CA Summary:\n- Broken: 8\n- Potential renames detected: 2\n\
  ```\n\n**Claude Response**:\n```\n## Validation After Restructuring\n\nDetected\
  \ broken links likely caused by recent page renames:\n\n**Action Needed**:\n1. Update\
  \ links in 5 files: [[Old Page Name]] → [[New Page Name]]\n2. Update links in 3\
  \ files: [[Another Old Name]] → [[Renamed Page]]\n\n**Options**:\nA) Fix manually\
  \ using search/replace\nB) Create redirect stubs (Old Page Name.md with link to\
  \ new name)\nC) Use /knowledge/validate-links to create stubs, then merge content\n\
  \n**Recommendation**: Update links to reflect new page names for clean references.\n\
  \nWould you like me to help update these links across your wiki?\n```\n\n---\n\n\
  ## Integration Patterns\n\n### Pre-Commit Hook Integration\nAdd to `.git/hooks/pre-commit`\
  \ in wiki repository:\n```bash\n#!/bin/bash\ncd ~/Documents/personal-wiki\nlogseq-validate-links\
  \ validate --exit-code\nif [ $? -eq 1 ]; then\n    echo \"❌ Commit blocked: Broken\
  \ links found\"\n    echo \"Fix links or run 'logseq-validate-links validate --create-missing'\"\
  \n    exit 1\nfi\n```\n\n### Periodic Health Checks\nAdd to cron for weekly validation:\n\
  ```bash\n# Every Sunday at 9 AM\n0 9 * * 0 cd ~/Documents/personal-wiki && logseq-validate-links\
  \ stats > /tmp/wiki_health.txt\n```\n\n### CI/CD Validation (GitHub Actions)\n```yaml\n\
  name: Validate Wiki Links\non: [push, pull_request]\njobs:\n  validate:\n    runs-on:\
  \ ubuntu-latest\n    steps:\n      - uses: actions/checkout@v3\n      - name: Install\
  \ dependencies\n        run: uv install -e .\n      - name: Validate links\n   \
  \     run: logseq-validate-links validate\n```\n\n---\n\n## Quality Standards\n\n\
  All validation must satisfy:\n\n1. **Completeness**:\n   - All markdown files scanned\
  \ (pages + journals)\n   - All link types validated ([[links]] and #[[tags]])\n\
  \   - No false positives or missed broken links\n\n2. **Accuracy**:\n   - Filename\
  \ matching handles case and special characters\n   - Typo detection uses reasonable\
  \ similarity threshold\n   - Priority categorization reflects actual reference patterns\n\
  \n3. **Actionability**:\n   - Clear recommendations provided\n   - Stub templates\
  \ are comprehensive and consistent\n   - Next steps explicitly stated\n\n4. **Safety**:\n\
  \   - Stub creation never overwrites existing files\n   - Original content never\
  \ modified (only new files created)\n   - Validation is non-destructive\n\n5. **Reporting**:\n\
  \   - Summary includes all key metrics\n   - Broken links grouped by priority\n\
  \   - Files created documented with full paths\n\n---\n\n## Command Invocation\n\
  \n**Format**: `/knowledge/validate-links [mode] [auto_fix]`\n\n**Arguments**:\n\
  - `mode` (optional): Validation mode\n  - `validate` (default): Full validation\
  \ with reporting\n  - `stats`: High-level statistics only\n  - `missing`: Quick\
  \ list of broken links\n  - `selective`: Process high-priority links only\n- `auto_fix`\
  \ (optional): Automatic stub creation\n  - `true` or `all`: Create stubs for all\
  \ broken links\n  - `false` (default): Report only, no stub creation\n  - `selective`:\
  \ Create stubs only for multi-referenced pages\n\n**Execution Mode**: Direct execution\
  \ using `logseq-validate-links` CLI tool\n\n**Expected Duration**: 5-30 seconds\
  \ depending on wiki size\n\n**Prerequisites**:\n- `stapler_logseq_tools` package\
  \ installed (`uv install -e .`)\n- Read access to logseq/pages and logseq/journals\
  \ directories\n- Write access to logseq/pages if creating stubs\n"
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
