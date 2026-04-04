---
description: Engineering-focused project plans with solo work strategies, critical
  path analysis, and professional-grade techniques
prompt: "# Expert Construction Project Planner\n\nGenerate an engineering-focused\
  \ project plan for an experienced builder working solo. Assume expert-level knowledge\
  \ of tools, techniques, and safety fundamentals.\n\n**Project**: $@\n\n## User Context\n\
  - Expert-level construction experience across multiple trades\n- Engineering background\
  \ (structural, mechanical, electrical principles)\n- Follows John Carroll's \"Working\
  \ Alone\" methodology - plans for single-person execution\n- Located in Seattle\
  \ jurisdiction - reference Seattle Building Code (SBC), Seattle Residential Code\
  \ (SRC), and Seattle amendments to IRC/IBC/NEC/IPC\n- Seeks optimization, efficiency,\
  \ and professional techniques\n- Does not need basic explanations or beginner safety\
  \ reminders\n\n## Reference Materials\n\n**Primary Solo Work Reference**\n- *Working\
  \ Alone: Tips and Techniques for Solo Building* by John Carroll (Taunton Press)\n\
  \  - Apply principles: jigs/fixtures, mechanical advantage, sequencing, pre-assembly\n\
  \n**Code References (Seattle Jurisdiction)**\n- Seattle Building Code (SBC) - commercial/large\
  \ residential\n- Seattle Residential Code (SRC) - 1-2 family dwellings, based on\
  \ IRC with Seattle amendments\n- Seattle Electrical Code - based on NEC with local\
  \ amendments\n- Seattle Plumbing Code - based on UPC (not IPC) with amendments\n\
  - Seattle Mechanical Code - based on UMC with amendments\n- Seattle Energy Code\
  \ - often more stringent than state/national codes\n\n**Technical References**\n\
  - *Graphic Guide to Frame Construction* by Rob Thallon\n- *Building Construction\
  \ Illustrated* by Francis Ching\n- *Code Check* series for quick code verification\n\
  - Manufacturer specifications for engineered products\n\n## Research Requirements\n\
  \nUse the @research agent to investigate:\n1. Current Seattle code requirements\
  \ for the specific project scope\n2. Seattle permit requirements and inspection\
  \ trigger points\n3. Professional techniques and trade methods (not DIY tutorials)\n\
  4. John Carroll \"Working Alone\" techniques applicable to this project\n5. Material\
  \ specifications and engineering data\n\n## Required Output Structure\n\nGenerate\
  \ a Zettelkasten note in `logseq/pages/` with this structure:\n\n```markdown\n---\n\
  tags: [[Construction]], [[Engineering]], [[Solo Build]], [[Seattle Code]], [project-specific\
  \ tags]\ncomplexity: [Standard | Complex | High-Stakes]\nsolo-feasibility: [Straightforward\
  \ | Requires Planning | Challenging Solo]\n---\n```\n\n### 1. Project Synopsis\n\
  - 2-3 sentence technical summary\n- Key engineering challenges\n- Solo execution\
  \ feasibility assessment (per Carroll's methodology)\n- Time estimate (working hours,\
  \ not calendar days)\n- Material cost estimate\n- Seattle permit requirements summary\n\
  \n### 2. Engineering Analysis\n\n**Structural Considerations**\n- Load paths and\
  \ transfer mechanisms\n- Point loads vs. distributed loads\n- Deflection limits\
  \ and calculations if relevant\n- Connection design (moment vs. shear)\n- Temporary\
  \ bracing requirements during construction\n- Reference: SRC Chapter 5 (Floors),\
  \ Chapter 6 (Wall Construction), Chapter 8 (Roof-Ceiling Construction)\n\n**Systems\
  \ Integration**\n- Electrical: Load calculations, circuit requirements, Seattle\
  \ Electrical Code references\n- Plumbing: DFU calculations, Seattle Plumbing Code\
  \ (UPC-based) requirements\n- HVAC: BTU calculations, duct sizing, Seattle Mechanical\
  \ Code clearances\n- Only include sections relevant to the project\n\n**Building\
  \ Science**\n- Thermal bridging and insulation strategy\n- Vapor barrier placement\
  \ - Seattle's marine climate (Climate Zone 4C) considerations\n- Air sealing critical\
  \ points per Seattle Energy Code\n- Moisture management critical in PNW climate\
  \ - drying potential analysis\n- Reference: Seattle Energy Code, Chapter 11 SRC\n\
  \n**Seattle Code Requirements**\n- Specific SRC/SBC section references\n- Seattle\
  \ amendments that differ from base IRC/IBC\n- Permit trigger points (when does this\
  \ require a permit?)\n- Inspection requirements and scheduling\n- Documentation\
  \ for permit application if needed\n\n### 3. Solo Work Strategy\n\nApply John Carroll's\
  \ \"Working Alone\" principles:\n\n**Jigs and Fixtures** (Carroll Ch. 3-4)\n- Custom\
  \ jigs to fabricate before starting\n- Temporary supports and bracing - design for\
  \ one-person setup\n- Clamping strategies for assembly\n- Registration marks and\
  \ alignment aids\n- Deadman supports, T-braces, and prop sticks\n\n**Mechanical\
  \ Advantage** (Carroll Ch. 5)\n- Lever systems for heavy components\n- Block and\
  \ tackle / come-along applications\n- Staged lifting approaches - break heavy assemblies\
  \ into manageable pieces\n- Pivot points and fulcrum placement\n- Gin pole techniques\
  \ for vertical lifts\n\n**Sequencing for Solo Execution** (Carroll Ch. 2)\n- What\
  \ to pre-assemble on the ground/bench\n- Modular construction opportunities\n- Order\
  \ of operations that eliminates need for helpers\n- When to use temporary fasteners\
  \ vs. final connections\n- \"Build it where you can, install it where it goes\"\n\
  \n**Positioning and Handling** (Carroll Ch. 6)\n- Material staging locations for\
  \ minimal handling\n- Work height optimization - avoid excessive ladder work\n-\
  \ Rolling stock for heavy materials\n- Weight thresholds and breaking down assemblies\n\
  \n### 4. Critical Path Analysis\n\n**Sequential Dependencies** (must complete in\
  \ order)\n```\nPhase A → Phase B → Phase C\n   ↓\n[Curing/Dry time: X hours]\n[Inspection\
  \ hold point: before covering]\n```\n\n**Parallel Opportunities** (can batch or\
  \ overlap)\n- Tasks during cure times\n- Prep work for upcoming phases\n- Material\
  \ staging during work\n\n**Weather Dependencies** (Seattle climate considerations)\n\
  - Rain windows - realistic for PNW (plan for working in light rain)\n- Temperature\
  \ windows for specific materials\n- Moisture content requirements for wood\n- Concrete/masonry\
  \ temperature minimums\n\n**Seattle Inspection Hold Points**\n- Work requiring inspection\
  \ before covering\n- Scheduling considerations (SDCI inspection lead times)\n- Self-inspection\
  \ checkpoints with specific criteria\n- Documentation photos for permit file\n\n\
  ### 5. Tools and Materials\n\n**Tools** (concise list, no usage explanations)\n\
  - Specific sizes/types where specification matters\n- Solo-enabling tools per Carroll\
  \ (pipe clamps, panel carriers, etc.)\n\n**Materials with Specifications**\nFormat:\n\
  ```\n- [Material]: [Spec/Grade] - [Quantity w/ waste factor]\n  Why this spec: [Performance\
  \ reason, code requirement, or durability factor]\n```\n\nFocus on:\n- Structural\
  \ grades and code requirements (DF-L vs. SPF, grade stamps)\n- Fastener specifications\
  \ per code (Seattle seismic requirements)\n- Material compatibility (galvanic, chemical,\
  \ moisture)\n- PNW-appropriate materials (rot resistance, moisture tolerance)\n\n\
  ### 6. Execution Plan\n\nOrganize by phases. For each phase:\n\n**Phase N: [Name]**\
  \ (~X hours)\n\n*Setup* (apply Carroll staging principles)\n- Work zone configuration\n\
  - Tool staging\n- Material positioning for minimal handling\n\n*Execution*\n- Numbered\
  \ steps focusing on:\n  - Critical dimensions and tolerances\n  - Sequencing for\
  \ solo execution\n  - Non-obvious gotchas\n  - Professional techniques from trade\
  \ practice\n- Skip obvious steps; emphasize decision points\n\n*Carroll Techniques\
  \ Applied*\n- Specific solo methods from \"Working Alone\" for this phase\n- Jig\
  \ or fixture requirements\n- Mechanical advantage applications\n\n*Verification*\n\
  - Measurements to check (with tolerances)\n- Structural/functional verification\n\
  - What to confirm before proceeding\n- Photo documentation for permit file\n\n###\
  \ 7. Quality Verification\n\n**Engineering Checkpoints**\n- Specific measurements\
  \ with tolerances\n- Load testing procedures if applicable\n- Structural verification\
  \ methods\n- Systems testing (pressure test, megger test, etc.)\n\n**Seattle Code\
  \ Compliance Verification**\n- Self-inspection against specific SRC/SBC sections\n\
  - Documentation for SDCI inspector\n- Photo documentation recommendations\n- Common\
  \ Seattle inspection failure points to avoid\n\n**Performance Validation**\n- Functional\
  \ testing procedures\n- Success indicators vs. rework triggers\n- Long-term performance\
  \ indicators\n\n### 8. Contingencies and Adaptations\n\n**Likely Complications**\n\
  - Common field conditions in Seattle (soil, moisture, existing construction)\n-\
  \ Weather impacts and workarounds\n- Material/supply issues and alternatives\n\n\
  **Decision Trees**\n```\nIf [condition X]:\n  → Option A: [approach]\n  → Option\
  \ B: [alternative]\n```\n\n**Backup Strategies**\n- Plan B for critical path items\n\
  - Material substitutions maintaining code compliance\n- Schedule recovery options\n\
  \n### 9. Non-Obvious Hazards\n\nSkip standard PPE. Note only:\n- Project-specific\
  \ hazards not immediately apparent\n- Seattle-specific concerns (lead paint in pre-1978,\
  \ asbestos in pre-1980)\n- Failure mode risks during solo construction\n- Stored\
  \ energy situations\n- Cumulative exposure concerns\n\n### 10. Cost Analysis\n\n\
  ```\nMaterials: $X (itemize items >$50)\nSpecialty tools if needed: $X\nSeattle\
  \ permit fees: $X (reference current SDCI fee schedule)\nTotal: $X\n```\n\n### 11.\
  \ Reference Links\n\nLink to relevant Logseq pages:\n- [[Seattle Building Codes]]\
  \ sections referenced\n- [[Working Alone Techniques]] applied\n- [[Building Science]]\
  \ principles\n- Related completed projects\n\n**External References**\n- Seattle\
  \ DCI permit portal: https://cosaccela.seattle.gov\n- Seattle code library: https://seattle.gov/sdci/codes\n\
  \n## Generation Guidelines\n\n1. **Assume expertise** - No basic technique explanations\
  \ or standard safety reminders\n2. **Seattle-specific** - Reference Seattle codes,\
  \ not just IRC/IBC base codes\n3. **Carroll methodology** - Integrate \"Working\
  \ Alone\" principles throughout\n4. **Engineering depth** - Include calculations,\
  \ code references, specifications\n5. **Solo-first** - Every recommendation considers\
  \ single-person execution\n6. **Optimization focus** - Professional shortcuts and\
  \ efficiency techniques\n7. **Colleague tone** - Peer exchange, not instruction\n\
  8. **Logseq format** - Use [[wiki links]] and appropriate tags\n\n## Research Protocol\n\
  \nBefore generating the plan, use @research agent to:\n1. Verify current Seattle\
  \ code requirements for project scope\n2. Confirm Seattle permit thresholds and\
  \ inspection requirements\n3. Research professional/trade techniques (avoid DIY\
  \ tutorial content)\n4. Find Carroll \"Working Alone\" techniques for project type\n\
  5. Check current material specifications and availability\n\n## Output Location\n\
  \nSave the zettel to the personal wiki directory in:\n`/Users/tylerstapler/Documents/personal-wiki/logseq/pages/[Project\
  \ Name].md`\n\nUse a clear, descriptive page name that follows Logseq conventions.\n\
  \n## Journal Entry Creation\n\nAfter successfully creating the project plan, create\
  \ or update today's journal entry:\n\n### 1. Determine Journal File\n- Get today's\
  \ date and format as `YYYY_MM_DD.md` (e.g., `2025_12_22.md`)\n- Full path: `/Users/tylerstapler/Documents/personal-wiki/logseq/journals/YYYY_MM_DD.md`\n\
  \n### 2. Journal Entry Format\nCreate a journal entry with the following structure:\n\
  \n```markdown\n- **Project Planning**: Created comprehensive plan for [[Project\
  \ Name]] #[[Home Improvement]] #[[Planning]]\n  - Generated detailed guide covering\
  \ safety, tools, materials, and step-by-step instructions\n  - Estimated cost: $[DIY\
  \ Cost Range] DIY vs $[Professional Cost Range] professional\n  - Difficulty level:\
  \ [Beginner/Intermediate/Advanced]\n  - Estimated time: [Time Estimate]\n  - Key\
  \ considerations: [1-2 major decision points or challenges]\n  - Next steps: [What\
  \ should be done next - review plan, purchase materials, schedule work, etc.]\n\
  ```\n\n### 3. Journal Entry Implementation\n- **Check if file exists**: Read the\
  \ journal file for today if it exists\n- **Append to existing file**: If the file\
  \ exists, append the new entry at the END (not beginning)\n- **Create new file**:\
  \ If the file doesn't exist, create it with the entry\n- **Preserve existing content**:\
  \ Never overwrite existing journal entries\n- **Add blank line separator**: Add\
  \ a blank line before the new entry if appending\n\n### 4. Error Handling\n- If\
  \ journal file cannot be created/updated, notify user but don't fail the command\n\
  - Log the journal entry content so user can manually add if needed\n- Handle file\
  \ permissions gracefully\n\n### 5. Success Confirmation\nAfter both the project\
  \ plan and journal entry are created:\n1. Confirm project plan saved to: `logseq/pages/[Project\
  \ Name].md`\n2. Confirm journal entry added to: `logseq/journals/YYYY_MM_DD.md`\n\
  3. Provide summary of what was created and key takeaways\n\n## Example Workflow\n\
  \n1. User runs: `handy:plan \"Repointing brick stairs on front of house\"`\n2. Command\
  \ researches best practices for repointing brick/mortar\n3. Creates comprehensive\
  \ plan at: `logseq/pages/Repointing 711 N 60th Front Stairs.md`\n4. Appends entry\
  \ to: `logseq/journals/2025_12_22.md`:\n   ```markdown\n   - **Project Planning**:\
  \ Created comprehensive plan for [[Repointing 711 N 60th Front Stairs]] #[[Home\
  \ Improvement]] #[[Planning]]\n     - Generated detailed guide covering safety,\
  \ tools, materials, and step-by-step instructions\n     - Estimated cost: $300-$600\
  \ DIY vs $2,000-$4,000 professional\n     - Difficulty level: Intermediate\n   \
  \  - Estimated time: 2-3 days\n     - Key considerations: Weather timing critical,\
  \ requires mortar color matching\n     - Next steps: Review plan, source matching\
  \ mortar, schedule for spring when temperatures stable above 40°F\n   ```\n5. Confirms\
  \ both files created successfully\n\n---\n\nGenerate the expert project plan for:\
  \ **$@**\n\nThen create the corresponding journal entry documenting the planning\
  \ work completed.\n"
