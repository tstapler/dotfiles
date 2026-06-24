---
description: Finds journal entries marked with [[Needs Handy Plan]], generates comprehensive
  construction/house project plans with tools, parts, safety, and instructions, creates
  Logseq pages, and removes labels after success
prompt: "# Process Needs Handy Plan Entries\n\n**Command Purpose**: Systematically\
  \ process all journal entries marked with `[[Needs Handy Plan]]` by:\n1. Discovering\
  \ and cataloging all pending handy plan entries\n2. Researching best practices,\
  \ safety requirements, tools, and materials\n3. Creating comprehensive project plans\
  \ as Logseq Zettelkasten pages\n4. Adding journal entries documenting the planning\
  \ work\n5. Removing handy plan labels after successful processing\n6. Generating\
  \ completion report\n\n**When to Use**: Tag entries with `[[Needs Handy Plan]]`\
  \ when you have a construction, home improvement, repair, or DIY project that needs\
  \ detailed planning before execution.\n\n**Semantic Definition**:\n> `[[Needs Handy\
  \ Plan]]` = \"I have a physical project that requires planning: tools, materials,\
  \ safety considerations, step-by-step instructions, and cost estimates before I\
  \ can execute it.\"\n\n**Contrast with Other Tags**:\n- `[[Needs Research]]`: For\
  \ technology evaluations, product comparisons, or technical deep-dives\n- `[[Needs\
  \ Synthesis]]`: For learning from articles, papers, or books - creating evergreen\
  \ knowledge\n- `[[Book Recommendation]]`: For book recommendations to add to your\
  \ reading list\n\n---\n\n## Core Methodology\n\n### Phase 1: Discovery and Cataloging\n\
  \n**Objective**: Find all entries marked for handy plans and extract project details.\n\
  \n**Actions**:\n1. **Search for handy plan markers**:\n   ```bash\n   grep -rn \"\
  [[Needs Handy Plan]]\" ~/Documents/personal-wiki/logseq/journals/\n   ```\n   -\
  \ Record file paths, line numbers, and content\n   - Handle case variations\n\n\
  2. **Parse each entry**:\n   - Extract project name and description\n   - Capture\
  \ surrounding context (3-5 lines before/after)\n   - Identify project type (see\
  \ Project Types below)\n   - Note any specific constraints (budget, timeline, skill\
  \ level)\n\n3. **Categorize and prioritize**:\n   - **High priority**: Safety-critical,\
  \ urgent repairs, time-sensitive\n   - **Medium priority**: Standard improvements\
  \ with clear scope\n   - **Low priority**: Nice-to-have projects, exploratory planning\n\
  \   - **Requires clarification**: Vague descriptions, missing details\n\n4. **Generate\
  \ discovery report**:\n   ```\n   ## Handy Plan Queue Discovery\n\n   **Total Entries\
  \ Found**: [count]\n\n   **High Priority** ([count]):\n   - [Journal Date] - [Project\
  \ Preview]\n\n   **Medium Priority** ([count]):\n   - [Journal Date] - [Project\
  \ Preview]\n\n   **Low Priority** ([count]):\n   - [Journal Date] - [Project Preview]\n\
  \n   **Requires Clarification** ([count]):\n   - [Journal Date] - [Issue]\n   ```\n\
  \n**Project Types to Recognize**:\n\n1. **Repair projects**:\n   ```markdown\n \
  \  - Fix leaking faucet in kitchen [[Needs Handy Plan]]\n   ```\n\n2. **Installation\
  \ projects**:\n   ```markdown\n   - Install ceiling fan in bedroom [[Needs Handy\
  \ Plan]]\n   ```\n\n3. **Renovation projects**:\n   ```markdown\n   - Remodel bathroom\
  \ shower [[Needs Handy Plan]]\n   ```\n\n4. **Maintenance projects**:\n   ```markdown\n\
  \   - Annual HVAC maintenance checklist [[Needs Handy Plan]]\n   ```\n\n5. **Construction\
  \ projects**:\n   ```markdown\n   - Build raised garden beds [[Needs Handy Plan]]\n\
  \   ```\n\n6. **Exterior projects**:\n   ```markdown\n   - Repoint brick stairs\
  \ on front porch [[Needs Handy Plan]]\n   ```\n\n---\n\n### Phase 2: Research and\
  \ Planning\n\n**Objective**: Conduct comprehensive research for each project to\
  \ create detailed, actionable plans.\n\n**Actions**:\nFor each entry in priority\
  \ order:\n\n1. **Research project requirements**:\n   - Use Brave Search to find:\n\
  \     - Best practices and recommended approaches\n     - Safety requirements and\
  \ code compliance\n     - Tool requirements and alternatives\n     - Material specifications\
  \ and quantities\n     - Common mistakes and how to avoid them\n     - Time and\
  \ cost estimates\n   - Search patterns:\n     ```\n     \"[project type] DIY guide\"\
  \n     \"[project] step by step tutorial\"\n     \"[project] safety requirements\"\
  \n     \"[project] tools materials list\"\n     \"[project] common mistakes\"\n\
  \     \"building code [project type]\"\n     ```\n\n2. **Assess skill requirements**:\n\
  \   - Determine if project is DIY-appropriate\n   - Identify when professional help\
  \ is needed\n   - Note any permit or inspection requirements\n\n3. **Calculate costs**:\n\
  \   - Materials with 10% overage\n   - Tool purchase vs rental options\n   - Professional\
  \ comparison costs\n\n**Success Criteria (per entry)**:\n- Minimum 3-5 quality sources\
  \ consulted\n- Safety considerations identified\n- Complete tools and materials\
  \ list\n- Realistic time and cost estimates\n- Clear when to call a professional\n\
  \n---\n\n### Phase 3: Zettel Creation\n\n**Objective**: Create comprehensive project\
  \ plan zettels as Logseq pages.\n\n**Actions**:\nFor each project entry:\n\n1. **Create\
  \ project zettel** at:\n   `/Users/tylerstapler/Documents/personal-wiki/logseq/pages/[Project\
  \ Name].md`\n\n2. **Use this structure**:\n\n```markdown\n# [Project Name]\n\n##\
  \ Overview\n- **Difficulty**: [Beginner/Intermediate/Advanced]\n- **Estimated Time**:\
  \ [realistic estimate]\n- **Estimated Cost**: $[DIY range] DIY vs $[Pro range] Professional\n\
  - **Project Type**: [Repair/Installation/Renovation/Maintenance/Construction]\n\n\
  [2-3 sentences describing the project and its purpose]\n\n## Safety Brief\n\n**Critical\
  \ Warnings**:\n- [Top hazards specific to this project]\n\n**Required Safety Equipment**:\n\
  - [PPE and safety gear needed]\n\n**Emergency Procedures**:\n- [What to do if something\
  \ goes wrong]\n\n**When to Stop**:\n- [Red flags indicating professional help needed]\n\
  \n**Code Compliance**:\n- [Building codes or permits required]\n\n## Tools List\n\
  \n**Essential Tools**:\n- [Tool] - [specific type/size if relevant]\n\n**Power Tools**:\n\
  - [Tool] - [rent/buy recommendation]\n\n**Hand Tools**:\n- [Tool]\n\n**Safety Equipment**:\n\
  - [PPE item]\n\n**Measurement/Layout**:\n- [Measuring tools]\n\n**Optional/Nice-to-Have**:\n\
  - [Tool that makes job easier]\n\n## Materials List\n\n**Primary Materials**:\n\
  | Item | Quantity | Size/Spec | Est. Cost | Where to Buy |\n|------|----------|-----------|-----------|--------------|\n\
  | [Material] | [qty + 10%] | [spec] | $[cost] | [store] |\n\n**Fasteners/Hardware**:\n\
  - [Item] - [quantity] - $[cost]\n\n**Consumables**:\n- [Item] - [quantity] - $[cost]\n\
  \n**Finishing Materials**:\n- [Item] - [quantity] - $[cost]\n\n## Pre-Work Preparation\n\
  \n**Site Preparation**:\n- [Area prep steps]\n\n**Utility Considerations**:\n- [Any\
  \ shutoffs needed]\n\n**Permits/Inspections**:\n- [Requirements]\n\n**Weather Considerations**:\n\
  - [Best conditions, what to avoid]\n\n**Timeline Planning**:\n- [Multi-day considerations]\n\
  \n## Step-by-Step Instructions\n\n### Phase 1: [Phase Name] (estimated time)\n\n\
  1. **[Action Description]**\n   - [Detail about how to do it]\n   - [Measurement\
  \ or specification]\n   - What to watch for: [critical points]\n   - Expected result:\
  \ [what success looks like]\n\n2. **[Next Action]**\n   - [Details]\n\n**Quality\
  \ Check**: [How to verify Phase 1 is correct]\n\n### Phase 2: [Phase Name] (estimated\
  \ time)\n\n[Continue with remaining phases...]\n\n## Quality Control & Inspection\n\
  \n**During Work**:\n- [Checkpoints throughout project]\n\n**Final Inspection**:\n\
  - [What to verify when complete]\n\n**Testing**:\n- [Functional tests if applicable]\n\
  \n**Common Issues**:\n- [How to identify problems]\n\n## Troubleshooting Guide\n\
  \n| Problem | Possible Causes | Solutions | Prevention |\n|---------|-----------------|-----------|------------|\n\
  | [Issue] | [Why it happens] | [How to fix] | [How to avoid] |\n\n## Cleanup & Disposal\n\
  \n**During Project**:\n- [Managing waste and mess]\n\n**Final Cleanup**:\n- [Complete\
  \ cleanup procedures]\n\n**Disposal Requirements**:\n- [How to dispose of materials\
  \ properly]\n\n**Tool Maintenance**:\n- [Cleaning and storing tools]\n\n## Maintenance\
  \ & Follow-up\n\n**Initial Curing/Settling**:\n- [What to expect in first days/weeks]\n\
  \n**Regular Maintenance**:\n- [Ongoing care required]\n\n**Inspection Schedule**:\n\
  - [When to check on work]\n\n**Expected Lifespan**:\n- [How long this should last]\n\
  \n## Success Criteria Checklist\n\n- [ ] [Structural/functional requirement]\n-\
  \ [ ] [Safety standard met]\n- [ ] [Aesthetic requirement]\n- [ ] [Cleanup complete]\n\
  - [ ] [Passes inspection if required]\n\n## When to Call a Professional\n\n- [Complexity\
  \ beyond DIY]\n- [Code requirements]\n- [Safety concerns]\n- [Specialized equipment\
  \ needed]\n- [When pro is better value]\n\n## Cost Breakdown\n\n| Category | Estimate\
  \ |\n|----------|----------|\n| Materials | $X - $Y |\n| Tools (purchase) | $X -\
  \ $Y |\n| Tools (rental) | $X - $Y |\n| Permits/Inspections | $X - $Y |\n| **Total\
  \ DIY** | **$X - $Y** |\n| **Professional Cost** | **$X - $Y** |\n\n## Sources\n\
  - [URL 1] - [description] (accessed YYYY-MM-DD)\n- [URL 2] - [description] (accessed\
  \ YYYY-MM-DD)\n\n## Related\n[[Home Improvement]] [[DIY]] #[[Project Type]]\n```\n\
  \n3. **Add journal entry** to today's journal:\n   ```markdown\n   - **Project Planning**:\
  \ Created comprehensive plan for [[Project Name]] #[[Home Improvement]] #[[Planning]]\n\
  \     - Generated detailed guide covering safety, tools, materials, and step-by-step\
  \ instructions\n     - Estimated cost: $[DIY Cost Range] DIY vs $[Professional Cost\
  \ Range] professional\n     - Difficulty level: [Beginner/Intermediate/Advanced]\n\
  \     - Estimated time: [Time Estimate]\n     - Key considerations: [1-2 major decision\
  \ points or challenges]\n     - Next steps: [What should be done next]\n   ```\n\
  \n**Success Criteria**:\n- Project plan minimum 500 words\n- Complete safety section\n\
  - Full tools and materials lists with costs\n- Detailed step-by-step instructions\n\
  - Sources cited\n\n---\n\n### Phase 4: Label Management\n\n**Objective**: Update\
  \ processed entries by removing `[[Needs Handy Plan]]` markers.\n\n**Actions**:\n\
  For each successfully processed entry:\n\n1. **Transform the entry**:\n\n   | Entry\
  \ Type | Before | After |\n   |------------|--------|-------|\n   | Standard | `-\
  \ Fix [project] [[Needs Handy Plan]]` | `- Created plan for [[Project Name]] - see\
  \ comprehensive guide [[Planned YYYY-MM-DD]]` |\n   | With notes | `- [Project]\
  \ with [details] [[Needs Handy Plan]]` | `- [[Project Name]] - comprehensive plan\
  \ created [[Planned YYYY-MM-DD]]` |\n\n2. **Key transformation rules**:\n   - **REMOVE**\
  \ the `[[Needs Handy Plan]]` marker entirely\n   - **ADD** link to created project\
  \ plan `[[Project Name]]`\n   - **ADD** completion marker `[[Planned YYYY-MM-DD]]`\n\
  \n3. **Verify edit success**:\n   - Confirm file was modified\n   - Re-read line\
  \ to verify change\n\n---\n\n### Phase 5: Verification and Reporting\n\n**Objective**:\
  \ Confirm all processing completed successfully.\n\n**Actions**:\n1. **Verify label\
  \ removal**:\n   ```bash\n   grep -rn \"[[Needs Handy Plan]]\" ~/Documents/personal-wiki/logseq/journals/\n\
  \   ```\n\n2. **Validate created plans**:\n   - All referenced files exist\n   -\
  \ Each plan has required sections\n   - Safety section present\n   - Cost estimates\
  \ included\n\n3. **Generate completion report**:\n   ```\n   ## Handy Plan Processing\
  \ Complete\n\n   **Processing Summary**:\n   - Total entries discovered: [count]\n\
  \   - Successfully processed: [count]\n   - Partial success: [count]\n   - Failed:\
  \ [count]\n\n   **Project Plans Created**: [count]\n   - [[Project 1]] (from [journal\
  \ date])\n     - Difficulty: [level]\n     - Cost: $[range] DIY\n   - [[Project\
  \ 2]] (from [journal date])\n     - Difficulty: [level]\n     - Cost: $[range] DIY\n\
  \n   **Entries Requiring Manual Review**: [count]\n   - [Journal date] - [Issue\
  \ description]\n\n   **Next Actions**:\n   [List any entries needing clarification\
  \ or follow-up]\n   ```\n\n---\n\n## Usage Examples\n\n### Example 1: Simple Repair\
  \ Project\n**Journal Content** (`2026_01_07.md`):\n```markdown\n- Fix dripping kitchen\
  \ faucet [[Needs Handy Plan]]\n```\n\n**Processing**:\n1. Discovery: 1 entry found\
  \ (High priority - active leak)\n2. Research: Faucet repair techniques, parts, tools\n\
  3. Plan created: `[[Kitchen Faucet Repair]]`\n4. Entry transformed\n\n**Result**:\n\
  ```markdown\n- Created plan for [[Kitchen Faucet Repair]] - comprehensive repair\
  \ guide [[Planned 2026-01-07]]\n```\n\n### Example 2: Complex Construction Project\n\
  **Journal Content** (`2026_01_07.md`):\n```markdown\n- Build a raised garden bed\
  \ system in backyard [[Needs Handy Plan]]\n  - Want 3 beds, 4x8 feet each\n  - Need\
  \ to consider drainage\n```\n\n**Processing**:\n1. Discovery: 1 entry with specifications\
  \ (Medium priority)\n2. Research: Raised bed construction, materials, drainage solutions\n\
  3. Plan created: `[[Raised Garden Bed System]]`\n4. Entry transformed with context\
  \ preserved\n\n---\n\n## Quality Standards\n\nAll processing must satisfy:\n\n1.\
  \ **Safety Focus**:\n   - Safety section is comprehensive and prominent\n   - PPE\
  \ requirements clearly listed\n   - Emergency procedures included\n   - Professional\
  \ thresholds documented\n\n2. **Completeness**:\n   - All tools listed with specifications\n\
  \   - Materials include 10% overage\n   - Step-by-step instructions are actionable\n\
  \   - Cost estimates are realistic\n\n3. **Actionability**:\n   - Plan can be followed\
  \ without additional research\n   - Measurements and specifications are precise\n\
  \   - Quality checkpoints are clear\n   - Success criteria defined\n\n---\n\n##\
  \ Error Handling\n\n### Vague Project Description\n**Pattern**: \"Fix stuff around\
  \ house\"\n**Handling**: Add `#needs-clarification` tag, request specific project\
  \ details.\n\n### Safety-Critical Projects\n**Pattern**: Electrical, gas, structural\
  \ work\n**Handling**: Emphasize professional consultation, include detailed safety\
  \ warnings, note permit requirements.\n\n### Budget Constraints\n**Pattern**: User\
  \ mentions budget limit\n**Handling**: Prioritize cost-effective approaches, include\
  \ rental options, note where to save vs splurge.\n\n---\n\n## Command Invocation\n\
  \n**Format**: `/knowledge/process-needs-handy-plan`\n\n**Arguments**: None (processes\
  \ all pending entries)\n\n**Expected Duration**: 5-15 minutes per project\n\n**Prerequisites**:\n\
  - Brave Search accessible\n- Web tools functional\n\n**Post-Execution**:\n- Review\
  \ completion report\n- Address any entries requiring clarification\n- Verify new\
  \ project plans are complete\n"
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
