---
name: salary-negotiation-prep
description: Research market rates, build negotiation strategy, and create counter-offer scripts
---

# Salary Negotiation Prep

## When to Use This Skill

Use this skill when the user wants to:
- Negotiate a job offer or salary
- Research market rates for their role
- Create a counter-offer strategy
- Understand total compensation packages
- Mentions: "salary negotiation", "negotiate offer", "counter offer", "compensation", "how much should I ask for"

## Core Capabilities

- Research and validate market compensation
- Build negotiation strategy and scripts
- Calculate total compensation (not just base salary)
- Prepare counter-offer responses
- Identify negotiation leverage points
- Navigate difficult salary conversations

## The Negotiation Mindset

**Key Principles:**
1. Negotiation is expected - companies budget for it
2. 84% of employers expect candidates to negotiate
3. Not negotiating leaves $500K-$1M on the table over a career
4. The goal is win-win, not adversarial

**What You're Really Negotiating:**
Base salary, signing bonus, annual bonus/commission, equity (stock options, RSUs), benefits (401k match, insurance), perks (vacation, remote work, professional development), start date, title.

## Research Phase

### Step 1: Determine Market Rate

**Sources to Check:** Levels.fyi (best for tech), Glassdoor (general, take with grain of salt), LinkedIn Salary, Blind (anonymous reports), PayScale, Salary.com, H1B salary data (publicly available).

**Build a Range:**
```
Low (25th percentile): $XXX,XXX
Target (50th percentile): $XXX,XXX
High (75th percentile): $XXX,XXX
Stretch (90th percentile): $XXX,XXX
```

### Step 2: Know Your Value

**Factors That Increase Your Worth:** years of relevant experience, specialized/rare skills, track record of results, in-demand certifications, current competing offers, referral from employee, market demand in your field.

**Factors That May Limit:** entry level or career change, less experience than ideal candidate, gaps in required skills, location arbitrage (lower cost of living).

### Step 3: Calculate Total Compensation

**Total Comp = Base + Bonus + Equity + Benefits**

```
EXAMPLE:
Base Salary: $150,000
Target Bonus (15%): $22,500
RSU Grant (4-year): $200,000 ($50,000/year)
401k Match (4%): $6,000
Benefits Value: ~$15,000

Total Annual Comp: $243,500
```

**Common Equity Terms:**
- **RSUs:** Restricted Stock Units (real shares, taxed when vesting)
- **Options:** Right to buy at strike price (value = current price - strike price)
- **Vesting:** Typically 4-year with 1-year cliff
- **Refresh grants:** Annual additional equity grants

## Negotiation Strategy

### When to Negotiate

**Best Time:** After you have a written offer, before you sign

**Timeline:** receive verbal offer (express enthusiasm, ask for written offer) → receive written offer (thank them, ask for time to review) → research and prepare (24-48 hours) → counter with ask (email or call) → discussion/back and forth (may take several rounds) → final agreement (get in writing). See `references/scripts.md` for the negotiation timeline template and ready-to-use email/call scripts.

### The Counter-Offer Framework

**Structure:**
1. Express enthusiasm
2. Reinforce your value
3. Make specific ask
4. Provide justification
5. Open discussion

For situational scripts — a low first offer, being asked for salary expectations first, a firm base salary, competing offers, or illegal current-salary questions — see `references/scenarios.md`.

## Negotiation Tactics

### Do's:
- Always negotiate (respectfully)
- Get the offer in writing before negotiating
- Research thoroughly
- Be specific with numbers
- Express genuine enthusiasm
- Give them a way to say yes
- Consider total compensation
- Be patient - process takes time
- Get final agreement in writing

### Don'ts:
- Accept on the spot
- Give a salary history (if not required by law)
- Make ultimatums
- Lie about competing offers
- Be rude or aggressive
- Negotiate just for the sake of it
- Accept verbal promises without writing
- Burn bridges if it doesn't work out

## Comparing Multiple Offers

When there's more than one offer to weigh, build a side-by-side total-compensation table. See `references/comparison-example.md` for a worked example; use the `offer-comparison-analyzer` skill for a full multi-offer decision.

## Output Format

When preparing salary negotiation:

```markdown
# SALARY NEGOTIATION STRATEGY

## Market Research Summary
**Role:** [Title]
**Location:** [City/Remote]
**Experience Level:** [Years]

**Market Range:**
- 25th percentile: $XXX,XXX
- 50th percentile: $XXX,XXX (target)
- 75th percentile: $XXX,XXX
- 90th percentile: $XXX,XXX (stretch)

**Sources:** [List sources used]

## Their Offer
| Component | Amount |
|-----------|--------|
| Base | $XXX,XXX |
| Bonus | X% |
| Equity | $XXX,XXX |
| Signing | $XXX |
| Total Year 1 | $XXX,XXX |

## Your Counter
| Component | Ask | Justification |
|-----------|-----|---------------|
| Base | $XXX,XXX | [Why] |
| Signing | $XXX | [Why] |
| [Other] | | |

## Counter-Offer Script
[Email template or call script customized for this situation]

## If They Push Back
**Plan B:** [Alternative elements to negotiate]
**Walk-away Point:** [Your minimum]

## Key Talking Points
1. [Your experience/value point]
2. [Market data point]
3. [Specific achievement]

## Questions to Clarify
- [Equity vesting schedule?]
- [Bonus guaranteed?]
- [Review cycle timeline?]
```

## Implementation Checklist

1. Research market rate from 3+ sources
2. Calculate total compensation (not just base)
3. Identify your priorities
4. Determine walk-away point
5. Prepare counter-offer with justification
6. Write or practice negotiation script
7. Plan for pushback scenarios
8. Get agreement in writing
9. Review final offer letter carefully
10. Sign and celebrate!

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `offer-comparison-analyzer` | Compare total compensation before choosing which offer to negotiate |
| `job-description-analyzer` | Use published salary range from JD as baseline research data |
| `interview-prep-generator` | Prepare for salary discussion questions in final interview rounds |
| `meta-research-workflow` | Research market rates via Levels.fyi, Glassdoor, and H1B data |
