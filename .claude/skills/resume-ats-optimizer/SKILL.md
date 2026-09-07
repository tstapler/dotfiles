---
name: resume-ats-optimizer
description: Optimize resumes for Applicant Tracking Systems, check ATS compatibility, and analyze keyword match
---

# Resume ATS Optimizer

## When to Use This Skill

Use this skill when the user wants to:
- Optimize their resume for Applicant Tracking Systems (ATS)
- Check if their resume will pass automated screening
- Understand why their applications aren't getting responses
- Mentions keywords like: "ATS", "not getting interviews", "resume not working", "optimize resume", "keyword optimization"

Also use when the user provides a resume file and mentions they're applying to jobs.

## Core Capabilities

- Parse resume and test ATS compatibility
- Extract and analyze keywords against job descriptions
- Identify formatting issues that break ATS parsers
- Calculate match scores between resume and job postings
- Suggest keyword additions and placements
- Generate ATS-friendly formatting recommendations

## The ATS Problem

75% of resumes are rejected by Applicant Tracking Systems before a human ever sees them. Companies use ATS to:
- Filter out unqualified candidates automatically
- Search for specific keywords from job requirements
- Parse resumes into structured data
- Rank candidates by keyword match percentage

Common reasons resumes fail ATS:
1. Poor formatting (tables, columns, headers/footers)
2. Missing keywords from job description
3. Inconsistent section headers
4. Non-standard fonts or special characters
5. Text embedded in images
6. Incorrect file format

For the recurring formatting/naming/keyword mistakes that trip up ATS parsers, see [references/failure-patterns.md](references/failure-patterns.md).

## ATS Compatibility Checklist

### File Format
- Use .docx or .pdf (not .pages, .odt)
- PDF must be text-based, not scanned image
- File name: "FirstName_LastName_Resume.pdf"

### Font & Formatting
- Standard fonts: Arial, Calibri, Georgia, Times New Roman
- Font size: 10-12pt for body, 14-16pt for headers
- No text boxes, tables, or columns
- No headers/footers (put contact info in body)
- No images, graphics, or charts
- Consistent date formats (MM/YYYY)
- Standard bullet points (•, -, *)

### Section Headers
Use standard, recognizable headers:
- "Professional Experience" or "Work Experience" (not "Where I've Been")
- "Education" (not "Academic Background")
- "Skills" (not "Core Competencies")
- "Summary" or "Professional Summary"

### Contact Information
```
John Smith
email@example.com | (555) 123-4567 | LinkedIn: linkedin.com/in/johnsmith
San Francisco, CA
```

NOT in header/footer, and avoid tables for contact info, special characters in email, multiple phone numbers, or a full mailing address.

## Keyword Optimization Process

### Step 1: Extract Job Description Keywords

Identify three types of keywords:

**Hard Skills (Technical)**: Programming languages, tools/platforms, certifications, methodologies (Agile, Six Sigma, SDLC).

**Soft Skills**: Leadership, collaboration, communication, problem-solving, stakeholder management.

**Industry Terms**: B2B, SaaS, e-commerce, enterprise, SMB, ARR, MRR, churn rate.

### Step 2: Match Analysis

For each keyword in job description:
1. Check if exact phrase appears in resume
2. Check for synonyms or variations
3. Count frequency of mention
4. Note location (summary, experience, skills)

### Step 3: Calculate Match Score

```
Match Score = (Keywords Matched / Total Required Keywords) × 100

Example:
Job has 20 required keywords
Your resume has 15 of them
Match Score = 75%

Target: 80%+ for strong match
```

### Step 4: Keyword Placement Strategy

**Priority 1: Professional Summary (Top of Resume)** — include 5-8 most important keywords, used naturally in a 3-4 sentence paragraph.

**Priority 2: Skills Section** — list keywords explicitly, group by category if needed, use exact phrasing from job description.

**Priority 3: Experience Bullets** — incorporate keywords into achievement statements without forcing them; vary phrasing throughout.

**Keyword Density Guidelines:**
- Critical keywords: Appear 2-4 times throughout resume
- Important keywords: Appear 1-2 times
- Don't keyword stuff — keep it natural
- Vary phrasing (e.g., "led team" and "team leadership")

## Analysis Output

When analyzing a resume, produce a structured report scoring overall ATS compatibility, formatting issues, and keyword match with before/after recommendations. See [references/output-template.md](references/output-template.md) for the exact format to follow.

## Industry-Specific Considerations

Tech, business/finance, healthcare, and marketing resumes each have their own high-value keyword categories and required credentials — see [references/industry-considerations.md](references/industry-considerations.md).

## Edge Cases & Special Situations

Career changers, recent graduates, executives, and candidates with employment gaps each need adjusted keyword and formatting strategies — see [references/edge-cases.md](references/edge-cases.md).

## Implementation Checklist

When helping user optimize for ATS:

1. Scan current resume for ATS compatibility issues
2. Analyze job description for required keywords
3. Calculate current match score
4. Identify specific missing keywords
5. Suggest exact placements for new keywords
6. Flag formatting problems
7. Provide before/after examples
8. Re-score after suggested changes
9. Verify file format and naming
10. Test with ATS simulator if possible

## Success Metrics

After optimization, the resume should:
- Score 80%+ match for target job descriptions
- Pass ATS parsing test (all sections recognized)
- Have zero formatting errors
- Include all critical keywords 2-4x each
- Read naturally (not keyword-stuffed)
- Be ready to submit immediately

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `job-description-analyzer` | Extract required keywords before running ATS optimization |
| `resume-tailor` | Apply keyword strategy within a role-specific tailored version |
| `resume-formatter` | Fix formatting issues (tables, columns) that break ATS parsers |
| `resume-bullet-writer` | Incorporate keywords naturally into achievement bullets |
| `resume-section-builder` | Use ATS-recognized section headers throughout |
| `tech-resume-optimizer` | Apply tech-specific keyword and skills-section guidance |
| `career-changer-translator` | Add target-industry keywords from translated experience |
