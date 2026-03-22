---
title: Process Needs Handy Plan Entries
description: Finds journal entries marked with [[Needs Handy Plan]], generates comprehensive construction/house project plans with tools, parts, safety, and instructions, creates Logseq pages, and removes labels after success
arguments: []
tools: Read, Write, Edit, Glob, Grep, WebFetch, mcp__read-website-fast__read_website, mcp__brave-search__brave_web_search, TodoWrite
model: opus
---

# Process Needs Handy Plan Entries

**Command Purpose**: Systematically process all journal entries marked with `[[Needs Handy Plan]]` by:
1. Discovering and cataloging all pending handy plan entries
2. Researching best practices, safety requirements, tools, and materials
3. Creating comprehensive project plans as Logseq Zettelkasten pages
4. Adding journal entries documenting the planning work
5. Removing handy plan labels after successful processing
6. Generating completion report

**When to Use**: Tag entries with `[[Needs Handy Plan]]` when you have a construction, home improvement, repair, or DIY project that needs detailed planning before execution.

**Semantic Definition**:
> `[[Needs Handy Plan]]` = "I have a physical project that requires planning: tools, materials, safety considerations, step-by-step instructions, and cost estimates before I can execute it."

**Contrast with Other Tags**:
- `[[Needs Research]]`: For technology evaluations, product comparisons, or technical deep-dives
- `[[Needs Synthesis]]`: For learning from articles, papers, or books - creating evergreen knowledge
- `[[Book Recommendation]]`: For book recommendations to add to your reading list

---

## Core Methodology

### Phase 1: Discovery and Cataloging

**Objective**: Find all entries marked for handy plans and extract project details.

**Actions**:
1. **Search for handy plan markers**:
   ```bash
   grep -rn "[[Needs Handy Plan]]" ~/Documents/personal-wiki/logseq/journals/
   ```
   - Record file paths, line numbers, and content
   - Handle case variations

2. **Parse each entry**:
   - Extract project name and description
   - Capture surrounding context (3-5 lines before/after)
   - Identify project type (see Project Types below)
   - Note any specific constraints (budget, timeline, skill level)

3. **Categorize and prioritize**:
   - **High priority**: Safety-critical, urgent repairs, time-sensitive
   - **Medium priority**: Standard improvements with clear scope
   - **Low priority**: Nice-to-have projects, exploratory planning
   - **Requires clarification**: Vague descriptions, missing details

4. **Generate discovery report**:
   ```
   ## Handy Plan Queue Discovery

   **Total Entries Found**: [count]

   **High Priority** ([count]):
   - [Journal Date] - [Project Preview]

   **Medium Priority** ([count]):
   - [Journal Date] - [Project Preview]

   **Low Priority** ([count]):
   - [Journal Date] - [Project Preview]

   **Requires Clarification** ([count]):
   - [Journal Date] - [Issue]
   ```

**Project Types to Recognize**:

1. **Repair projects**:
   ```markdown
   - Fix leaking faucet in kitchen [[Needs Handy Plan]]
   ```

2. **Installation projects**:
   ```markdown
   - Install ceiling fan in bedroom [[Needs Handy Plan]]
   ```

3. **Renovation projects**:
   ```markdown
   - Remodel bathroom shower [[Needs Handy Plan]]
   ```

4. **Maintenance projects**:
   ```markdown
   - Annual HVAC maintenance checklist [[Needs Handy Plan]]
   ```

5. **Construction projects**:
   ```markdown
   - Build raised garden beds [[Needs Handy Plan]]
   ```

6. **Exterior projects**:
   ```markdown
   - Repoint brick stairs on front porch [[Needs Handy Plan]]
   ```

---

### Phase 2: Research and Planning

**Objective**: Conduct comprehensive research for each project to create detailed, actionable plans.

**Actions**:
For each entry in priority order:

1. **Research project requirements**:
   - Use Brave Search to find:
     - Best practices and recommended approaches
     - Safety requirements and code compliance
     - Tool requirements and alternatives
     - Material specifications and quantities
     - Common mistakes and how to avoid them
     - Time and cost estimates
   - Search patterns:
     ```
     "[project type] DIY guide"
     "[project] step by step tutorial"
     "[project] safety requirements"
     "[project] tools materials list"
     "[project] common mistakes"
     "building code [project type]"
     ```

2. **Assess skill requirements**:
   - Determine if project is DIY-appropriate
   - Identify when professional help is needed
   - Note any permit or inspection requirements

3. **Calculate costs**:
   - Materials with 10% overage
   - Tool purchase vs rental options
   - Professional comparison costs

**Success Criteria (per entry)**:
- Minimum 3-5 quality sources consulted
- Safety considerations identified
- Complete tools and materials list
- Realistic time and cost estimates
- Clear when to call a professional

---

### Phase 3: Zettel Creation

