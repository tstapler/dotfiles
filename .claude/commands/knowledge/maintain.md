# Knowledge Maintenance Orchestrator

**Purpose**: Comprehensive, automated knowledge library maintenance with intelligent remediation.

**Status**: Production-ready with automation capabilities

**Integration**: Leverages `logseq-knowledge-maintain` CLI tool + Claude agents for content creation

---

## Overview

This command orchestrates complete knowledge library maintenance using a hybrid approach:
1. **Python CLI** (`uv run logseq-knowledge-maintain`) for assessment, validation, and coordination
2. **Claude Agents** for content creation (synthesis, zettels, topic expansion)
3. **Automated Remediation** for common link health issues

**CRITICAL**: All processing is done in REVERSE CHRONOLOGICAL order (newest journal dates first) to prioritize recent work over old journal entries. This ensures that recently captured knowledge is fleshed out before moving on to historical entries.

---

## Execution Workflow

### Phase 1: Assessment (Automated)

Run Python CLI for comprehensive assessment:

```bash
uv run logseq-knowledge-maintain --scope {scope} --mode comprehensive --no-confirm
```

**Outputs**:
- Synthesis entries count
- Unlinked concepts estimate
- Missing topics count
- Link health metrics
- Priority recommendations

**Success Criteria**:
- All metrics collected
- Priorities calculated
- Execution plan generated

---

### Phase 2: Automated Remediation (Script-Based)

**BEFORE** launching content creation agents, fix systematic link health issues using automation scripts.

#### 2.1 Remove Template Artifacts

```bash
# Fix placeholder tags from templates (high impact: ~111 broken links)
find logseq/pages -name "*.md" -type f -exec grep -l "technical-area\|domain-category\|Official Documentation Comprehensive" {} \; | \
  while read file; do
    sed -i.bak '/technical-area/d; /domain-category/d; /Official Documentation Comprehensive/d' "$file" && rm "${file}.bak"
  done
```

**Impact**: Eliminates ~37 × 3 = ~111 broken link references

#### 2.2 Create Top Category Pages

```bash
# Create missing high-impact category pages
uv run logseq-knowledge-maintain create-categories \
  --categories "CI/CD,Leadership,Technology,Risk Management,Home Improvement" \
  --template comprehensive
```

