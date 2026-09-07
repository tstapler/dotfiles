---
name: job-description-analyzer
description: Analyze job postings, calculate match scores, identify gaps, and create application strategy
---

# Job Description Analyzer

## When to Use This Skill

Use this skill when the user:
- Wants to analyze a job posting
- Asks "should I apply to this job?"
- Wants to know their match percentage for a role
- Needs help understanding job requirements
- Wants to tailor their resume for a specific position
- Mentions: "analyze this job", "am I qualified", "match score", "should I apply"

Use this BEFORE resume tailoring to ensure effort is worth it.

## Core Capabilities

- Extract and categorize job requirements (must-have vs nice-to-have)
- Calculate match score between user's experience and job requirements
- Identify skill gaps and strengths
- Detect red flags in job postings
- Prioritize which experiences to highlight
- Generate resume tailoring strategy
- Create cover letter talking points
- Assess company culture fit indicators

## The Strategic Problem

Most job seekers waste time on:
- Jobs they're under-qualified for (<60% match)
- Jobs they're over-qualified for (flight risk)
- Jobs with red flags (high turnover, toxic culture)
- Applying to 50+ jobs blindly hoping something sticks

Better approach:
- Apply to 10-15 jobs strategically
- Target 70-90% match jobs
- Customize deeply for each
- Higher response rate, less burnout

## Analysis Process

### Step 1: Extract Requirements

Break job description into categories:

**Required (Must-Have)**
- Education requirements
- Years of experience
- Specific technical skills
- Certifications/licenses
- Industry experience

**Preferred (Nice-to-Have)**
- "Bonus" skills
- Advanced certifications
- Domain expertise
- Specific tool experience

**Soft Skills/Culture**
- Communication style
- Work environment
- Team structure
- Company values

### Step 2: Keyword Extraction

Identify three types:

**Hard Skills** (Technical abilities)
- Tools: Salesforce, Python, AWS, Excel
- Methodologies: Agile, Six Sigma, SDLC
- Certifications: PMP, CPA, AWS Certified

**Soft Skills** (Interpersonal)
- Leadership, collaboration, communication
- Problem-solving, critical thinking
- Adaptability, initiative

**Industry/Domain Knowledge**
- B2B SaaS, healthcare, fintech
- Enterprise vs SMB
- Regulatory knowledge (HIPAA, SOX, GDPR)

### Step 3: Calculate Match Score

```
MATCH CALCULATION:

Required Skills:
- User has 8 out of 10 required = 80%

Preferred Skills:
- User has 3 out of 5 preferred = 60%

Overall Match:
- Weight required 70%, preferred 30%
- (80% × 0.7) + (60% × 0.3) = 74%

INTERPRETATION:
90-100% = Overqualified (may be flight risk)
75-89% = Excellent fit (apply immediately)
60-74% = Good fit (apply with strong cover letter)
50-59% = Stretch role (apply if passionate)
<50% = Under-qualified (skip unless dream job)
```

### Step 4: Gap Analysis

For each missing requirement:
- **Critical gap**: Deal-breaker (don't apply)
- **Major gap**: Significant but addressable (mention in cover letter)
- **Minor gap**: Easy to learn (downplay or emphasize related skills)

### Step 5: Red Flag Detection

Scan for warning signs:

**Workload Red Flags:**
- "Wear many hats"
- "Fast-paced environment"
- "Hit the ground running"
- "Self-starter in ambiguous situations"

**Culture Red Flags:**
- "Rockstar/Ninja/Guru"
- "We work hard, play hard"
- "Unlimited vacation"
- "Like a family"

**Compensation Red Flags:**
- "Competitive salary" (won't tell you range)
- "Equity-heavy" (low cash compensation)
- "Commission-based" (no base salary)
- "DOE" with no range

## Match Score Output Format

Structure the analysis report with these sections, in order: header (position/company/location/salary), overall match score + recommendation, requirements breakdown (required/preferred/soft skills with ✅/❌), strengths to emphasize, gaps to address (critical/major/minor with strategy for each), resume customization strategy, cover letter talking points, red flags analysis, application timeline, and decision factors (reasons to apply vs. hesitate, overall recommendation).

See `references/sample-report.md` for a complete worked example of this report format.

## Requirement Classification Guide

Classify each requirement as required vs. preferred based on its language ("must have" vs. "nice to have", frequency of mention, section placement), then flag genuine dealbreakers (missing required license/clearance, degree, or location fit) separately from gaps that are still worth applying through.

See `references/classification-and-edge-cases.md` for the full language cues, dealbreaker criteria, and handling of vague/reposted/internal/multi-role postings.

## Implementation Checklist

When analyzing a job:

1. ✅ Extract all requirements (required vs preferred)
2. ✅ Identify all keywords (hard skills, soft skills, industry terms)
3. ✅ Calculate match score
4. ✅ Identify strengths to emphasize
5. ✅ Identify gaps and strategies to address
6. ✅ Detect red flags
7. ✅ Create resume customization plan
8. ✅ Generate cover letter talking points
9. ✅ Research company
10. ✅ Provide application recommendation and timeline

Edge cases (vague postings, multiple roles in one JD, internal postings, reposted jobs) are covered in `references/classification-and-edge-cases.md`.

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `resume-tailor` | Apply analysis output to customize resume for this role |
| `cover-letter-generator` | Use talking points and gap strategy from analysis |
| `resume-ats-optimizer` | Ensure extracted keywords appear correctly in resume |
| `interview-prep-generator` | Turn identified competencies into STAR story prep |
| `career-changer-translator` | Address skill gaps by reframing transferable experience |
| `salary-negotiation-prep` | Use salary range from JD to anchor negotiation research |
| `meta-research-workflow` | Research company culture and red flags before applying |
