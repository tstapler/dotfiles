# Knowledge Processing Architecture

A unified system for processing tagged journal entries into comprehensive Zettelkasten knowledge.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    /knowledge/enrich                            │
│                  (Single Orchestrator)                          │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1: Discovery    - Scan journals for ALL enrichment tags  │
│  Phase 2: Dispatch     - Route to specialized handlers          │
│  Phase 3: Cleanup      - Consistent tag removal                 │
│  Phase 4: Report       - Unified completion report              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Handler Skills                                │
│              (.claude/skills/knowledge/handlers/)                │
├────────────────┬────────────────┬────────────────┬──────────────┤
│  synthesis-    │  research-     │  handy-plan-   │  book-       │
│  handler.md    │  handler.md    │  handler.md    │  recommend-  │
│                │                │                │  ation-      │
│ [[Needs       │ [[Needs        │ [[Needs Handy  │  handler.md  │
│  Synthesis]]   │  Research]]    │  Plan]]        │              │
│                │                │                │ [[Book       │
│ Domain logic   │ Domain logic   │ Domain logic   │  Recommend-  │
│ for knowledge  │ for evaluation │ for project    │  ation]]     │
│ synthesis      │ and comparison │ planning       │              │
│                │                │                │ Domain logic │
│                │                │                │ for book     │
│                │                │                │ processing   │
└────────────────┴────────────────┴────────────────┴──────────────┘
```

---

## Key Design Principles

### 1. Single Entry Point
Users invoke **one command** (`/knowledge/enrich`) that handles all tag types. No need to remember separate commands for each tag.

### 2. Specialized Knowledge in Handlers
Each handler skill contains deep domain-specific logic:
- **Synthesis handler**: Hub/spoke architecture, child topic discovery, source requirements
- **Research handler**: Comparison matrices, recommendation patterns, source evaluation
- **Handy plan handler**: Safety sections, cost estimates, tool/material lists
- **Book handler**: Library integration, audiobook checking, author linking

### 3. Consistent Orchestration
The orchestrator ensures:
- **Uniform discovery** across all tag types
- **Consistent cleanup** (same transformation pattern)
- **Unified reporting** (single comprehensive report)
- **Graceful error handling** (failures don't cascade)

### 4. Extensibility
Adding new tag types requires:
1. Create new handler skill in `.claude/skills/knowledge/handlers/`
2. Add tag pattern to orchestrator's discovery phase
3. No changes to cleanup or reporting logic

---

## Semantic Definitions

### The Four Knowledge Tags

| Tag | Purpose | When to Use | Output |
|-----|---------|-------------|--------|
| `[[Needs Synthesis]]` | Create evergreen knowledge from learning | Articles, papers, books, videos, podcasts to synthesize | Daily hub + comprehensive topic Zettels |
| `[[Needs Research]]` | Evaluate and compare options | Products, tools, technologies to evaluate | Comparison zettels + recommendations |
| `[[Needs Handy Plan]]` | Plan physical projects | Construction, DIY, home improvement | Project plans with tools, materials, safety |
| `[[Book Recommendation]]` | Track and evaluate book recommendations | Books to consider adding to reading list | Book-sync entry + wiki page |

---

### [[Needs Synthesis]]

**Semantic Definition**:
> "I have consumed or found content (article, paper, video, book chapter) that contains valuable knowledge I want to internalize and make evergreen in my personal knowledge system."

**Use When**:
- Reading an interesting article or blog post
- Watching an educational video or talk
- Finishing a book chapter with key insights
- Discovering a new concept or pattern to understand
- Processing conference talks or podcasts

**NOT For**:
- Evaluating products or tools (use `[[Needs Research]]`)
- Planning physical projects (use `[[Needs Handy Plan]]`)
- Books you haven't read yet (use `[[Book Recommendation]]`)

**Example Entries**:
```markdown
- Dynamic Routing on WireGuard | https://example.com/article [[Needs Synthesis]]
- Great talk on Event Sourcing at QCon [[Needs Synthesis]]
- "Designing Data-Intensive Applications" Chapter 9 [[Needs Synthesis]]
```

**Output**:
- Comprehensive topic Zettel(s) (500+ words)
- Brief summary in daily synthesis hub (30-80 words)
- Bidirectional wiki links

---

### [[Needs Research]]

**Semantic Definition**:
> "I need to evaluate, compare, or investigate something before making a decision. This requires research from multiple sources to understand trade-offs and make a recommendation."

**Use When**:
- Evaluating which tool/product to buy or adopt
- Comparing technical approaches or architectures
- Investigating why something isn't working
- Researching best practices for implementation
- Making buy vs build decisions

**NOT For**:
- Learning from content already consumed (use `[[Needs Synthesis]]`)
- Physical DIY projects (use `[[Needs Handy Plan]]`)
- Books to add to reading list (use `[[Book Recommendation]]`)

**Example Entries**:
```markdown
- Compare Kafka vs Pulsar vs RabbitMQ for our use case [[Needs Research]]
- Need to find a good password manager for the team [[Needs Research]]
- Research why PostgreSQL queries are slow [[Needs Research]]
```

**Output**:
- Research Zettel with findings (300+ words)
- Comparison matrix (for evaluations)
- Clear recommendation with reasoning
- Individual product/tool pages as needed

---

### [[Needs Handy Plan]]

**Semantic Definition**:
> "I have a physical project that requires detailed planning before execution: tools needed, materials to buy, safety considerations, and step-by-step instructions."

**Use When**:
- Home repairs (fix leaky faucet, repair drywall)
- Home improvements (install ceiling fan, build shelves)
- Renovation projects (bathroom remodel, kitchen updates)
- Construction projects (build deck, garden beds)
- Maintenance tasks (HVAC service, gutter cleaning)

**NOT For**:
- Software or technical research (use `[[Needs Research]]`)
- Learning from content (use `[[Needs Synthesis]]`)
- Buying decisions without physical work (use `[[Needs Research]]`)

**Example Entries**:
```markdown
- Fix dripping kitchen faucet [[Needs Handy Plan]]
- Install ceiling fan in bedroom [[Needs Handy Plan]]
- Build raised garden beds [[Needs Handy Plan]]
- Repoint brick stairs on front porch [[Needs Handy Plan]]
```

**Output**:
- Comprehensive project plan Zettel with:
  - Safety brief and PPE requirements
  - Complete tools list
  - Materials list with quantities and costs
  - Step-by-step instructions
  - Quality control checklist
  - Professional threshold indicators

---

### [[Book Recommendation]]

**Semantic Definition**:
> "Someone recommended a book, or I saw a book mentioned that I want to consider adding to my reading list. I need to research it, evaluate fit, and add it to my library system."

**Use When**:
- Someone recommends a book in conversation
- You see a book mentioned in an article or podcast
- You want to explore an author's work
- A book appears on a "best of" list
- You want to track a book for future consideration

**NOT For**:
- Books you've already read (create Zettel directly)
- Synthesizing book content (use `[[Needs Synthesis]]`)
- Comparing specific editions (use `[[Needs Research]]`)

**Example Entries**:
```markdown
- "Deep Work" by Cal Newport - John recommended for focus strategies [[Book Recommendation]]
- Check out "The Phoenix Project" [[Book Recommendation]]
- Tim Ferriss mentioned "Tools of Titans" on podcast [[Book Recommendation]]
```

**Output**:
- Book wiki page with synopsis, audiobook info
- Entry in book-sync system
- Updated journal with links to book page

---

## Decision Tree: Which Tag to Use?

```
Is this about a BOOK I want to read?
├─ YES → [[Book Recommendation]]
└─ NO → Continue

