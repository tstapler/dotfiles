---
name: resume-tailor
description: Customize resume for specific job postings while maintaining truthfulness
---

# Resume Tailor

## When to Use This Skill

Use this skill when the user wants to:
- Customize their resume for a specific job posting
- Adjust their resume to match job requirements
- Create a targeted version of their resume
- Mentions: "tailor resume", "customize resume", "target role", "specific job", "match job description"

Use AFTER job-description-analyzer to know what to emphasize.

## Core Capabilities

- Reorder experience sections by relevance to target role
- Adjust professional summary for specific position
- Add missing keywords from job description
- Modify bullet points to match job requirements
- Maintain authenticity while optimizing match
- Create multiple targeted resume versions

## The Tailoring Philosophy

**Key Principle:** You're not lying or fabricating - you're HIGHLIGHTING the most relevant parts of your true experience.

Think of your full experience as a library of achievements. Tailoring means selecting the books that best fit what each employer is looking for.

## Tailoring Process

### Step 1: Analyze the Job (Use Job Description Analyzer First)
- Identify required skills and keywords
- Note the company's priorities
- Understand the role's primary responsibilities

### Step 2: Audit Your Resume
For each section, ask:
- Does this support my candidacy for THIS specific role?
- Is there a better way to phrase this for THIS job?
- Should this be higher or lower in priority?

### Step 3: Make Strategic Adjustments

**Professional Summary:** Rewrite to mirror the job's key requirements

**Skills Section:** Reorder to put most relevant skills first, add missing keywords

**Experience:**
- Reorder jobs if a less recent role is more relevant
- Swap bullet points to lead with most relevant achievements
- Add keywords naturally into existing bullets

**Education:** Highlight relevant coursework, certifications

See `references/section-examples.md` for detailed before/after examples of summary rewrites, skills reordering, and bullet-language adjustments. See `references/scenarios.md` for strategies covering common situations (technical role at a non-tech company, IC-vs-management history, startup-vs-big-company moves).

Use `references/templates.md` for a ready-to-fill tailoring plan template for each application.

## Keyword Integration Rules

### DO:
- Add keywords that truthfully describe your work
- Use exact phrasing from job description when accurate
- Place keywords naturally in context
- Include keywords in multiple locations (summary, skills, experience)

### DON'T:
- Add skills you don't actually have
- Keyword stuff (repeating same term 10x)
- Create a different meaning than your actual experience
- Sacrifice readability for keyword density

## Truth vs. Tailoring Line

**Acceptable Tailoring:**
- Reordering true information
- Emphasizing relevant experience
- Using industry-standard terminology
- Adding context to vague statements
- Matching language style to job description

**Unacceptable (Lying):**
- Adding skills you don't have
- Changing numbers or metrics
- Creating fake experiences
- Claiming titles you didn't hold
- Stating certifications you don't have

## Version Management

Keep a master resume with every bullet you've ever written, and name each targeted version clearly (e.g. `Smith_Resume_PM_Google_Jan2024.pdf`). See `references/version-management.md` for the full convention, and use the `resume-version-manager` skill to track versions systematically across applications.

## Quick Tailoring Checklist

Before submitting any resume:

1. Summary mentions the exact job title/function
2. Top 5 skills match job description's top 5 requirements
3. Most relevant experience is positioned first
4. Each job's top bullet addresses job's key requirement
5. Keywords from JD appear naturally throughout
6. Company/industry terminology is used correctly
7. All claims are truthful
8. File is named appropriately
9. ATS formatting maintained
10. Saved for interview prep reference

## Output Format

When tailoring a resume, provide:

```markdown
# TAILORED RESUME CHANGES

## Target: [Job Title] at [Company]

### Professional Summary
**Before:** [Original]
**After:** [Tailored version]
**Keywords Added:** [List]

### Skills Section
**New Order:** [Reordered list]
**Added:** [New keywords]
**Removed:** [If any, for space]

### Experience Changes

**[Company Name] - [Title]**
- Move bullet X to position 1
- Modify bullet Y: [Before → After]
- Add keyword "[phrase]" to bullet Z

[Repeat for each relevant job]

### Overall Changes Summary
- Keywords added: X
- Bullets modified: Y
- Sections reordered: Yes/No
- Estimated new match score: Z%
```

## Implementation Notes

- Always start with the job description analyzer
- Keep tailoring changes documented for interview prep
- Maintain master resume as source of truth
- Never sacrifice ATS compatibility for tailoring
- Test keyword match after tailoring

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `job-description-analyzer` | Run analysis first to know what to emphasize |
| `resume-ats-optimizer` | Verify keyword match score after tailoring |
| `resume-bullet-writer` | Rewrite specific bullets to match the target role language |
| `resume-version-manager` | Save and track each tailored version systematically |
| `cover-letter-generator` | Write matching cover letter after tailoring is complete |
| `career-changer-translator` | Translate experience language for cross-industry tailoring |
| `resume-section-builder` | Restructure section order for role type or career stage |
