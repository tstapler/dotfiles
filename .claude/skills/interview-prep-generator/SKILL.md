---
name: interview-prep-generator
description: Generate STAR stories, practice questions, and talking points from resume
---

# Interview Prep Generator

## When to Use This Skill

Use this skill when the user wants to:
- Prepare for a job interview
- Practice answering interview questions
- Create STAR stories from their experience
- Anticipate questions for a specific role
- Mentions: "interview prep", "prepare for interview", "STAR stories", "interview questions", "behavioral questions"

## Core Capabilities

- Generate role-specific interview questions
- Create STAR stories from resume bullets
- Predict questions based on job description
- Prepare answers for common questions
- Create talking points for each experience
- Identify potential concerns and prepare responses

## Interview Preparation Framework

### Phase 1: Role Analysis
- Extract likely questions from job description
- Identify skills that will be tested
- Research company interview style

### Phase 2: Story Banking
- Convert resume bullets into STAR stories
- Create stories for common competencies
- Practice concise delivery

### Phase 3: Mock Preparation
- Practice common questions
- Prepare questions to ask
- Research company-specific topics

## The STAR Method Detailed

### Structure
- **S**ituation: Set the context (1-2 sentences)
- **T**ask: Describe your responsibility (1 sentence)
- **A**ction: Explain what YOU did (2-3 sentences)
- **R**esult: Share the outcome with metrics (1-2 sentences)

### STAR Story Template

```
SITUATION: "At [Company], we faced [specific challenge/context]..."

TASK: "I was responsible for [specific ownership]..."

ACTION: "I [specific action 1], [specific action 2], and [specific action 3]..."

RESULT: "As a result, [quantified outcome]. This led to [business impact]."
```

See `references/star-story-examples.md` for a full worked example at the
right level of specificity (90 seconds to 2 minutes spoken).

## Story Banking Process

### Step 1: Identify Core Competencies

**Leadership Stories Needed:**
- Led a team through challenge
- Managed conflict
- Made a difficult decision
- Delegated effectively
- Developed/mentored someone

**Problem-Solving Stories Needed:**
- Solved complex technical problem
- Fixed a process that was broken
- Handled unexpected obstacle
- Made decision with incomplete information
- Improved something proactively

**Collaboration Stories Needed:**
- Worked with difficult colleague
- Aligned cross-functional stakeholders
- Built consensus
- Partnered with other teams
- Influenced without authority

**Achievement Stories Needed:**
- Exceeded goals/expectations
- Delivered under pressure
- Went above and beyond
- Took initiative
- Accomplished something proud of

**Failure/Growth Stories Needed:**
- Made a mistake and learned
- Received critical feedback
- Failed and recovered
- Changed approach based on learning

### Step 2: Map Resume to Stories

For each resume bullet, create a full STAR story. See
`references/star-story-examples.md` for a worked bullet → STAR expansion.

### Step 3: Create Multiple Versions

Each story should have:
- **Full version:** 2 minutes (for "tell me about a time...")
- **Short version:** 60 seconds (for follow-ups)
- **One-liner:** 15 seconds (for "give me an example")

## Common Interview Questions by Category

The full question bank — Behavioral (Leadership, Problem-Solving,
Collaboration, Achievement, Failure/Growth), Role-Specific (PM, Engineering,
Marketing, Sales), Standard ("tell me about yourself" and company/role
questions), and Questions to Ask Interviewers (by audience, plus what to
avoid) — lives in `references/question-bank.md`. Draw from it to predict
questions for a role and pick which stories answer them.

## Handling Difficult Questions

Formulas and model answers for "What's your greatest weakness?", "Why are you
leaving your current job?", "Tell me about a time you failed", and salary
questions live in `references/difficult-questions.md`.

## Output Format

When generating interview prep:

```markdown
# INTERVIEW PREP: [POSITION] AT [COMPANY]

## Role Analysis
**Key competencies they'll test:**
1. [Competency] - Evidence: [From JD]
2. [Competency] - Evidence: [From JD]
3. [Competency] - Evidence: [From JD]

## Predicted Questions

### High Probability (prepare thoroughly)
1. [Question] → Use story: [Story name]
2. [Question] → Use story: [Story name]
3. [Question] → Use story: [Story name]

### Medium Probability
1. [Question]
2. [Question]

## Your STAR Story Bank

### Story 1: [Name - e.g., "Product Launch Success"]
**Use for:** Leadership, Achievement, Cross-functional
**STAR:**
- S: [Situation]
- T: [Task]
- A: [Action]
- R: [Result with metrics]
**Short version:** [60 second version]

### Story 2: [Name]
[Same structure]

## "Tell Me About Yourself" Script
[2-minute pitch tailored to this role]

## Questions to Ask
**For Hiring Manager:**
1. [Question]
2. [Question]

**For Team:**
1. [Question]
2. [Question]

## Company Research Notes
- Recent news: [Item]
- Key facts to reference: [Facts]
- Potential concerns: [Items to be ready for]

## Red Flag Answers to Avoid
- Don't mention: [Topics]
- Don't criticize: [Past employer aspects]
- Watch out for: [Potential trap questions]
```

## Implementation Checklist

For complete interview prep:
1. ✅ Analyze job description for competencies
2. ✅ Create 8-10 STAR stories covering all competencies
3. ✅ Write "tell me about yourself" pitch
4. ✅ Prepare answers for likely questions
5. ✅ Research company thoroughly
6. ✅ Prepare thoughtful questions to ask
7. ✅ Practice out loud (time yourself)
8. ✅ Prepare logistics (outfit, route, tech check)
9. ✅ Review the day before interview
10. ✅ Send thank you notes after

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `job-description-analyzer` | Identify which competencies will be tested before prepping |
| `resume-tailor` | Align resume stories to the specific role beforehand |
| `cover-letter-generator` | Use cover letter talking points as interview anchor stories |
| `salary-negotiation-prep` | Prepare to handle compensation questions in final rounds |
| `career-changer-translator` | Prepare answers explaining an industry transition |
| `meta-research-workflow` | Research company news, products, and culture for "why us?" |