Is this a PHYSICAL project requiring tools/materials?
├─ YES → [[Needs Handy Plan]]
└─ NO → Continue

Am I EVALUATING or COMPARING options to make a decision?
├─ YES → [[Needs Research]]
└─ NO → Continue

Am I LEARNING from content I've consumed or found?
├─ YES → [[Needs Synthesis]]
└─ NO → Probably doesn't need a tag
```

---

## Command and Skill Locations

### Main Orchestrator
```
.claude/commands/knowledge/enrich.md
```

### Handler Skills
```
.claude/skills/knowledge/handlers/
├── synthesis-handler.md        # [[Needs Synthesis]] processing
├── research-handler.md         # [[Needs Research]] processing
├── handy-plan-handler.md       # [[Needs Handy Plan]] processing
└── book-recommendation-handler.md  # [[Book Recommendation]] processing
```

### Legacy Commands (Deprecated)
The following commands still exist but should be considered deprecated in favor of `/knowledge/enrich`:
```
.claude/commands/knowledge/
├── process-needs-synthesis.md      # Use: /knowledge/enrich --only synthesis
├── process-needs-research.md       # Use: /knowledge/enrich --only research
├── process-needs-handy-plan.md     # Use: /knowledge/enrich --only handy-plan
└── process-book-recommendations.md # Use: /knowledge/enrich --only book
```

### Related Commands (Still Active)
```
.claude/commands/knowledge/
├── maintain.md                 # Higher-level orchestration
├── synthesize-knowledge.md     # Single-topic synthesis
├── validate-links.md           # Link health checking
├── identify-unlinked-concepts.md  # Concept detection
└── expand-missing-topics.md    # Missing page creation
```

---

## Usage

### Primary Usage: Process All Tags

```bash
# Process all enrichment tags from last week (default)
/knowledge/enrich

