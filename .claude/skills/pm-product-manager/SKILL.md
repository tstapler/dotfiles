---
name: pm-product-manager
description: >
  Apply evidence-based product management to roadmap decisions, feature prioritization,
  discovery research, PRD writing, and success metrics. Use when the user asks about
  what to build next, how to prioritize features, how to define a feature, how to
  measure success, or how to communicate product decisions. Grounded in Marty Cagan
  (Inspired/Empowered), Teresa Torres (Continuous Discovery Habits), Ryan Singer
  (Shape Up), Clayton Christensen (JTBD), and Jeff Patton (User Story Mapping).
---

# Product Manager

Evidence-based product management grounded in research on what makes software products
excellent and beloved. The core belief (Cagan): **outcomes over output** — the goal is
not to ship features but to solve real problems in ways users love, that work for the
business.

---

## The Four Big Risks (Marty Cagan — *Inspired*)

Every feature must address all four before committing:

| Risk | Question | Who owns it |
|------|----------|-------------|
| **Value** | Will users actually want this? | Discovery |
| **Usability** | Can users figure out how to use it? | UX/Design |
| **Feasibility** | Can we build it with current tech/time? | Engineering |
| **Viability** | Does it work for our business? | PM/Leadership |

Reject or reshape any feature that hasn't de-risked all four.

---

## Workflow 1: Discovery — Finding the Right Problem

Based on Teresa Torres *Continuous Discovery Habits*:

### Opportunity Solution Tree (OST)
```
Desired Outcome (North Star)
  └── Opportunity 1 (unmet need / pain / JTBD)
       ├── Solution A → Experiment A1, A2
       └── Solution B → Experiment B1
  └── Opportunity 2
       └── Solution C → Experiment C1
```

1. **Start with one desired outcome** — a measurable user/business result, not a feature.
2. **Map opportunities** through continuous user interviews (Torres: at minimum weekly).
3. **Generate multiple solutions per opportunity** before committing to any.
4. **Run the smallest possible experiment** to test assumptions before building.

### Jobs To Be Done lens (Christensen/Ulwick)
- Ask: *"What job is the user hiring this product/feature to do?"*
- Separate the functional job ("transfer a file"), emotional job ("feel in control"), and social job ("look competent to colleagues").
- The best features serve a job that is important, underserved, and clearly defined.

### Interview protocol
- Minimum: 30-minute sessions, weekly cadence
- Focus on past behaviour, not hypothetical preferences ("Tell me about the last time you…")
- Extract: context, motivation, friction, outcome sought
- Never ask users what features they want — ask what problems they face

---

## Workflow 2: Prioritization — What to Build Next

### RICE Scoring (Intercom)
```
RICE = (Reach × Impact × Confidence) / Effort
```
| Factor | Definition | Scale |
|--------|-----------|-------|
| **Reach** | Users affected per period | Absolute number |
| **Impact** | Effect on the metric | 3=massive, 2=high, 1=medium, 0.5=low, 0.25=minimal |
| **Confidence** | Evidence quality | 100%=high, 80%=medium, 50%=low |
| **Effort** | Person-months | Absolute number |

Higher RICE = higher priority. Use for comparing independent features.

### Kano Model (Noriaki Kano)
Classify every proposed feature before scoring:

- **Basic expectations** (must-haves): Absence causes dissatisfaction; presence is invisible. Never cut these.
- **Performance satisfiers**: More = better satisfaction. Prioritize by ROI.
- **Delighters**: Unexpected; create delight when present, no harm when absent. Reserve for after basics are solid.
- **Indifferent**: Users don't care. Avoid.
- **Reverse**: Presence actively annoys some users. Research carefully.

### MoSCoW for release scoping
- **Must**: Non-negotiable for this release
- **Should**: High value, include if possible
- **Could**: Nice to have, cut first under pressure
- **Won't**: Explicitly out of scope (document why)

### Shape Up appetite (Ryan Singer — *Shape Up*)
Before prioritising, set the **appetite** — the maximum time worth spending:
- Small batch: 1–2 weeks
- Large batch: up to 6 weeks (a "bet")

If a solution can't fit the appetite, either narrow the problem or reject it. **Never expand the appetite to fit a solution.**

---

## Workflow 3: Shaping — Defining What to Build

### The Shape Up shaping process
1. **Set the appetite** first (see above)
2. **Find the elements**: rough UI sketches, key interactions — not wireframes, not specs
3. **Identify rabbit holes**: what could go wrong, what's technically uncertain, what's undefined
4. **Patch the holes**: make explicit calls on edge cases before pitching
5. **Write the pitch**: problem, appetite, solution sketch, rabbit holes addressed, no-gos

### PRD structure (lean, outcome-oriented)
See `templates/prd-template.md` for full template.

