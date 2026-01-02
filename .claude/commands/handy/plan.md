---
title: Handy Project Planner with Journal Integration
description: Generate comprehensive project plans for construction and house projects with tools, parts, safety, and step-by-step instructions, plus automatic journal entry creation
arguments: [project_description]
---

# Home/Construction Project Plan Generator with Journal Integration

Create a comprehensive, actionable project plan as a Zettelkasten note for the following home improvement or construction project:

**Project Description**: $@

## Required Output Format

Generate a Zettelkasten note in the personal wiki `logseq/pages/` directory with the following structure:

### 1. Frontmatter and Overview
- Tags: Relevant tags like [[Home Improvement]], [[Construction]], [[DIY]], specific technique or area tags
- Related pages: Link to related concepts
- Project overview: 2-3 sentences describing the project
- Difficulty level: Beginner/Intermediate/Advanced
- Estimated time: Realistic time estimate
- Estimated cost: Cost range with breakdown

### 2. Safety Brief
Create a prominent safety section with:
- **Critical Safety Warnings**: Top hazards specific to this project
- **Required Safety Equipment**: PPE and safety gear needed
- **Emergency Procedures**: What to do if something goes wrong
- **When to Stop**: Red flags that indicate you should call a professional
- **Code Compliance**: Any building codes or permits required

### 3. Tools List
Organize tools into categories:
- **Essential Tools**: Must-have items
- **Power Tools**: Electric/battery powered equipment
- **Hand Tools**: Manual tools needed
- **Safety Equipment**: PPE and protective gear
- **Measurement/Layout**: Measuring and marking tools
- **Optional/Nice-to-Have**: Tools that make job easier but aren't required

For each tool, note:
- Specific type or size if relevant
- Can it be rented vs purchased
- Approximate cost if significant

### 4. Parts/Materials List
Create detailed materials list with:
- **Primary Materials**: Main components
- **Fasteners/Hardware**: Screws, nails, anchors, etc.
- **Consumables**: Sandpaper, tape, drop cloths, etc.
- **Finishing Materials**: Paint, stain, sealant, etc.

For each item include:
- Quantity needed (with ~10% overage where applicable)
- Specific size/dimensions
- Material grade or quality level
- Estimated cost
- Where to purchase (big box store, specialty supplier, etc.)

### 5. Pre-Work Preparation
- **Site Preparation**: Area prep, protection, access
- **Utility Considerations**: Power, water, gas shutoffs if needed
- **Permits/Inspections**: What's required
- **Weather Considerations**: Best conditions, what to avoid
- **Timeline Planning**: Best time of year, multi-day considerations

### 6. Step-by-Step Instructions
Create detailed phases with numbered steps:

For each major phase:
- **Phase Name** (estimated time)
- Numbered steps with clear actions
- **Key Points to Watch**: Critical details for each step
- **Common Mistakes to Avoid**: What often goes wrong
- **Quality Checks**: How to verify work is correct
- **Photos/Diagrams**: Suggest helpful visual references

Format each step clearly:
```
1. **Action Description**
   - Detail about how to do it
   - Measurement or specification
   - What to watch for
   - Expected result
```

### 7. Quality Control & Inspection
- **During Work**: Checkpoints throughout project
- **Final Inspection**: What to verify when complete
- **Testing**: Functional tests if applicable
- **Common Issues**: How to identify problems

### 8. Troubleshooting Guide
Create a troubleshooting section with:
- **Problem**: Common issue that occurs
- **Possible Causes**: Why it happens
- **Solutions**: How to fix it
- **Prevention**: How to avoid it next time

### 9. Cleanup & Disposal
- **During Project**: Managing waste and mess
- **Final Cleanup**: Complete cleanup procedures
- **Disposal Requirements**: How to dispose of materials (regular trash, hazardous waste, recycling)
- **Tool Maintenance**: Cleaning and storing tools

### 10. Maintenance & Follow-up
- **Initial Curing/Settling**: What to expect in first days/weeks
- **Regular Maintenance**: Ongoing care required
- **Inspection Schedule**: When to check on work
- **Expected Lifespan**: How long this should last

### 11. Success Criteria Checklist
Provide a clear checklist of what "done right" looks like:
- [ ] Structural/functional requirements met
- [ ] Safety standards met
- [ ] Aesthetic requirements met
- [ ] Cleanup complete
- [ ] Passes inspection (if required)

### 12. When to Call a Professional
Be honest about situations where professional help is needed:
- Complexity beyond DIY skill level
- Code requirements
- Safety concerns
- Specialized tools/equipment needed
- Time/cost where professional might be better value

### 13. Cost Breakdown
Provide realistic cost analysis:
- Materials: $X - $Y
- Tools (if purchasing): $X - $Y
- Tools (if renting): $X - $Y
- Permits/Inspections: $X - $Y
- Professional help (if any): $X - $Y
- **Total DIY Cost**: $X - $Y
- **Professional Cost Comparison**: $X - $Y

### 14. Related Concepts
Link to related Logseq pages:
- Techniques used in this project
- Related home improvement topics
- Building codes and regulations
- Tool usage guides
- Similar projects

## Important Guidelines

1. **Be Specific**: Use exact measurements, specific product types, and clear instructions
2. **Safety First**: Always emphasize safety over speed or cost
3. **Realistic Estimates**: Don't underestimate time or difficulty
4. **Local Codes**: Mention when local building codes should be consulted
5. **Skill Level**: Be honest about required skill level
6. **Professional Help**: Don't hesitate to recommend professionals when appropriate
7. **Quality Over Speed**: Emphasize doing it right over doing it fast
8. **Logseq Format**: Use proper wiki links [[Like This]] and tags #[[Like This]]

## Research Approach

If needed to create comprehensive plan:
1. Use WebSearch to research best practices for this specific project
2. Look up current building codes and safety standards
3. Research common mistakes and how to avoid them
4. Find typical material costs and availability
5. Identify any specialized techniques or considerations

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

Now, please generate a comprehensive project plan for: **$@**

Then create the corresponding journal entry documenting the planning work completed.