**Objective**: Create comprehensive project plan zettels as Logseq pages.

**Actions**:
For each project entry:

1. **Create project zettel** at:
   `/Users/tylerstapler/Documents/personal-wiki/logseq/pages/[Project Name].md`

2. **Use this structure**:

```markdown
# [Project Name]

## Overview
- **Difficulty**: [Beginner/Intermediate/Advanced]
- **Estimated Time**: [realistic estimate]
- **Estimated Cost**: $[DIY range] DIY vs $[Pro range] Professional
- **Project Type**: [Repair/Installation/Renovation/Maintenance/Construction]

[2-3 sentences describing the project and its purpose]

## Safety Brief

**Critical Warnings**:
- [Top hazards specific to this project]

**Required Safety Equipment**:
- [PPE and safety gear needed]

**Emergency Procedures**:
- [What to do if something goes wrong]

**When to Stop**:
- [Red flags indicating professional help needed]

**Code Compliance**:
- [Building codes or permits required]

## Tools List

**Essential Tools**:
- [Tool] - [specific type/size if relevant]

**Power Tools**:
- [Tool] - [rent/buy recommendation]

**Hand Tools**:
- [Tool]

**Safety Equipment**:
- [PPE item]

**Measurement/Layout**:
- [Measuring tools]

**Optional/Nice-to-Have**:
- [Tool that makes job easier]

## Materials List

**Primary Materials**:
| Item | Quantity | Size/Spec | Est. Cost | Where to Buy |
|------|----------|-----------|-----------|--------------|
| [Material] | [qty + 10%] | [spec] | $[cost] | [store] |

**Fasteners/Hardware**:
- [Item] - [quantity] - $[cost]

**Consumables**:
- [Item] - [quantity] - $[cost]

**Finishing Materials**:
- [Item] - [quantity] - $[cost]

## Pre-Work Preparation

**Site Preparation**:
- [Area prep steps]

**Utility Considerations**:
- [Any shutoffs needed]

**Permits/Inspections**:
- [Requirements]

**Weather Considerations**:
- [Best conditions, what to avoid]

**Timeline Planning**:
- [Multi-day considerations]

## Step-by-Step Instructions

### Phase 1: [Phase Name] (estimated time)

1. **[Action Description]**
   - [Detail about how to do it]
   - [Measurement or specification]
   - What to watch for: [critical points]
   - Expected result: [what success looks like]

2. **[Next Action]**
   - [Details]

**Quality Check**: [How to verify Phase 1 is correct]

### Phase 2: [Phase Name] (estimated time)

[Continue with remaining phases...]

## Quality Control & Inspection

**During Work**:
- [Checkpoints throughout project]

**Final Inspection**:
- [What to verify when complete]

**Testing**:
- [Functional tests if applicable]

**Common Issues**:
- [How to identify problems]

## Troubleshooting Guide

| Problem | Possible Causes | Solutions | Prevention |
|---------|-----------------|-----------|------------|
| [Issue] | [Why it happens] | [How to fix] | [How to avoid] |

## Cleanup & Disposal

**During Project**:
- [Managing waste and mess]

**Final Cleanup**:
- [Complete cleanup procedures]

**Disposal Requirements**:
- [How to dispose of materials properly]

**Tool Maintenance**:
- [Cleaning and storing tools]

## Maintenance & Follow-up

**Initial Curing/Settling**:
- [What to expect in first days/weeks]

**Regular Maintenance**:
- [Ongoing care required]

**Inspection Schedule**:
- [When to check on work]

**Expected Lifespan**:
- [How long this should last]

## Success Criteria Checklist

- [ ] [Structural/functional requirement]
- [ ] [Safety standard met]
- [ ] [Aesthetic requirement]
- [ ] [Cleanup complete]
- [ ] [Passes inspection if required]

## When to Call a Professional

- [Complexity beyond DIY]
- [Code requirements]
- [Safety concerns]
- [Specialized equipment needed]
- [When pro is better value]

## Cost Breakdown

| Category | Estimate |
|----------|----------|
| Materials | $X - $Y |
| Tools (purchase) | $X - $Y |
| Tools (rental) | $X - $Y |
| Permits/Inspections | $X - $Y |
| **Total DIY** | **$X - $Y** |
| **Professional Cost** | **$X - $Y** |

## Sources
- [URL 1] - [description] (accessed YYYY-MM-DD)
- [URL 2] - [description] (accessed YYYY-MM-DD)

## Related
[[Home Improvement]] [[DIY]] #[[Project Type]]
```

3. **Add journal entry** to today's journal:
   ```markdown
   - **Project Planning**: Created comprehensive plan for [[Project Name]] #[[Home Improvement]] #[[Planning]]
     - Generated detailed guide covering safety, tools, materials, and step-by-step instructions
     - Estimated cost: $[DIY Cost Range] DIY vs $[Professional Cost Range] professional
     - Difficulty level: [Beginner/Intermediate/Advanced]
     - Estimated time: [Time Estimate]
     - Key considerations: [1-2 major decision points or challenges]
     - Next steps: [What should be done next]
   ```

