---
name: resume-version-manager
description: Track different resume versions, maintain master resume, manage tailored versions
---

# Resume Version Manager

## When to Use This Skill

Use this skill when the user:
- Has multiple resume versions to manage
- Needs to track tailored resumes
- Wants to maintain a master resume
- Is applying to many different roles
- Mentions: "resume versions", "master resume", "different versions", "track resumes", "which resume"

## Core Capabilities

- Create and maintain master resume document
- Track tailored resume versions
- Organize resume versions by role/industry
- Maintain consistent source of truth
- Streamline resume updates
- Prevent version confusion

## The Version Management Problem

**Common Pain Points:**
- "Which version did I send to Company X?"
- "Where's my most recent resume?"
- "I have 15 resume files and don't know which is best"
- "I forgot to update my resume after that project"
- "I keep tailoring from different base versions"

**The Solution:**
A systematic approach with:
1. One master resume (source of truth)
2. Organized tailored versions
3. Clear naming conventions
4. Update workflow

## Master Resume Concept

A master resume is a single comprehensive document containing ALL your experiences, bullet points, and achievements — even ones that won't fit on any one-page tailored version. It's the source of truth every tailored resume pulls from; never edit it directly for a specific application.

See `references/master-resume-template.md` for the full section-by-section template.

## File Organization

Organize resumes into `Master/`, `Tailored/<role-type>/`, `CoverLetters/`, and `Applications/` folders, with a consistent naming pattern: `[LastName]_[Role/Type]_[Company]_[Date].pdf`.

See `references/organization.md` for the full folder structure and version categories (by target role, industry, and seniority level).

## Update Workflow

### When to Update Master Resume

**Immediately Update For:**
- New job or promotion
- Completed major project
- New skills or certifications
- Significant achievements
- Awards or recognition

**Quarterly Review:**
- Add recent accomplishments
- Update metrics with new data
- Refresh skills section
- Remove outdated information

### Master to Tailored Workflow

```
1. Start with Master Resume
   ↓
2. Copy to new file (don't edit master)
   ↓
3. Analyze job description
   ↓
4. Select relevant bullets from master
   ↓
5. Choose appropriate summary version
   ↓
6. Reorder skills for relevance
   ↓
7. Add job-specific keywords
   ↓
8. Trim to appropriate length
   ↓
9. Save with proper naming convention
   ↓
10. Update application tracker
```

Track every submission (company, role, version used, date, status) so you always know what was sent where — see `references/application-tracking.md` for a ready-to-use tracker format. For scenario-specific strategies (similar roles, different role types, high application volume, career transitions), see `references/scenarios.md`.

## Version Control Best Practices

### DO:
- Always work from master as source
- Use consistent naming conventions
- Track which version went where
- Keep master updated
- Date your files
- Backup to cloud storage

### DON'T:
- Edit master directly for applications
- Use vague names like "resume_final_v2"
- Forget which version you sent
- Let master get out of date
- Have multiple "master" files
- Delete old versions (archive instead)

## Output Format

When managing resume versions:

```markdown
# RESUME VERSION MANAGEMENT

## Master Resume Status
**Last Updated:** [Date]
**Location:** [File path]
**Total Experience Entries:** [X]
**Total Bullet Points Available:** [X]

## Active Versions

### Role Type: Product Management
**Base Version:** PM_General_2024.docx
**Tailored Versions:**
| Company | File Name | Date Created | Status |
|---------|-----------|--------------|--------|
| Google | PM_Google_Jan24 | 1/15/24 | Submitted |
| Meta | PM_Meta_Jan24 | 1/18/24 | Submitted |

### Role Type: Engineering
[Same structure]

## Update Queue
- [ ] Add Q4 project results to master
- [ ] Update skills with new certification
- [ ] Archive versions older than 6 months

## Recommended Actions
1. [Action 1]
2. [Action 2]
```

## Version Management Checklist

- Master resume exists and is current
- Folder structure is organized
- Naming convention is consistent
- Application tracker is maintained
- Know which version sent to each company
- All versions pull from same master
- Backup system in place
- Old versions archived (not deleted)
- Update workflow is established
- Regular master resume reviews scheduled

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `resume-tailor` | Create each new tailored version from the master |
| `job-description-analyzer` | Determine which master bullets to pull for each tailored version |
| `resume-ats-optimizer` | Validate each tailored version before filing it |
| `cover-letter-generator` | Track matching cover letters alongside each resume version |
| `resume-bullet-writer` | Update master resume with newly written strong bullets |
