---
title: Process Needs Research Entries
description: Finds journal entries marked with [[Needs Research]], discovers and incorporates child topic pages, conducts research for projects or products, creates comprehensive zettels with hierarchical awareness, removes labels after success
arguments: []
tools: Read, Write, Edit, Glob, Grep, WebFetch, mcp__read-website-fast__read_website, mcp__brave-search__brave_web_search, TodoWrite
model: opus
---

# Process Needs Research Entries

**Command Purpose**: Systematically process all journal entries marked with `[[Needs Research]]` by:
1. Discovering and cataloging all pending research entries
2. Discovering existing child topic pages for hierarchical context
3. Conducting comprehensive research using web search and analysis
4. Incorporating child topic insights into research findings
5. Creating detailed zettels with findings, comparisons, and recommendations
6. Establishing hierarchical page structures when appropriate
7. Removing research labels after successful processing
8. Verifying child topic integration and generating completion report

**When Invoked**: This command performs direct research and synthesis (unlike process-needs-synthesis which delegates to an agent).

---

## Core Methodology

### Phase 1: Discovery and Cataloging

**Objective**: Find all entries marked for research and extract actionable items.

**Actions**:
1. **Search for research markers**:
   ```bash
   grep -rn "[[Needs Research]]" ~/Documents/personal-wiki/logseq/journals/
   ```
   - Record file paths, line numbers, and content
   - Handle case variations: `[[needs research]]`, `[[Needs Research]]`
   - Check both uppercase and lowercase patterns

2. **Parse each entry**:
   - Extract project name or product type from the line
   - Capture surrounding context (3-5 lines before/after for context)
   - Identify entry type (see Entry Types below)
   - Note any specific requirements, constraints, or criteria

3. **Categorize and prioritize**:
   - **High priority**: Explicit "urgent", "important", upcoming deadlines
   - **Medium priority**: Standard projects/products with clear criteria
   - **Low priority**: Exploratory research, long-term planning
   - **Requires clarification**: Vague requests, missing criteria, ambiguous goals

3.5. **Discover child topic pages** (NEW - CRITICAL):

   For each topic identified in research entries:

   **Check filesystem for child pages**:
   ```bash
   # Check if topic has a child pages directory
   ls -la "/storage/emulated/0/personal-wiki/logseq/pages/[Topic Name]/" 2>/dev/null

   # Example: Check for Kubernetes child pages
   ls -la "/storage/emulated/0/personal-wiki/logseq/pages/Kubernetes/" 2>/dev/null
   ```

   **Search for namespaced wiki link references**:
   ```bash
   # Find all namespaced references to the topic
   grep -r "\[\[Topic Name/" /storage/emulated/0/personal-wiki/logseq/pages/ 2>/dev/null

   # Example: Find all Kubernetes subtopics
   grep -r "\[\[Kubernetes/" /storage/emulated/0/personal-wiki/logseq/pages/
   ```

   **Record child topic information**:
   - List of child page files found
   - Namespaced references discovered
   - Existing knowledge to incorporate into research

4. **Generate discovery report**:
   ```
   ## Research Queue Discovery

   **Total Entries Found**: [count]

   **High Priority** ([count]):
   - [Journal Date] - [Entry Preview] - [Research Topic]
     - Child topics found: [count] (e.g., [[Topic/Subtopic1]], [[Topic/Subtopic2]])

   **Medium Priority** ([count]):
   - [Journal Date] - [Entry Preview] - [Research Topic]
     - Child topics found: [count]

   **Low Priority** ([count]):
   - [Journal Date] - [Entry Preview] - [Research Topic]
     - Child topics found: [count]

   **Requires Clarification** ([count]):
   - [Journal Date] - [Entry Preview] - [Issue]

   **Child Topic Summary**:
   - Topics with existing child pages: [count]
   - Total child pages discovered: [count]
   - Child page content to incorporate: [list]
   ```

**Success Criteria**:
- All `[[Needs Research]]` markers found and recorded
- Each entry categorized by type and priority
- Research topics/criteria extracted successfully
- **Child topic pages discovered for each topic** (NEW)
- Discovery report generated with counts and child topic information

**Entry Types to Recognize**:

1. **Project research**:
   ```markdown
   - Need to research best practices for implementing event sourcing in microservices [[Needs Research]]
   ```