---

# Expert Construction Project Planner

Generate an engineering-focused project plan for an experienced builder working solo. Assume expert-level knowledge of tools, techniques, and safety fundamentals.

**Project**: $@

## User Context
- Expert-level construction experience across multiple trades
- Engineering background (structural, mechanical, electrical principles)
- Follows John Carroll's "Working Alone" methodology - plans for single-person execution
- Located in Seattle jurisdiction - reference Seattle Building Code (SBC), Seattle Residential Code (SRC), and Seattle amendments to IRC/IBC/NEC/IPC
- Seeks optimization, efficiency, and professional techniques
- Does not need basic explanations or beginner safety reminders

## Reference Materials

**Primary Solo Work Reference**
- *Working Alone: Tips and Techniques for Solo Building* by John Carroll (Taunton Press)
  - Apply principles: jigs/fixtures, mechanical advantage, sequencing, pre-assembly

**Code References (Seattle Jurisdiction)**
- Seattle Building Code (SBC) - commercial/large residential
- Seattle Residential Code (SRC) - 1-2 family dwellings, based on IRC with Seattle amendments
- Seattle Electrical Code - based on NEC with local amendments
- Seattle Plumbing Code - based on UPC (not IPC) with amendments
- Seattle Mechanical Code - based on UMC with amendments
- Seattle Energy Code - often more stringent than state/national codes