**Implementation** (if script doesn't exist, use Claude synthesis):
For each missing category with >20 references:
1. Use `/knowledge/synthesize-knowledge` command
2. Pass category name as topic
3. Request comprehensive zettel with research

**Impact**: Fixes ~160 broken link references

#### 2.3 Create Person Pages

```bash
# Create missing person pages (frequently referenced)
uv run logseq-knowledge-maintain create-person-pages \
  --from-references --min-count 20
```

**Implementation** (use Claude if script missing):
For each person with >20 references:
1. Create page: `logseq/pages/{Person Name}.md`
2. Template:
```markdown
tags:: [[People]], [[FBG]] (or relevant org)
category:: Person

# {Person Name}

## Context
{Inferred from journal mentions}

## Related Topics
{Auto-link to referenced topics}
```

**Impact**: Fixes ~152 broken link references

---

### Phase 3: Content Creation (Claude Agents)

Launch Claude agents for knowledge synthesis and topic expansion.

#### Wave 1: Independent Tasks (Parallel)

```bash
# Launch 3 agents in parallel using Task tool
@task synthesis (haiku) → Process [[Needs Synthesis]] entries
@task concepts (haiku) → Identify unlinked concepts
@task validation (haiku) → Validate links post-remediation
```

**Agent Instructions**:

**Synthesis Agent**:
```
Scan journals within {scope} for [[Needs Synthesis]] tags.
For each entry:
1. Extract content and context
2. Use /knowledge/synthesize-knowledge {topic}
3. Update journal with completion marker
4. Return: count processed, pages created
```

**Concepts Agent**:
```
Scan journals within {scope} for unlinked technical terms.
Patterns: Capitalized phrases, technical compound terms
Filter: Exclude existing pages
Return: List of 10 highest-priority unlinked concepts with context
```

**Validation Agent**:
```
Run: uv run logseq-validate-links validate
Parse output for:
- Total links
- Broken links (count + top 10 by reference)
- Link health percentage
Return: Metrics + recommendations
```

#### Wave 2: Dependent Tasks (Sequential/Parallel)

```bash
# Launch after Wave 1 completes
@task expansion (haiku) → Expand missing topics (depends: synthesis)
@task revalidation (haiku) → Re-validate links (depends: expansion)
```

**Expansion Agent**:
```
From validation results, get top 10 missing topics by reference count.
For each topic (up to 5):
1. Use /knowledge/synthesize-knowledge {topic}
2. Request comprehensive zettel with research
3. Track: topic name, page created, word count
Return: Topics expanded, pages created
```

#### Wave 3: Final Linking (Sequential)

```bash
# Link newly created pages to existing content
@task linking (haiku) → Add wiki links to new pages (depends: expansion)
```

**Linking Agent**:
```
From expansion results, get list of newly created page titles.
Scan journals within {scope} for mentions of these titles (case-insensitive).
For each match:
1. Convert plain text to [[Wiki Link]]
2. Preserve surrounding context
3. Track: links added per file
Return: Total links added
```

---

### Phase 4: Validation & Reporting (Automated)

```bash
# Re-run validation to measure improvement
uv run logseq-validate-links validate > post_maintenance_report.txt

# Generate delta report
python3 - <<EOF
import re

def parse_metrics(file):
    content = open(file).read()
    return {
        'broken': int(re.search(r'Broken links:\s*(\d+)', content).group(1)),
        'total': int(re.search(r'Total links:\s*(\d+)', content).group(1))
    }

before = parse_metrics('pre_maintenance_report.txt')
after = parse_metrics('post_maintenance_report.txt')

print(f"Link Health Improvement:")
print(f"  Before: {before['broken']} broken / {before['total']} total")
print(f"  After:  {after['broken']} broken / {after['total']} total")
print(f"  Fixed:  {before['broken'] - after['broken']} broken links")
print(f"  Health: {((after['total'] - after['broken']) / after['total'] * 100):.1f}%")
EOF
```

---

## Arguments

| Argument | Values | Default | Description |
|----------|--------|---------|-------------|
| `scope` | today, week, month, all | week | Time range for maintenance |
| `mode` | comprehensive, quick, synthesis-only, linking-only | comprehensive | Maintenance mode |
| `--auto-remediate` | flag | false | Enable automated script-based fixes |
| `--skip-confirmation` | flag | false | Skip all confirmation prompts |
| `--parallel` | flag | true | Run agents in parallel |
| `--max-agents` | number | 6 | Maximum concurrent agents |

---

## Usage Examples

### Daily Quick Maintenance
```bash
/knowledge/maintain today quick
```
**Actions**: Synthesis only, no remediation

### Weekly Comprehensive (Default)
```bash
/knowledge/maintain
# Same as: /knowledge/maintain week comprehensive
```
**Actions**: Full workflow with auto-remediation recommendations

### Monthly Deep Clean
```bash
/knowledge/maintain month comprehensive --auto-remediate
```
**Actions**:
1. Full assessment
2. **Automated remediation** (templates, categories, people pages)
3. Comprehensive synthesis and expansion
4. Final validation and reporting

### Synthesis Only (Fast)
```bash
/knowledge/maintain week synthesis-only
```
**Actions**: Only process [[Needs Synthesis]] entries, skip everything else

---

## Auto-Remediation Details

When `--auto-remediate` is enabled:

### Safe Automated Fixes (No Confirmation)
1. **Remove template artifacts** - Zero risk, high impact
2. **Run existing validation scripts** - Read-only operations
3. **Generate reports** - Documentation only

### Semi-Automated Fixes (With Confirmation)
1. **Create category pages** - Uses synthesis command
2. **Create person pages** - Simple template-based creation
3. **Fix date format issues** - Batch sed operations

### Manual Review Required
1. **Ambiguous broken links** - May be typos or intentional
2. **High-priority missing topics** - Require research and synthesis
3. **Complex link graph issues** - Need human judgment

---

## Integration with Existing Tools

### Python CLI (`logseq-knowledge-maintain`)
- **Assessment**: Metrics collection and priority calculation
- **Orchestration**: Wave planning and agent coordination
- **Validation**: Link health checking via `logseq-validate-links`

### Claude Agents (via Task tool)
- **Synthesis**: `/knowledge/synthesize-knowledge` for content creation
- **Research**: Web search and comprehensive zettel generation
- **Linking**: Intelligent wiki link insertion

### Automation Scripts (Shell/Python)
- **sed/awk**: Template artifact removal
- **find/grep**: Broken link identification
- **Python**: Category page generation, metrics calculation

---

## Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Link health | ≥ 95% | (total - broken) / total |
| Synthesis backlog | 0 pending | grep count of [[Needs Synthesis]] |
| Missing high-priority pages | ≤ 5 | Top referenced broken links |
| Agent completion rate | 100% | All agents completed successfully |
| Improvement delta | ≥ 10% | Link health after vs before |

---

## Error Handling

### Agent Failures
- **Retry strategy**: Automatic retry once after 30s delay
- **Graceful degradation**: Continue with remaining agents
- **Recovery commands**: Provide manual recovery steps in report

### Script Failures
- **Validation**: Test on dry-run before execution
- **Backup**: Create `.bak` files before destructive operations
- **Rollback**: Provide rollback commands in case of issues

### Link Health Issues
- **Progressive approach**: Fix highest-impact issues first
- **Incremental validation**: Validate after each remediation phase
- **Stop conditions**: Abort if health decreases

---

## Performance Optimization

### Parallelization Strategy
- **Wave 1**: 3 agents (synthesis, concepts, validation) - fully parallel
- **Wave 2**: 2 agents (expansion, revalidation) - parallel where possible
- **Wave 3**: 1 agent (linking) - sequential (requires Wave 2 completion)

### Model Selection
- **Assessment/Validation**: Use CLI tools (instant)
- **Simple agents** (concepts, validation): Haiku (fast, low cost)
- **Complex synthesis**: Sonnet (quality, reasoning)
- **Research-heavy**: Sonnet with extended thinking

### Caching Strategy
- **Link validation results**: Cache for 5 minutes
- **Page existence checks**: Cache during single maintenance run
- **Assessment metrics**: Persist between waves

---

## Maintenance Schedule Recommendations

### Daily (Quick Mode)
```bash
/knowledge/maintain today quick
```
**Duration**: 2-5 minutes
**Focus**: Clear synthesis backlog

### Weekly (Comprehensive)
```bash
/knowledge/maintain week comprehensive --auto-remediate
```
**Duration**: 10-20 minutes
**Focus**: Full maintenance with automated fixes

### Monthly (Deep Clean)
```bash
/knowledge/maintain month comprehensive --auto-remediate
```
**Duration**: 30-60 minutes
**Focus**: Comprehensive cleanup, expansion, health restoration

---

## Command Invocation

**Format**: `/knowledge/maintain [scope] [mode] [--flags]`

**Minimum**: `/knowledge/maintain` (uses all defaults)

**Prerequisites**:
- `uv` installed and configured
- `logseq-knowledge-maintain` script in PATH
- Wiki repository at current working directory
- Claude Code with Task tool access

**Post-Execution**:
- Review completion report
- Address any manual review items
- Verify link health improvement
- Schedule next maintenance
