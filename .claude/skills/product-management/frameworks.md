# Prioritization Frameworks

Use these frameworks when ranking features, analyzing trade-offs, or deciding what to build next.

## RICE Scoring

**Best for**: Comparing features with different scales of impact and effort.

| Factor | Definition | Scale |
|--------|-----------|-------|
| **Reach** | How many users/events per time period | Numeric (e.g., 500 users/quarter) |
| **Impact** | Effect on each user reached | 3 = massive, 2 = high, 1 = medium, 0.5 = low, 0.25 = minimal |
| **Confidence** | How sure are you about estimates | 100% = high, 80% = medium, 50% = low |
| **Effort** | Person-months (or person-weeks for solo dev) | Numeric (e.g., 2 weeks) |

**Formula**: `RICE = (Reach x Impact x Confidence) / Effort`

**Solo dev adaptation**: Use person-days for Effort. Reach can be "times I encounter this problem per week" for internal tools.

### Scoring Process

1. List all candidate features
2. Estimate each factor independently (avoid anchoring)
3. Be honest about Confidence -- low confidence = research first, don't build
4. Score and rank
5. Sanity check: does the ranking feel right? If not, revisit assumptions

## ICE Scoring

**Best for**: Quick gut-check prioritization when RICE feels heavy.

| Factor | Definition | Scale |
|--------|-----------|-------|
| **Impact** | How much will this move the needle | 1-10 |
| **Confidence** | How sure are you | 1-10 |
| **Ease** | How easy to implement | 1-10 |

**Formula**: `ICE = Impact x Confidence x Ease`

Use ICE for initial triage, then switch to RICE for the top candidates.

## MoSCoW Method

**Best for**: Scoping a specific release or milestone.

| Category | Meaning | Rule |
|----------|---------|------|
| **Must have** | Non-negotiable for this release | Without these, the release has no value |
| **Should have** | Important but not critical | Can be deferred to next release if needed |
| **Could have** | Desirable, low effort | Include if time permits |
| **Won't have (this time)** | Explicitly excluded | Documented for future consideration |

**Rules**:
- Must haves should be no more than 60% of total effort
- Every feature in "Must" should survive the question: "Would we delay the release for this?"
- "Won't have" is as important as "Must have" -- it prevents scope creep

## Kano Model

**Best for**: Understanding user satisfaction curves for different feature types.

| Type | Absent | Present | Examples |
|------|--------|---------|----------|
| **Basic (Must-be)** | Dissatisfaction | No extra satisfaction | Login works, data doesn't corrupt |
| **Performance (One-dimensional)** | Less satisfied | More satisfied | Speed, storage capacity |
| **Delighter (Attractive)** | No dissatisfaction | High satisfaction | Smart defaults, auto-complete |
| **Indifferent** | No effect | No effect | Backend refactor users never see |
| **Reverse** | Satisfied | Dissatisfied | Unwanted notifications |

**Application**: Ensure all Basics are covered first. Invest in Performance features proportionally. Add Delighters sparingly for differentiation.

## Jobs-to-be-Done (JTBD)

**Best for**: Understanding WHY users want something, beyond surface requests.

### Job Statement Format

> When [situation], I want to [motivation], so I can [expected outcome].

### Decomposition

| Layer | Question | Example |
|-------|----------|---------|
| **Functional job** | What are they trying to accomplish? | "Merge wiki changes without conflicts" |
| **Emotional job** | How do they want to feel? | "Confident my notes are safe" |
| **Social job** | How do they want to be perceived? | N/A for solo tools |
| **Related jobs** | What else are they doing around this? | "Searching past notes", "syncing across devices" |

### Outcome Statements

> [Direction] + [metric] + [object of control] + [context]

Example: **Minimize** the **time** it takes to **find a past note** when **researching a topic**.

Use outcome statements as success metrics in PRDs.

## Trade-Off Analysis

**Best for**: Choosing between competing approaches.

### Structure

```
## Option A: [Name]
- **Pros**: [list]
- **Cons**: [list]
- **Effort**: [estimate]
- **Risk**: [what could go wrong]
- **Reversibility**: [one-way door / two-way door]

## Option B: [Name]
- [same structure]

## Recommendation
- **Choice**: [A or B]
- **Rationale**: [why, referencing specific pros/cons]
- **Mitigation**: [how to address the chosen option's cons]
```

### Decision Criteria

Rank these by importance for each decision:

1. **User impact** - Which option better serves the user's job?
2. **Time to value** - Which gets value to users sooner?
3. **Reversibility** - Can we change our mind later?
4. **Complexity cost** - What ongoing maintenance does this create?
5. **Learning value** - Which teaches us more about our assumptions?