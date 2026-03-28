# Framework Reference

Detailed reference for frameworks mentioned in SKILL.md.

---

## Opportunity Solution Tree (Teresa Torres)

```
                    [Desired Outcome]
                          │
          ┌───────────────┼───────────────┐
          │               │               │
    [Opportunity 1] [Opportunity 2] [Opportunity 3]
          │               │
    ┌─────┴─────┐   ┌─────┴─────┐
    │           │   │           │
[Solution A] [Solution B] [Solution C] [Solution D]
    │                           │
[Experiment 1]            [Experiment 2]
[Experiment 2]            [Experiment 3]
```

**How to build it**:
1. Define one desired outcome (a measurable change in user/business behaviour)
2. Conduct weekly interviews → extract opportunities (needs, pains, desires)
3. Cluster opportunities by theme; identify which to address this cycle
4. Brainstorm ≥3 solutions per opportunity before evaluating any
5. Map assumptions → design smallest experiment to test biggest assumption
6. Build only after experiments de-risk key assumptions

**Common mistakes**:
- Jumping straight to solutions (skipping opportunities)
- Having only one solution per opportunity
- Treating the tree as a document, not a living artefact
- Conducting interviews to validate pre-chosen solutions

---

## RICE Scoring Worksheet

```
Feature: _______________________________________________

Reach:       ________ users per quarter affected
Impact:      ________ (3=massive, 2=high, 1=medium, 0.5=low, 0.25=minimal)
Confidence:  ________% (100=data-backed, 80=some evidence, 50=gut feel)
Effort:      ________ person-months

RICE = (Reach × Impact × Confidence%) / Effort = ________
```

**Calibration tips**:
- Reach: use actual analytics, not guesses
- Impact: estimate relative to your most important metric
- Confidence: be honest — most new features are 50–70%
- Effort: get engineering estimate before scoring, not after

---

## Kano Survey Technique

For each feature, ask two questions:
1. "If this feature **were present**, how would you feel?" (Functional form)
2. "If this feature **were absent**, how would you feel?" (Dysfunctional form)

Answers: Delighted / Expect it as a matter of course / Neutral / Can live with it / Dislike it

**Interpretation matrix**:

| Functional \ Dysfunctional | Delighted | Expect | Neutral | Live with | Dislike |
|---------------------------|-----------|--------|---------|-----------|---------|
| **Delighted** | Q | Delighter | Delighter | Delighter | Performance |
| **Expect** | Reverse | Indifferent | Indifferent | Indifferent | Basic |
| **Neutral** | Reverse | Indifferent | Indifferent | Indifferent | Basic |
| **Live with** | Reverse | Indifferent | Indifferent | Indifferent | Basic |
| **Dislike** | Reverse | Reverse | Reverse | Reverse | Basic |

**What to do by category**:
- Basic: Must have; fix immediately if broken; don't over-invest
- Performance: Prioritise by ROI; linear return on investment
- Delighter: Include opportunistically; high value per effort when basics are solid
- Indifferent: Drop immediately
- Reverse: Investigate segment carefully before building

---

## Shape Up Pitch Template (Ryan Singer)

```
# [Feature/Problem Name]

## Problem
[1–3 sentences: who experiences this, when, what goes wrong]

## Appetite
[ ] Small batch (1–2 weeks)  [ ] Large batch (up to 6 weeks)

## Solution
[Fat-marker sketches, key screens, key interactions — NOT wireframes]

Key elements:
- [Element 1]
- [Element 2]
- [Element 3]

## Rabbit Holes
What could go wrong / what's technically uncertain:
- [Risk 1] → Mitigation: [how we addressed it]
- [Risk 2] → Mitigation: [how we addressed it]

## No-gos
Explicitly out of scope for this bet:
- [Exclusion 1]
- [Exclusion 2]
```