Key sections:
- **Problem statement**: Who has what problem in what context, and what's the evidence?
- **Desired outcome**: What measurable change in user behaviour or metric are we targeting?
- **Proposed solution**: Sketched, not over-specified
- **Success criteria**: How will we know it worked?
- **Out of scope**: Explicit exclusions
- **Open questions**: What must be resolved before or during build

---

## Workflow 4: Roadmap Management

### Outcome-based roadmap (not feature roadmap)
| Now | Next | Later |
|-----|------|-------|
| Committed, scoped bets | Shaped, prioritised, awaiting a cycle | Opportunities under consideration |

Each item is an **outcome or problem to solve**, not a feature name. Feature names lock in solutions before discovery.

### Roadmap health checks
- Is every "Now" item tied to a measurable outcome? If not, why are we building it?
- Does the "Later" column contain items older than 6 months? Re-evaluate or discard.
- Are we balancing new features vs. quality/reliability? (Recommended: 70/30 or 80/20 new vs. investment)
- Are engineering and design involved in shaping before items enter "Now"?

### Sequencing principles
1. **Dependency order**: Unblock other items first
2. **Risk-highest first**: Tackle the riskiest assumption early — fail fast
3. **User journey coherence**: Ship complete experiences, not feature fragments
4. **Technical leverage**: Items that enable many future items cheaply

---

## Workflow 5: Metrics — Measuring Success

### North Star Metric (Sean Ellis / Amplitude)
One metric that best captures the value users get from the product.
- Must be **leading** (predicts retention/growth), not lagging
- Must reflect **user value**, not business value
- Examples: "books successfully downloaded per week", "% of sessions ending in file save"

Supporting metrics:
- **Input metrics**: Levers the team controls that drive the North Star
- **Counter-metrics**: Guard rails to prevent gaming (e.g. don't optimise downloads at the cost of abuse)

### HEART framework (Google — Kerry Rodden)
For feature-level success:

| Dimension | Measures | Example metric |
|-----------|---------|----------------|
| **Happiness** | User satisfaction | CSAT, NPS, survey |
| **Engagement** | Depth of interaction | Sessions per user, actions per session |
| **Adoption** | New users / feature uptake | % users using feature |
| **Retention** | Users returning | 30-day retention rate |
| **Task Success** | Completion, errors, time | Completion rate, error rate |

Pick 1–2 HEART dimensions per feature. Don't measure all five.

### OKRs (Objectives and Key Results)
- **Objective**: Qualitative, inspiring direction ("Users can reliably download any book they have access to")
- **Key Results**: 3–5 measurable outcomes, not tasks ("Download success rate > 95%", "Zero user-reported silent failures in 30 days")
- KRs are outcomes, never outputs. "Ship feature X" is not a KR.

---

## Key Principles (Never Violate)

1. **Outcome over output** (Cagan): A shipped feature that doesn't change behaviour is waste.
2. **Continuous discovery** (Torres): Weekly user contact is not optional; it's the job.
3. **Appetite-first** (Singer): Budget time before designing solutions.
4. **Four risks** (Cagan): Value, usability, feasibility, viability — validate all before building.
5. **Smallest experiment** (Ries): The fastest way to learn is not to build the full feature.
6. **Basic expectations first** (Kano): Delight is irrelevant if basics are broken.
7. **Problems, not solutions** (Torres/Christensen): Users describe pain, not features. Translate pain into opportunity.

---

## Anti-Patterns to Call Out

- ❌ **Feature factory**: Shipping features without measuring outcomes
- ❌ **HiPPO-driven roadmap**: Highest-paid person's opinion overrides evidence
- ❌ **Solution-first thinking**: "We should build X" without an articulated problem
- ❌ **Fake agile**: Two-week sprints delivering predetermined features, no discovery
- ❌ **Vanity metrics**: Downloads, pageviews, sign-ups without engagement evidence
- ❌ **Everything is Must**: If everything is critical, nothing is
- ❌ **Roadmap as promise**: Treat roadmap as a communication tool about priorities, not a delivery commitment

---

## For This Project (internet_archive_downloader)

Context-specific guidance:

- **Users**: People who want to save Archive.org and HathiTrust books locally
- **Core job**: "When I borrow a book I can't keep, help me save it before the loan expires"
- **North Star candidate**: Weekly successful downloads per active user
- **Current quality investments**: Bug fixes improving reliability are basic expectations — ship these before new features
- **Feature backlog signal**: Silent failures (BUG-004/005/006) were invisible to users; any new feature should have explicit error surfaces

---

## Progressive Context

For detailed framework references and scoring worksheets: `frameworks.md`
For PRD template: `templates/prd-template.md`
For roadmap item template: `templates/roadmap-item.md`
For feature brief template: `templates/feature-brief.md`