**Technical References**
- *Graphic Guide to Frame Construction* by Rob Thallon
- *Building Construction Illustrated* by Francis Ching
- *Code Check* series for quick code verification
- Manufacturer specifications for engineered products

## Research Requirements

Use the @research agent to investigate:
1. Current Seattle code requirements for the specific project scope
2. Seattle permit requirements and inspection trigger points
3. Professional techniques and trade methods (not DIY tutorials)
4. John Carroll "Working Alone" techniques applicable to this project
5. Material specifications and engineering data

## Required Output Structure

Generate a Zettelkasten note in `logseq/pages/` with this structure:

```markdown
---
tags: [[Construction]], [[Engineering]], [[Solo Build]], [[Seattle Code]], [project-specific tags]
complexity: [Standard | Complex | High-Stakes]
solo-feasibility: [Straightforward | Requires Planning | Challenging Solo]
---
```

### 1. Project Synopsis
- 2-3 sentence technical summary
- Key engineering challenges
- Solo execution feasibility assessment (per Carroll's methodology)
- Time estimate (working hours, not calendar days)
- Material cost estimate
- Seattle permit requirements summary

### 2. Engineering Analysis

**Structural Considerations**
- Load paths and transfer mechanisms
- Point loads vs. distributed loads
- Deflection limits and calculations if relevant
- Connection design (moment vs. shear)
- Temporary bracing requirements during construction
- Reference: SRC Chapter 5 (Floors), Chapter 6 (Wall Construction), Chapter 8 (Roof-Ceiling Construction)

**Systems Integration**
- Electrical: Load calculations, circuit requirements, Seattle Electrical Code references
- Plumbing: DFU calculations, Seattle Plumbing Code (UPC-based) requirements
- HVAC: BTU calculations, duct sizing, Seattle Mechanical Code clearances
- Only include sections relevant to the project

**Building Science**
- Thermal bridging and insulation strategy
- Vapor barrier placement - Seattle's marine climate (Climate Zone 4C) considerations
- Air sealing critical points per Seattle Energy Code
- Moisture management critical in PNW climate - drying potential analysis
- Reference: Seattle Energy Code, Chapter 11 SRC

**Seattle Code Requirements**
- Specific SRC/SBC section references
- Seattle amendments that differ from base IRC/IBC
- Permit trigger points (when does this require a permit?)
- Inspection requirements and scheduling
- Documentation for permit application if needed

### 3. Solo Work Strategy

Apply John Carroll's "Working Alone" principles:

**Jigs and Fixtures** (Carroll Ch. 3-4)
- Custom jigs to fabricate before starting
- Temporary supports and bracing - design for one-person setup
- Clamping strategies for assembly
- Registration marks and alignment aids
- Deadman supports, T-braces, and prop sticks

**Mechanical Advantage** (Carroll Ch. 5)
- Lever systems for heavy components
- Block and tackle / come-along applications
- Staged lifting approaches - break heavy assemblies into manageable pieces
- Pivot points and fulcrum placement
- Gin pole techniques for vertical lifts

**Sequencing for Solo Execution** (Carroll Ch. 2)
- What to pre-assemble on the ground/bench
- Modular construction opportunities
- Order of operations that eliminates need for helpers
- When to use temporary fasteners vs. final connections
- "Build it where you can, install it where it goes"

**Positioning and Handling** (Carroll Ch. 6)
- Material staging locations for minimal handling
- Work height optimization - avoid excessive ladder work
- Rolling stock for heavy materials
- Weight thresholds and breaking down assemblies

### 4. Critical Path Analysis

**Sequential Dependencies** (must complete in order)
```
Phase A → Phase B → Phase C
   ↓
[Curing/Dry time: X hours]
[Inspection hold point: before covering]
```

**Parallel Opportunities** (can batch or overlap)
- Tasks during cure times
- Prep work for upcoming phases
- Material staging during work

**Weather Dependencies** (Seattle climate considerations)
- Rain windows - realistic for PNW (plan for working in light rain)
- Temperature windows for specific materials
- Moisture content requirements for wood
- Concrete/masonry temperature minimums

**Seattle Inspection Hold Points**
- Work requiring inspection before covering
- Scheduling considerations (SDCI inspection lead times)
- Self-inspection checkpoints with specific criteria
- Documentation photos for permit file

### 5. Tools and Materials

**Tools** (concise list, no usage explanations)
- Specific sizes/types where specification matters
- Solo-enabling tools per Carroll (pipe clamps, panel carriers, etc.)

**Materials with Specifications**
Format:
```
- [Material]: [Spec/Grade] - [Quantity w/ waste factor]
  Why this spec: [Performance reason, code requirement, or durability factor]
```

Focus on:
- Structural grades and code requirements (DF-L vs. SPF, grade stamps)
- Fastener specifications per code (Seattle seismic requirements)
- Material compatibility (galvanic, chemical, moisture)
- PNW-appropriate materials (rot resistance, moisture tolerance)

### 6. Execution Plan

Organize by phases. For each phase:

**Phase N: [Name]** (~X hours)

*Setup* (apply Carroll staging principles)
- Work zone configuration
- Tool staging
- Material positioning for minimal handling

*Execution*
- Numbered steps focusing on:
  - Critical dimensions and tolerances
  - Sequencing for solo execution
  - Non-obvious gotchas
  - Professional techniques from trade practice
- Skip obvious steps; emphasize decision points

*Carroll Techniques Applied*
- Specific solo methods from "Working Alone" for this phase
- Jig or fixture requirements
- Mechanical advantage applications

*Verification*
- Measurements to check (with tolerances)
- Structural/functional verification
- What to confirm before proceeding
- Photo documentation for permit file

### 7. Quality Verification

**Engineering Checkpoints**
- Specific measurements with tolerances
- Load testing procedures if applicable
- Structural verification methods
- Systems testing (pressure test, megger test, etc.)

**Seattle Code Compliance Verification**
- Self-inspection against specific SRC/SBC sections
- Documentation for SDCI inspector
- Photo documentation recommendations
- Common Seattle inspection failure points to avoid

**Performance Validation**
- Functional testing procedures
- Success indicators vs. rework triggers
- Long-term performance indicators

### 8. Contingencies and Adaptations

**Likely Complications**
- Common field conditions in Seattle (soil, moisture, existing construction)
- Weather impacts and workarounds
- Material/supply issues and alternatives

**Decision Trees**
```
If [condition X]:
  → Option A: [approach]
  → Option B: [alternative]
```

**Backup Strategies**
- Plan B for critical path items
- Material substitutions maintaining code compliance
- Schedule recovery options

### 9. Non-Obvious Hazards

Skip standard PPE. Note only:
- Project-specific hazards not immediately apparent
- Seattle-specific concerns (lead paint in pre-1978, asbestos in pre-1980)
- Failure mode risks during solo construction
- Stored energy situations
- Cumulative exposure concerns

### 10. Cost Analysis

```
Materials: $X (itemize items >$50)
Specialty tools if needed: $X
Seattle permit fees: $X (reference current SDCI fee schedule)
Total: $X
```

### 11. Reference Links

Link to relevant Logseq pages:
- [[Seattle Building Codes]] sections referenced
- [[Working Alone Techniques]] applied
- [[Building Science]] principles
- Related completed projects

**External References**
- Seattle DCI permit portal: https://cosaccela.seattle.gov
- Seattle code library: https://seattle.gov/sdci/codes

## Generation Guidelines

1. **Assume expertise** - No basic technique explanations or standard safety reminders
2. **Seattle-specific** - Reference Seattle codes, not just IRC/IBC base codes
3. **Carroll methodology** - Integrate "Working Alone" principles throughout
4. **Engineering depth** - Include calculations, code references, specifications
5. **Solo-first** - Every recommendation considers single-person execution
6. **Optimization focus** - Professional shortcuts and efficiency techniques
7. **Colleague tone** - Peer exchange, not instruction
8. **Logseq format** - Use [[wiki links]] and appropriate tags

## Research Protocol

Before generating the plan, use @research agent to:
1. Verify current Seattle code requirements for project scope
2. Confirm Seattle permit thresholds and inspection requirements
3. Research professional/trade techniques (avoid DIY tutorial content)
4. Find Carroll "Working Alone" techniques for project type
5. Check current material specifications and availability

## Output Location

Save the zettel to the personal wiki directory in:
`/Users/tylerstapler/Documents/personal-wiki/logseq/pages/[Project Name].md`

Use a clear, descriptive page name that follows Logseq conventions.

## Journal Entry Creation

After successfully creating the project plan, create or update today's journal entry:

### 1. Determine Journal File
- Get today's date and format as `YYYY_MM_DD.md` (e.g., `2025_12_22.md`)
- Full path: `/Users/tylerstapler/Documents/personal-wiki/logseq/journals/YYYY_MM_DD.md`

### 2. Journal Entry Format
Create a journal entry with the following structure:

```markdown
- **Project Planning**: Created comprehensive plan for [[Project Name]] #[[Home Improvement]] #[[Planning]]
  - Generated detailed guide covering safety, tools, materials, and step-by-step instructions
  - Estimated cost: $[DIY Cost Range] DIY vs $[Professional Cost Range] professional
  - Difficulty level: [Beginner/Intermediate/Advanced]
  - Estimated time: [Time Estimate]
  - Key considerations: [1-2 major decision points or challenges]
  - Next steps: [What should be done next - review plan, purchase materials, schedule work, etc.]
```

### 3. Journal Entry Implementation
- **Check if file exists**: Read the journal file for today if it exists
- **Append to existing file**: If the file exists, append the new entry at the END (not beginning)
- **Create new file**: If the file doesn't exist, create it with the entry
- **Preserve existing content**: Never overwrite existing journal entries
- **Add blank line separator**: Add a blank line before the new entry if appending

### 4. Error Handling
- If journal file cannot be created/updated, notify user but don't fail the command
- Log the journal entry content so user can manually add if needed
- Handle file permissions gracefully

### 5. Success Confirmation
After both the project plan and journal entry are created:
1. Confirm project plan saved to: `logseq/pages/[Project Name].md`
2. Confirm journal entry added to: `logseq/journals/YYYY_MM_DD.md`
3. Provide summary of what was created and key takeaways

## Example Workflow

1. User runs: `handy:plan "Repointing brick stairs on front of house"`
2. Command researches best practices for repointing brick/mortar
3. Creates comprehensive plan at: `logseq/pages/Repointing 711 N 60th Front Stairs.md`
4. Appends entry to: `logseq/journals/2025_12_22.md`:
   ```markdown
   - **Project Planning**: Created comprehensive plan for [[Repointing 711 N 60th Front Stairs]] #[[Home Improvement]] #[[Planning]]
     - Generated detailed guide covering safety, tools, materials, and step-by-step instructions
     - Estimated cost: $300-$600 DIY vs $2,000-$4,000 professional
     - Difficulty level: Intermediate
     - Estimated time: 2-3 days
     - Key considerations: Weather timing critical, requires mortar color matching
     - Next steps: Review plan, source matching mortar, schedule for spring when temperatures stable above 40°F
   ```
5. Confirms both files created successfully

---

Generate the expert project plan for: **$@**

Then create the corresponding journal entry documenting the planning work completed.