**Success Criteria**:
- Project plan minimum 500 words
- Complete safety section
- Full tools and materials lists with costs
- Detailed step-by-step instructions
- Sources cited

---

### Phase 4: Label Management

**Objective**: Update processed entries by removing `[[Needs Handy Plan]]` markers.

**Actions**:
For each successfully processed entry:

1. **Transform the entry**:

   | Entry Type | Before | After |
   |------------|--------|-------|
   | Standard | `- Fix [project] [[Needs Handy Plan]]` | `- Created plan for [[Project Name]] - see comprehensive guide [[Planned YYYY-MM-DD]]` |
   | With notes | `- [Project] with [details] [[Needs Handy Plan]]` | `- [[Project Name]] - comprehensive plan created [[Planned YYYY-MM-DD]]` |

2. **Key transformation rules**:
   - **REMOVE** the `[[Needs Handy Plan]]` marker entirely
   - **ADD** link to created project plan `[[Project Name]]`
   - **ADD** completion marker `[[Planned YYYY-MM-DD]]`

3. **Verify edit success**:
   - Confirm file was modified
   - Re-read line to verify change

---

### Phase 5: Verification and Reporting

**Objective**: Confirm all processing completed successfully.

**Actions**:
1. **Verify label removal**:
   ```bash
   grep -rn "[[Needs Handy Plan]]" ~/Documents/personal-wiki/logseq/journals/
   ```

2. **Validate created plans**:
   - All referenced files exist
   - Each plan has required sections
   - Safety section present
   - Cost estimates included

3. **Generate completion report**:
   ```
   ## Handy Plan Processing Complete

   **Processing Summary**:
   - Total entries discovered: [count]
   - Successfully processed: [count]
   - Partial success: [count]
   - Failed: [count]

   **Project Plans Created**: [count]
   - [[Project 1]] (from [journal date])
     - Difficulty: [level]
     - Cost: $[range] DIY
   - [[Project 2]] (from [journal date])
     - Difficulty: [level]
     - Cost: $[range] DIY

   **Entries Requiring Manual Review**: [count]
   - [Journal date] - [Issue description]

   **Next Actions**:
   [List any entries needing clarification or follow-up]
   ```

---

## Usage Examples

### Example 1: Simple Repair Project
**Journal Content** (`2026_01_07.md`):
```markdown
- Fix dripping kitchen faucet [[Needs Handy Plan]]
```

**Processing**:
1. Discovery: 1 entry found (High priority - active leak)
2. Research: Faucet repair techniques, parts, tools
3. Plan created: `[[Kitchen Faucet Repair]]`
4. Entry transformed

**Result**:
```markdown
- Created plan for [[Kitchen Faucet Repair]] - comprehensive repair guide [[Planned 2026-01-07]]
```

### Example 2: Complex Construction Project
**Journal Content** (`2026_01_07.md`):
```markdown
- Build a raised garden bed system in backyard [[Needs Handy Plan]]
  - Want 3 beds, 4x8 feet each
  - Need to consider drainage
```

**Processing**:
1. Discovery: 1 entry with specifications (Medium priority)
2. Research: Raised bed construction, materials, drainage solutions
3. Plan created: `[[Raised Garden Bed System]]`
4. Entry transformed with context preserved

---

## Quality Standards

All processing must satisfy:

1. **Safety Focus**:
   - Safety section is comprehensive and prominent
   - PPE requirements clearly listed
   - Emergency procedures included
   - Professional thresholds documented

2. **Completeness**:
   - All tools listed with specifications
   - Materials include 10% overage
   - Step-by-step instructions are actionable
   - Cost estimates are realistic

3. **Actionability**:
   - Plan can be followed without additional research
   - Measurements and specifications are precise
   - Quality checkpoints are clear
   - Success criteria defined

---

## Error Handling

### Vague Project Description
**Pattern**: "Fix stuff around house"
**Handling**: Add `#needs-clarification` tag, request specific project details.

### Safety-Critical Projects
**Pattern**: Electrical, gas, structural work
**Handling**: Emphasize professional consultation, include detailed safety warnings, note permit requirements.

### Budget Constraints
**Pattern**: User mentions budget limit
**Handling**: Prioritize cost-effective approaches, include rental options, note where to save vs splurge.

---

## Command Invocation

**Format**: `/knowledge/process-needs-handy-plan`

**Arguments**: None (processes all pending entries)

**Expected Duration**: 5-15 minutes per project

**Prerequisites**:
- Brave Search accessible
- Web tools functional

**Post-Execution**:
- Review completion report
- Address any entries requiring clarification
- Verify new project plans are complete
