---
title: Expert Project Planner
description: Engineering-focused project plans with solo work strategies, critical path analysis, and professional-grade techniques
arguments: [project_description]
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

Save to: `logseq/pages/[Project Name].md`

---

Generate the expert project plan for: **$@**