2. **Product comparison**:
   ```markdown
   - Looking for a good password manager for the team [[Needs Research]]
   ```

3. **Technology evaluation**:
   ```markdown
   - Compare Kafka vs Pulsar vs RabbitMQ for our use case [[Needs Research]]
   ```

4. **Tool/service search**:
   ```markdown
   - Find a good CI/CD platform that supports monorepos [[Needs Research]]
   ```

5. **Problem investigation**:
   ```markdown
   - Research why our PostgreSQL queries are slow [[Needs Research]]
   ```

6. **Section header** (NOT actionable):
   ```markdown
   ## Research Queue [[Needs Research]]
   ```
   → **Skip**: Section headers are organizational, not research targets

7. **Nested items**:
   ```markdown
   - Project infrastructure decisions:
     - Database selection [[Needs Research]]
     - Message broker evaluation [[Needs Research]]
   ```
   → **Process**: Each nested item separately

8. **Topic with known child pages** (NEW):
   ```markdown
   - Need to research Kubernetes deployment strategies [[Needs Research]]
   ```
   → **Check for**: `Kubernetes/Pods.md`, `Kubernetes/Services.md`, `Kubernetes/Deployments.md`, etc.
   → **Action**: Read child pages and incorporate existing knowledge into research

---

### Phase 2: Research and Analysis

**Objective**: Conduct comprehensive research for each entry using available tools.

**Actions**:
For each entry in priority order:

1. **Analyze research requirements**:
   - Identify key questions to answer
   - Determine evaluation criteria (cost, features, performance, etc.)
   - Note any constraints (budget, timeline, technical requirements)
   - Extract specific use case or context