# Process today's tags only
/knowledge/enrich today

# Process entire month
/knowledge/enrich month

# Process all historical tags
/knowledge/enrich all
```

### Filtered Processing

```bash
# Only process synthesis tags
/knowledge/enrich week --only synthesis

# Only process book recommendations
/knowledge/enrich --only book

# Only process handy plans from today
/knowledge/enrich today --only handy-plan
```

### Integration with Maintain

The `/knowledge/maintain` command can be updated to use `/knowledge/enrich` as part of its workflow:

```bash
# Full maintenance workflow
/knowledge/maintain week comprehensive
# Internally calls: /knowledge/enrich week
# Then: /knowledge/identify-unlinked-concepts
# Then: /knowledge/validate-links
```

---

## Output Architecture

### Hub/Spoke Model (Synthesis)

```
Daily Hub (Knowledge Synthesis - YYYY-MM-DD.md)
├─ Brief Summary 1 (30-80 words) → [[Topic Zettel 1]]
├─ Brief Summary 2 (30-80 words) → [[Topic Zettel 2]]
└─ Brief Summary 3 (30-80 words) → [[Topic Zettel 3]]

Topic Zettels (Comprehensive Content)
├─ Topic Zettel 1.md (500-2000+ words)
├─ Topic Zettel 2.md (500-2000+ words)
└─ Topic Zettel 3.md (500-2000+ words)
```

### Research Output Model

```
Comparison Zettel (e.g., "Message Broker Comparison.md")
├─ Comparison matrix
├─ Individual analysis sections
├─ Recommendations by use case
└─ Links to individual product pages

Individual Product Zettels
├─ Product A.md (features, pricing, pros/cons)
├─ Product B.md (features, pricing, pros/cons)
└─ Product C.md (features, pricing, pros/cons)
```

### Project Plan Model

```
Project Plan Zettel (e.g., "Kitchen Faucet Repair.md")
├─ Overview (difficulty, time, cost)
├─ Safety Brief
├─ Tools List
├─ Materials List (with costs)
├─ Step-by-Step Instructions
├─ Quality Control Checklist
└─ When to Call Professional
```

### Book Model

```
Book Zettel (e.g., "Deep Work.md")
├─ Overview (author, publication info)
├─ Synopsis
├─ Why Read This
├─ Key Topics
├─ Audiobook Info
├─ Recommendation Source
└─ Related Books