**Betting table checklist** (before committing to a cycle):
- [ ] Does the team have capacity?
- [ ] Is the pitch fully shaped (no rabbit holes unaddressed)?
- [ ] Have all four risks been considered?
- [ ] Is the appetite firm, not a floor?
- [ ] Is there a clear problem statement, not just a solution?

---

## OKR Structure

```
Objective: [Qualitative, inspiring, time-bound direction]

  Key Result 1: [Measurable outcome — number, %, rate]
  Key Result 2: [Measurable outcome]
  Key Result 3: [Measurable outcome]

  Initiatives (NOT KRs):
  - [Project/feature that contributes to KRs]
  - [Project/feature that contributes to KRs]
```

**OKR quality test**:
- Can the team hit the KR without building anything? (Good — proves it measures outcome, not output)
- Is each KR binary (hit/miss)? Consider using ranges: 0.7 = stretch achieved, 1.0 = exceptional
- Do any KRs conflict with each other? (Counter-metric check)

**Typical cadence**:
- Company OKRs: Annual + Quarterly
- Team OKRs: Quarterly
- Review: Weekly check-in on leading indicators; monthly formal review

---

## HEART Metrics Planning

```
Feature: _______________________________________________
Goal of feature: _______________________________________

Selected HEART dimensions (choose 1–2):

[ ] Happiness
    Signal: ___________________________________________
    Metric: ___________________________________________

[ ] Engagement
    Signal: ___________________________________________
    Metric: ___________________________________________

[ ] Adoption
    Signal: ___________________________________________
    Metric: ___________________________________________

[ ] Retention
    Signal: ___________________________________________
    Metric: ___________________________________________

[ ] Task Success
    Signal: ___________________________________________
    Metric: ___________________________________________

Counter-metric (what not to break): ___________________
Measurement method: ___________________________________
Measurement cadence: __________________________________
```

---

## Jobs To Be Done Interview Guide

**Goal**: Understand the job, not the feature request.

### Recruiting criteria
- Users who have done the target job recently (within 30–90 days)
- Mix of successful completions and failures/workarounds

### Interview arc
1. **Warm-up** (5 min): Context, how they found the product, general usage
2. **First use / switch moment** (10 min): What prompted them to try this? What were they doing before?
3. **Struggling moment** (10 min): Tell me about the last time this was hard. What did you do?
4. **Success moment** (5 min): Tell me about a time it worked really well. What was different?
5. **Wrap-up** (5 min): What's the one thing you'd change?

### Questions that reveal the job
- "What were you trying to accomplish when you did that?"
- "What happened just before you decided to [do X]?"
- "What would you have done if [product] didn't exist?"
- "When does this not work? What do you do then?"
- "Who else is affected when this goes well/badly for you?"

### What to capture
| Category | Examples |
|----------|---------|
| Functional job | "Save the book before the loan expires" |
| Emotional job | "Feel like I haven't lost access permanently" |
| Social job | "Not feel like I'm technically incompetent" |
| Context | "At night, when I'm about to lose access" |
| Constraints | "I can't always predict when the loan will expire" |
| Workarounds | "I screenshot every page manually" |
| Hiring criteria | "I chose this because it was the only option I found" |

---

## Sources

- Cagan, M. *Inspired: How to Create Tech Products Customers Love* (2nd ed., 2018)
- Cagan, M. *Empowered: Ordinary People, Extraordinary Products* (2020)
- Torres, T. *Continuous Discovery Habits* (2021)
- Singer, R. *Shape Up: Stop Running in Circles and Ship Work that Matters* (2019) — free at basecamp.com/shapeup
- Christensen, C. *The Innovator's Dilemma* (1997); Ulwick, A. *Jobs to Be Done* (2016)
- Patton, J. *User Story Mapping* (2014)
- Ries, E. *The Lean Startup* (2011)
- Kano, N. et al. "Attractive quality and must-be quality" *Journal of the Japanese Society for Quality Control* (1984)
- Rodden, K. et al. "Measuring the User Experience on a Large Scale: User-Centered Metrics for Web Applications" *CHI* (2010)