1.5. **Read and incorporate child topic pages** (NEW - CRITICAL):

   If child pages were discovered in Phase 1:

   **Read child page content**:
   ```bash
   # Read each discovered child page
   cat "/storage/emulated/0/personal-wiki/logseq/pages/[Topic]/[Subtopic].md"
   ```

   **Extract existing knowledge**:
   - Note what's already documented about the topic
   - Identify gaps in existing knowledge
   - Find connections to research questions
   - Determine what new research adds to existing content

   **Integration strategy**:
   - Build upon existing knowledge (don't duplicate)
   - Address gaps identified in child pages
   - Create connections between new research and existing pages
   - Consider whether to update existing child pages or create new ones

2. **Conduct multi-source research**:

   **For Product/Tool Research**:
   - Use Brave Search to find:
     - Product comparisons and reviews
     - Official documentation and pricing
     - User experiences and case studies
     - Alternative solutions
   - Search patterns:
     ```
     "[product name] vs alternatives"
     "best [tool category] for [use case]"
     "[product] review [year]"
     "[product] pricing comparison"
     ```

   **For Project/Technical Research**:
   - Use Brave Search to find:
     - Best practices and patterns
     - Architecture examples
     - Common pitfalls and solutions
     - Performance considerations
   - Search patterns:
     ```
     "[technology] best practices"
     "[pattern] implementation guide"
     "[problem] solution"
     "how to [accomplish goal]"
     ```

   **For Technology Comparison**:
   - Create comparison matrix with:
     - Core features
     - Performance characteristics
     - Complexity/learning curve
     - Community support
     - Cost considerations
     - Use case fit

3. **Deep dive with Puppeteer** (when needed):
   - Navigate to official websites for detailed information
   - Screenshot key feature pages
   - Extract pricing information
   - Review documentation structure
   - Capture product demos or examples

4. **Synthesize findings**:
   - Summarize research results
   - Create comparison tables/matrices
   - Identify top recommendations
   - Note trade-offs and considerations
   - Provide implementation guidance

**Success Criteria (per entry)**:
- Minimum 3-5 quality sources consulted
- Key questions answered comprehensively
- Clear recommendations provided
- Trade-offs and considerations documented
- Sources properly cited with URLs and dates
- **Child topic pages read and incorporated** (NEW)
- **Existing knowledge gaps identified and addressed** (NEW)
- **Child pages referenced in research zettel** (NEW)

**Research Quality Standards**:

1. **Breadth**: Cover multiple perspectives and sources
2. **Depth**: Go beyond surface-level information
3. **Recency**: Prioritize recent information (last 1-2 years)
4. **Relevance**: Focus on specific use case and requirements
5. **Actionability**: Provide clear next steps or recommendations
6. **Context awareness**: Build upon existing child page knowledge (NEW)
7. **Hierarchical integration**: Link parent and child topics appropriately (NEW)

---

### Phase 3: Zettel Creation

**Objective**: Create comprehensive zettels documenting research findings.

**Actions**:
For each research entry:

1. **Determine zettel structure**:

   **For Product/Tool Research**:
   ```markdown
   # [Product/Tool Name]

   ## Overview
   [Brief description, purpose, key value proposition]

   ## Key Features
   - Feature 1: [description]
   - Feature 2: [description]

   ## Pricing
   [Pricing tiers, costs, free options]

   ## Alternatives
   - [[Alternative 1]] - [comparison point]
   - [[Alternative 2]] - [comparison point]

   ## Pros
   - [advantage]

   ## Cons
   - [limitation]

   ## Use Cases
   - Best for: [scenario]
   - Not ideal for: [scenario]

   ## Recommendation
   [Clear recommendation with reasoning]

   ## Sources
   - [URL 1] - [description] (accessed YYYY-MM-DD)
   - [URL 2] - [description] (accessed YYYY-MM-DD)

   ## Child Topics
   - [[Product/Subtopic 1]] - [Brief description, if child page exists or was created]
   - [[Product/Subtopic 2]] - [Brief description, if child page exists or was created]

   ## Related
   [[Tag 1]] [[Tag 2]] [[Related Concept]]
   ```

   **For Project/Technical Research**:
   ```markdown
   # [Topic/Pattern Name]

   ## Overview
   [What it is, why it matters]

   ## Key Concepts
   - Concept 1: [explanation]
   - Concept 2: [explanation]

   ## Best Practices
   1. [practice]: [reasoning]
   2. [practice]: [reasoning]

   ## Common Pitfalls
   - [pitfall]: [how to avoid]

   ## Implementation Approach
   [Step-by-step guidance or architecture overview]

   ## Examples
   [Code snippets, architecture diagrams, real-world examples]

   ## Performance Considerations
   [Scalability, efficiency, resource usage]

   ## When to Use
   - Good fit: [scenario]
   - Poor fit: [scenario]

   ## Sources
   - [URL 1] - [description] (accessed YYYY-MM-DD)
   - [URL 2] - [description] (accessed YYYY-MM-DD)

   ## Child Topics
   - [[Topic/Subtopic 1]] - [Brief description, if child page exists or was created]
   - [[Topic/Subtopic 2]] - [Brief description, if child page exists or was created]

   ## Related
   [[Tag 1]] [[Tag 2]] [[Related Concept]]
   ```

   **For Comparison Research**:
   ```markdown
   # [Technology A] vs [Technology B] vs [Technology C]

   ## Comparison Matrix
   | Feature | Tech A | Tech B | Tech C |
   |---------|--------|--------|--------|
   | Performance | [rating/detail] | [rating/detail] | [rating/detail] |
   | Complexity | [rating/detail] | [rating/detail] | [rating/detail] |
   | Cost | [rating/detail] | [rating/detail] | [rating/detail] |

   ## Detailed Analysis

   ### [[Technology A]]
   - Strengths: [list]
   - Weaknesses: [list]
   - Best for: [use case]

   ### [[Technology B]]
   - Strengths: [list]
   - Weaknesses: [list]
   - Best for: [use case]

   ## Recommendation
   - For [use case]: Choose [[Technology X]] because [reasoning]
   - For [different use case]: Choose [[Technology Y]] because [reasoning]

   ## Sources
   - [URL 1] - [description] (accessed YYYY-MM-DD)

   ## Related
   [[Tag 1]] [[Tag 2]]
   ```

2. **Create zettel files**:
   - Use appropriate naming: `logseq/pages/[Topic Name].md`
   - Ensure proper Logseq format
   - Include bidirectional links
   - Add relevant tags

3. **Link from journal entry**:
   ```markdown
   OLD: - Need to research [topic] [[Needs Research]]
   NEW: - Researched [topic] → [[Topic Name]] [[Researched on YYYY-MM-DD]]
   ```

4. **Create comparison pages** (for product/tech comparisons):
   - Main comparison zettel
   - Individual product/tech zettels
   - Cross-link all related zettels

**Success Criteria**:
- Minimum 200 words per zettel (300+ for complex topics)
- At least 3 cited sources
- Clear structure with headers
- Bidirectional links established
- Actionable recommendations provided

---

### Phase 4: Label Management

**Objective**: Update processed entries by completely removing `[[Needs Research]]` markers and transforming entries to indicate completion.

**Actions**:
For each successfully processed entry:

1. **Locate exact line** in journal file:
   - Use grep result (file path + line number) from Phase 1
   - Read file to confirm line still matches expected content
   - Verify no manual edits occurred during processing

2. **Transform the entry** (COMPLETE REPLACEMENT - no strikethrough):

   **Pattern: Transform verb tense AND remove marker entirely**

   | Entry Type | Before | After |
   |------------|--------|-------|
   | Standard | `- Need to research [topic] [[Needs Research]]` | `- Researched [topic] - see [[Topic Zettel]] [[Researched YYYY-MM-DD]]` |
   | Product search | `- Looking for a good [product] [[Needs Research]]` | `- Evaluated [product] options - see [[Product Comparison]] [[Researched YYYY-MM-DD]]` |
   | Comparison | `- Compare [A] vs [B] [[Needs Research]]` | `- Compared [A] vs [B] - see [[A vs B Comparison]] [[Researched YYYY-MM-DD]]` |
   | Investigation | `- Research why [problem] [[Needs Research]]` | `- Investigated [problem] - see [[Problem Analysis]] [[Researched YYYY-MM-DD]]` |
   | Thinking/Considering | `- Thinking about [topic] [[Needs Research]]` | `- Researched [topic] - see [[Topic Zettel]] [[Researched YYYY-MM-DD]]` |

   **Key transformation rules**:
   - **REMOVE** the `[[Needs Research]]` marker entirely (NO strikethrough)
   - **CHANGE** verb to past tense ("Need to research" -> "Researched")
   - **ADD** link to created zettel with "- see [[Zettel Name]]"
   - **ADD** completion marker `[[Researched YYYY-MM-DD]]`
   - **NEST** supporting details (URLs, notes) as sub-bullets

3. **Use Edit tool** for precise replacement:
   - Match entire line content (not just marker) for safety
   - Preserve indentation and formatting
   - Handle special characters correctly
   - Transform verb tense as part of the edit

4. **Verify edit success**:
   - Confirm file was modified
   - Re-read line to verify change
   - Ensure `[[Needs Research]]` is completely gone (not just struck through)
   - Verify new completion marker present

**Why Complete Removal (NOT Strikethrough)**:
- **Discovery efficiency**: `grep "[[Needs Research]]"` returns ONLY unprocessed entries
- **Clean journals**: No visual clutter from `~~[[Needs Research]]~~`
- **Clear status**: Entry wording itself indicates completion (past tense)
- **Traceability**: `[[Researched YYYY-MM-DD]]` provides audit trail

**Success Criteria**:
- All successful entries have `[[Needs Research]]` completely removed
- Verb tense transformed to past tense
- Links to research zettels added
- Completion date marker present
- No content loss or corruption
- File integrity maintained
- All edits validated

---

### Phase 5: Verification and Reporting

**Objective**: Confirm all processing completed successfully and generate comprehensive report.

**Actions**:
1. **Verify label removal**:
   ```bash
   # Confirm no [[Needs Research]] labels remain (except failures)
   grep -rn "[[Needs Research]]" ~/Documents/personal-wiki/logseq/journals/
   ```
   - Expected: Only entries marked as "Needs Manual Review"
   - If unexpected labels found, investigate and report

2. **Validate created zettels**:
   - All referenced files exist in pages directory
   - Each zettel has minimum content (200+ words)
   - Links are properly formatted and functional
   - Sources cited (minimum 3)
   - Recommendations are clear and actionable
   - **Child Topics section present if child pages exist** (NEW)

3. **Validate child topic integration** (NEW - CRITICAL):

   For each topic that had child pages discovered:

   **Child Page Discovery Verification**:
   ```bash
   # Re-check child pages exist
   ls -la "/storage/emulated/0/personal-wiki/logseq/pages/[Topic Name]/" 2>/dev/null
   ```

   **Child Topic Content Integration Verification**:
   - Read the created research zettel
   - Verify it references child pages in "Child Topics" section
   - Check for `[[Topic/Subtopic]]` style links
   - Confirm research builds upon existing child page knowledge

   **Bidirectional Link Verification**:
   - Verify parent page links to child pages
   - Verify child pages link back to parent (if updated)

   **Validation Criteria**:
   - **FAIL if**: Topic had child pages but research doesn't reference them
   - **PASS if**: Child pages are linked and their content informed the research

4. **Check knowledge base integration**:
   - New zettels linked from journal entries
   - Bidirectional links established
   - Comparison pages properly cross-linked
   - No broken references introduced
   - **Parent-child page relationships established** (NEW)

5. **Generate completion report**:
   ```
   ## Research Processing Complete

   **Processing Summary**:
   - Total entries discovered: [count]
   - Successfully processed: [count]
   - Partial success: [count]
   - Failed: [count]
   - Skipped (section headers): [count]

   **Research Zettels Created**: [count]
   - [[Research Topic 1]] (from [journal date])
   - [[Research Topic 2]] (from [journal date])

   **Comparison Pages Created**: [count]
   - [[Tech A vs Tech B vs Tech C]]
   - [[Product Comparison: Category]]

   **Child Topic Integration** (NEW):
   - Topics with existing child pages: [count]
   - Total child pages discovered: [count]
   - Child pages read and incorporated: [count]
   - New child pages created: [count]
   - Parent-child links established: [count]

   **Child Topics Processed**:
   - [[Parent Topic]]
     - [[Parent Topic/Child 1]] - incorporated into research
     - [[Parent Topic/Child 2]] - incorporated into research
   - [[Another Parent]]
     - [[Another Parent/Subtopic]] - new child page created

   **Entries Requiring Manual Review**: [count]
   - [Journal date] - [Issue description]

   **Verification**:
   - Labels updated: ✓ [count]
   - Files created successfully: ✓ [count]
   - Links validated: ✓
   - Sources cited (min 3 per entry): ✓
   - No broken references: ✓
   - **Child topics integrated**: ✓ [count] (NEW)

   **Next Actions**:
   [If any entries need manual review, list them here]
   ```

**Success Criteria**:
- Completion report generated with all metrics
- All successful entries verified
- Failed entries documented with reasons
- User provided clear next actions

---

## Usage Examples

### Example 1: Product Research (Password Manager)
**Journal Content** (`2025_10_15.md`):
```markdown
- Need to find a good password manager for the engineering team [[Needs Research]]
  - Must support: SSO, team sharing, audit logs
  - Budget: Up to $10/user/month
```

**Command**: `/knowledge:process-needs-research`

**Processing**:
1. Discovery: 1 entry found (Medium priority)
2. Research conducted:
   - Brave Search: "best password manager for teams 2025"
   - Brave Search: "1Password vs Bitwarden vs LastPass enterprise"
   - Puppeteer: Visit official sites for pricing
3. Zettels created:
   - `[[1Password]]` - Full feature review
   - `[[Bitwarden]]` - Full feature review
   - `[[LastPass]]` - Full feature review
   - `[[Password Manager Comparison for Teams]]` - Comparison matrix
4. Recommendation: 1Password for ease of use, Bitwarden for cost
5. Entry transformed (marker removed, verb changed)

**Result**:
```markdown
- Evaluated password managers - see [[Password Manager Comparison for Teams]] [[Researched 2025-10-15]]
  - Recommendation: [[1Password]] (best UX) or [[Bitwarden]] (best value)
  - Must support: SSO, team sharing, audit logs
  - Budget: Up to $10/user/month
```

---

### Example 2: Technical Research (Event Sourcing)
**Journal Content** (`2025_10_20.md`):
```markdown
- Need to research event sourcing implementation for order processing service [[Needs Research]]
```

**Command**: `/knowledge:process-needs-research`

**Processing**:
1. Discovery: 1 entry (Medium priority)
2. Research conducted:
   - "event sourcing best practices"
   - "event sourcing microservices implementation"
   - "event sourcing pitfalls"
   - "event store comparison"
3. Zettel created: `[[Event Sourcing Implementation Guide]]`
   - Best practices section
   - Common pitfalls
   - Architecture patterns
   - Implementation steps
   - Tool recommendations (EventStore, Axon, etc.)
4. Entry transformed

**Result**:
```markdown
- Researched event sourcing for order processing - see [[Event Sourcing Implementation Guide]] [[Researched 2025-10-20]]
```

---

### Example 3: Technology Comparison
**Journal Content** (`2025_10_25.md`):
```markdown
- Compare message brokers: Kafka vs RabbitMQ vs Pulsar [[Needs Research]]
  - Need: High throughput, reliable delivery, easy operations
```

**Command**: `/knowledge:process-needs-research`

**Processing**:
1. Discovery: 1 entry (High priority - architectural decision)
2. Research conducted:
   - "Kafka vs RabbitMQ vs Pulsar comparison"
   - Performance benchmarks for each
   - Operational complexity analysis
   - Use case fit
3. Zettels created:
   - `[[Apache Kafka]]` - Detailed profile
   - `[[RabbitMQ]]` - Detailed profile
   - `[[Apache Pulsar]]` - Detailed profile
   - `[[Message Broker Comparison]]` - Full comparison matrix
4. Recommendation based on criteria
5. Entry transformed

**Result**:
```markdown
- Compared message brokers - see [[Message Broker Comparison]] [[Researched 2025-10-25]]
  - Recommendation: [[Apache Kafka]] for high throughput use case
  - Need: High throughput, reliable delivery, easy operations
```

---

### Example 4: Multiple Nested Research Items
**Journal Content** (`2025_10_30.md`):
```markdown
## Infrastructure Decisions [[Needs Research]]
- Database selection: [[Needs Research]]
  - PostgreSQL vs MySQL for high-write workload
- Monitoring stack: [[Needs Research]]
  - Prometheus vs Datadog vs New Relic
- Load balancer: [[Needs Research]]
```

**Command**: `/knowledge:process-needs-research`

**Processing**:
1. Discovery: 4 labels found
   - Line 1 (section header): Skip
   - Lines 2-4 (specific items): Process each
2. Research conducted for each:
   - Database comparison with write performance focus
   - Monitoring stack comparison
   - Load balancer options research
3. Zettels created:
   - `[[PostgreSQL vs MySQL for Write-Heavy Workloads]]`
   - `[[Monitoring Stack Comparison]]`
   - `[[Load Balancer Options]]`
4. All entries transformed

**Result**:
```markdown
## Infrastructure Decisions
- Evaluated databases - see [[PostgreSQL vs MySQL for Write-Heavy Workloads]] [[Researched 2025-10-30]]
  - PostgreSQL vs MySQL for high-write workload
  - Recommendation: [[PostgreSQL]] with tuned settings
- Evaluated monitoring stacks - see [[Monitoring Stack Comparison]] [[Researched 2025-10-30]]
  - Prometheus vs Datadog vs New Relic
  - Recommendation: [[Datadog]] for full-stack visibility
- Researched load balancers - see [[Load Balancer Options]] [[Researched 2025-10-30]]
  - Recommendation: [[HAProxy]] or cloud-native options
```

---

### Example 5: Insufficient Information (Needs Clarification)
**Journal Content** (`2025_11_01.md`):
```markdown
- Need to research CI/CD [[Needs Research]]
```

**Command**: `/knowledge:process-needs-research`

**Processing**:
1. Discovery: 1 entry (vague, needs clarification)
2. Attempt basic research:
   - Too broad to provide actionable recommendations
   - Need: use case, constraints, team size, etc.
3. Apply error handling:
   - Label changed to `#needs-clarification`
   - Add note requesting more context

**Result**:
```markdown
- Need to research CI/CD #needs-clarification
  - NOTE: Please add more context:
    - What is the use case? (e.g., monorepo, microservices)
    - What are your requirements? (e.g., speed, cost, integrations)
    - What is your team size and tech stack?
```

---

### Example 6: Appliance Repair with URL (Real Example)
**Journal Content** (`2026_01_05.md`):
```markdown
- Thinking about [[ETW4400WQ0 Washer Suspension Repair]] https://g.co/gemini/share/898a1f5ec14e [[Needs Research]]
```

**Command**: `/knowledge:process-needs-research`

**Processing**:
1. Discovery: 1 entry (Medium priority - home maintenance)
2. Research conducted:
   - "ETW4400WQ0 Estate washer suspension repair guide"
   - "top load washer suspension rod replacement DIY"
   - "Estate ETW4400WQ0 suspension spring parts numbers"
   - Website deep-dive: PartSelect.com for parts and diagrams
3. Zettel created: `[[ETW4400WQ0 Washer Suspension Repair]]`
   - Complete diagnosis guide for shaking issues
   - Part numbers and pricing (WP63907, ~$10-15)
   - Step-by-step repair instructions
   - Tool requirements
   - Cost comparison (DIY vs professional)
   - Video resources
4. Entry transformed with URL nested

**Result**:
```markdown
- Researched [[ETW4400WQ0 Washer Suspension Repair]] - see comprehensive repair guide with part numbers, step-by-step instructions, and cost comparison [[Researched 2026-01-05]]
  - Gemini conversation: https://g.co/gemini/share/898a1f5ec14e
```

**Notes**:
- URL moved to nested sub-bullet for cleaner main entry
- Verb changed from "Thinking about" to "Researched"
- `[[Needs Research]]` completely removed (no strikethrough)
- Completion date added as `[[Researched 2026-01-05]]`

---

## Quality Standards

All processing must satisfy:

1. **Discovery Completeness**:
   - All `[[Needs Research]]` labels found (case-insensitive)
   - Entries properly categorized by type and priority
   - Context and requirements extracted
   - No entries missed or skipped unintentionally

2. **Research Thoroughness**:
   - Minimum 3-5 quality sources per entry
   - Multiple perspectives considered
   - Recent information prioritized (within 1-2 years)
   - Specific use case and requirements addressed
   - Trade-offs clearly documented

3. **Zettel Quality**:
   - Minimum 200 words (300+ for complex topics)
   - Clear structure with appropriate headers
   - Actionable recommendations provided
   - Sources properly cited with URLs and access dates
   - Bidirectional links established

4. **Comparison Quality** (when applicable):
   - Comparison matrix with relevant criteria
   - Individual profiles for each option
   - Clear recommendations based on use cases
   - Trade-offs explicitly stated

5. **Label Management Accuracy**:
   - Only successful entries have labels updated
   - Failed entries clearly marked with reasons
   - No content corruption or loss
   - Links to research zettels added
   - All edits validated

6. **Reporting Completeness**:
   - All metrics included (counts, successes, failures)
   - Failed entries documented with reasons
   - Clear next actions provided
   - Verification checklist completed

---

## Error Handling

### Vague or Broad Request
**Pattern**: "Research CI/CD" without context
**Handling**: Add `#needs-clarification` tag, request specific requirements, preserve original entry.

### Insufficient Search Results
**Issue**: Cannot find quality information (niche topic, new technology)
**Handling**: Document limitation in zettel, note "limited information available as of [date]", mark for future re-research.

### Conflicting Information
**Issue**: Sources contradict each other
**Handling**: Document multiple perspectives, cite sources for each view, recommend further investigation or testing.

### Section Headers with Labels
**Pattern**: `## Research Queue [[Needs Research]]`
**Handling**: Skip processing (organizational). Optionally remove label if section is empty.

### Concurrent Edits
**Issue**: Journal file modified during processing
**Handling**: Re-read file before editing, verify line still matches, retry once if mismatch, report if persistent.

### Partial Research
**Issue**: Some questions answered, others remain unclear
**Handling**: Mark as "Partial", keep label with note "Requires additional research on [specific aspect]".

---

## Command Invocation

**Format**: `/knowledge:process-needs-research`

**Arguments**: None (processes all pending entries)

**Execution Mode**: Direct research and synthesis (no agent delegation)

**Tools Used**:
- Brave Search for multi-source research
- Puppeteer for deep dives into specific sites
- Analysis tools for data processing (if needed)

**Expected Duration**: 10-30 minutes depending on queue size (3-8 minutes per entry for thorough research)

**Prerequisites**:
- Brave Search accessible
- Web tools (Puppeteer) functional
- Internet connection stable

**Post-Execution**:
- Review completion report
- Address any entries requiring clarification
- Verify new zettels integrate properly
- Act on recommendations as appropriate