Book-Sync Entry
└─ books/unified/[id].yaml
```

---

## Quality Standards by Tag

### [[Needs Synthesis]]
- **Daily hub section**: 30-80 words MAX, 2+ wiki links
- **Topic zettel**: 500+ words, 3+ sources, all sections complete
- **Validation**: Hub word count enforced, topic completeness checked

### [[Needs Research]]
- **Research zettel**: 200+ words (300+ for complex topics)
- **Sources**: 3+ cited with URLs
- **Recommendations**: Clear and actionable
- **Comparison matrix**: Required for multi-option evaluations

### [[Needs Handy Plan]]
- **Project plan**: 500+ words minimum
- **Required sections**: Safety, Tools, Materials, Steps, Cost
- **Safety emphasis**: Must be prominent and complete
- **Cost estimates**: DIY vs Professional comparison

### [[Book Recommendation]]
- **Book zettel**: Synopsis, audiobook info, recommendation source
- **Book-sync entry**: Complete YAML with all metadata
- **ISBN**: At least one captured (or noted unavailable)
- **Author**: Wiki-linked, page created if needed

---

## Tag Cleanup Transformations

The orchestrator applies consistent transformations after successful processing:

| Tag Type | Before | After |
|----------|--------|-------|
| `[[Needs Synthesis]]` | `- Topic [[Needs Synthesis]]` | `- Synthesized [[Topic Page]] - see [[Knowledge Synthesis - YYYY-MM-DD]]` |
| `[[Needs Research]]` | `- Research X [[Needs Research]]` | `- Researched X - see [[Research Zettel]] [[Researched YYYY-MM-DD]]` |
| `[[Needs Handy Plan]]` | `- Fix X [[Needs Handy Plan]]` | `- Created plan for [[X Project]] [[Planned YYYY-MM-DD]]` |
| `[[Book Recommendation]]` | `- "Book" by Author [[Book Recommendation]]` | `- Added [[Book Title]] to library [[Added YYYY-MM-DD]]` |

**Transformation Rules**:
1. **REMOVE** enrichment tag entirely
2. **ADD** wiki link to created page(s)
3. **ADD** completion date marker
4. **TRANSFORM** verb tense to past (Need to → Researched)
5. **PRESERVE** nested content below entry

---

## Error Handling

### Entry-Level Errors

| Issue | Handling |
|-------|----------|
| Vague entry | Mark failed, request more details |
| Section header tagged | Skip (organizational, not actionable) |
| URL inaccessible | Try search fallback, mark partial if still fails |
| Missing information | Best-effort processing, note gaps |
| Duplicate entry | Process first, mark others as duplicates |

### Handler-Level Errors

| Issue | Handling |
|-------|----------|
| Handler skill missing | Log warning, skip tag type, report |
| Handler failure | Log error, mark entry failed, continue |
| Multiple consecutive failures | Pause after 5, report status, allow user decision |

### Recovery

If processing is interrupted:
```bash
# Simply re-run - only unprocessed entries will be found
/knowledge/enrich [scope] [--only type]
```

---

## Extension Guide: Adding New Tag Types

### Step 1: Define Semantics
- What does this tag mean?
- When should users apply it?
- What output should it produce?
- What quality standards apply?

### Step 2: Create Handler Skill
Create `.claude/skills/knowledge/handlers/[new-tag]-handler.md` with:
- Semantic definition
- Processing logic steps
- Output structure templates
- Validation checklist
- Return format
- Error handling

### Step 3: Update Orchestrator
In `/knowledge/enrich.md`:
1. Add tag pattern to discovery grep commands
2. Add entry in tag types table
3. Add handler dispatch case
4. Add cleanup transformation pattern
5. Add section in completion report

### Step 4: Update Documentation
In this file:
1. Add semantic definition
2. Add to decision tree
3. Add quality standards
4. Add output model
5. Add cleanup transformation

---

## Migration from Legacy Commands

### Before (One Command Per Tag)
```bash
/knowledge/process-needs-synthesis
/knowledge/process-needs-research
/knowledge/process-needs-handy-plan
/knowledge/process-book-recommendations
```

### After (Single Orchestrator)
```bash
# Process all
/knowledge/enrich

# Filter to specific type
/knowledge/enrich --only synthesis
/knowledge/enrich --only research
/knowledge/enrich --only handy-plan
/knowledge/enrich --only book
```

### Migration Steps
1. The new architecture is immediately usable
2. Legacy commands remain for backward compatibility
3. Gradually transition to `/knowledge/enrich`
4. Legacy commands may be removed in future

### What Changed
- **Discovery**: Now unified across all tags
- **Cleanup**: Consistent transformation patterns
- **Reporting**: Single comprehensive report
- **Error handling**: Centralized, graceful failures
- **Extensibility**: Add new tags without modifying core orchestration

---

## Summary

The knowledge processing system provides:

1. **Single Entry Point** - One command to process all enrichment tags
2. **Specialized Handlers** - Deep domain knowledge in focused skill files
3. **Consistent Behavior** - Uniform discovery, cleanup, and reporting
4. **Clear Semantics** - Each tag has distinct purpose and output format
5. **Quality Standards** - Enforced requirements for each tag type
6. **Extensibility** - Easy to add new tag types
7. **Error Recovery** - Graceful handling, no cascading failures

The key insight is that each tag represents a different **relationship to knowledge**:
- **Synthesis**: Transforming consumed content into personal understanding
- **Research**: Evaluating options to make informed decisions
- **Handy Plan**: Preparing for physical action with detailed preparation
- **Book Recommendation**: Curating potential future learning sources
