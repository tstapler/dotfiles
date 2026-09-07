---
name: offer-comparison-analyzer
description: Compare multiple job offers side-by-side with total compensation analysis
---

# Offer Comparison Analyzer

## When to Use This Skill

Use this skill when the user:
- Has multiple job offers to compare
- Needs to evaluate total compensation
- Wants to make a data-driven job decision
- Is weighing different opportunities
- Mentions: "compare offers", "multiple offers", "which job", "offer comparison", "deciding between jobs"

## Core Capabilities

- Compare total compensation across offers
- Evaluate non-monetary factors
- Create weighted decision frameworks
- Calculate true offer value
- Identify hidden costs and benefits
- Guide the decision-making process

## The Comparison Challenge

**The Problem:** 
Comparing offers is hard because:
- Different compensation structures
- Non-monetary factors matter
- Hidden benefits and costs
- Emotional factors cloud judgment
- Information asymmetry

**The Solution:**
Systematic comparison framework that considers:
- Total compensation (not just salary)
- Career growth potential
- Work-life factors
- Risk assessment
- Personal values alignment

## Total Compensation Calculator

### Components to Include

**Cash Compensation:**
- Base salary
- Signing bonus (one-time)
- Annual bonus (target %)
- Commission (for sales roles)
- Relocation assistance

**Equity Compensation:**
- Stock options (value = current price - strike price)
- RSUs (value = current price × shares)
- Vesting schedule
- Refresh grant expectations

**Benefits Value:**
- Health insurance (employer contribution)
- 401(k) match
- HSA/FSA contributions
- Life/disability insurance
- Other insurance benefits

**Perks Value:**
- Vacation days (can assign $ value)
- Remote work (saves commute costs)
- Professional development budget
- Equipment/office stipend
- Meals, gym, etc.

See `references/worked-examples.md` for a full worked calculation template and side-by-side comparison table example.

## Non-Monetary Factor Framework

### Career Growth (Weight: High)

**Questions to Consider:**
- Which role offers more learning?
- Which company/brand helps future job search?
- Which has better promotion track?
- Which offers more scope/responsibility?
- Which manager will develop you more?

Score each on a 1-10 scale per question and average them — see `references/worked-examples.md` for a scored example.

### Work-Life Balance (Weight: Personal)

**Factors:**
- Expected hours
- Remote/hybrid flexibility
- Vacation usage culture
- On-call requirements
- Travel requirements
- Commute time

### Team & Culture (Weight: High)

**Factors:**
- Manager quality (crucial!)
- Team health/dynamics
- Company culture fit
- DEI considerations
- Company stability/growth
- Values alignment

### Risk Assessment (Weight: Medium)

**Startup vs. Established:**
- Funding runway
- Market position
- Company trajectory
- Equity risk (could be worth $0)

**Questions:**
- What happens if company struggles?
- How stable is this role?
- What's the severance policy?

## Weighted Decision Matrix

1. **Define priorities** — assign each factor (compensation, career growth, work-life balance, team/culture, location) a weight that sums to 100%, based on what the user says matters most.
2. **Score each offer** 1-10 per factor.
3. **Calculate the weighted score** — sum of `score × weight` per offer, then compare totals.

See `references/worked-examples.md` for a fully worked weighting, scoring, and calculation example.

## Red Flags to Watch

### In the Offer

- ❌ Vague bonus language ("up to 20%")
- ❌ Equity with no liquidity path
- ❌ High base but no equity (at startup)
- ❌ Cliff longer than 1 year
- ❌ Vesting acceleration absent
- ❌ Non-compete restrictions
- ❌ Verbal promises not in writing

### About the Company

- ❌ High turnover (check LinkedIn)
- ❌ Recent layoffs or reorgs
- ❌ Manager seems checked out
- ❌ Glassdoor patterns in bad reviews
- ❌ Funding concerns
- ❌ Unclear path to profitability

### About the Role

- ❌ Vague responsibilities
- ❌ Role seems to change during interviews
- ❌ Red flags in why position is open
- ❌ No growth path discussed
- ❌ Unrealistic expectations set

## Questions to Ask Yourself

### The Gut Check
- Which offer excites me more?
- Which would I regret not taking?
- Which aligns with my 5-year goals?
- Which would I brag about to friends?

### The Monday Morning Test
- Which job do I want to wake up for?
- Which team do I want to work with?
- Which problems do I want to solve?

### The Learning Test
- Where will I grow more?
- Which skills will I develop?
- Which looks better on my resume in 3 years?

### The Risk Test
- What's the downside of each?
- Which failure would I regret more?
- What's my backup plan for each?

## Output Format

Report offers being compared, total compensation comparison table, non-monetary comparison table, weighted analysis scores, key differences, a recommendation with reasons, open questions to clarify, and negotiation opportunities.

See `references/output-report-template.md` for the ready-to-fill template.

## Comparison Checklist

- ✅ Calculated total comp (not just base)
- ✅ Included equity with realistic valuation
- ✅ Factored in benefits value
- ✅ Considered tax implications
- ✅ Weighted non-monetary factors
- ✅ Assessed career growth potential
- ✅ Evaluated team and manager quality
- ✅ Checked company stability/risk
- ✅ Aligned with personal priorities
- ✅ Gut-checked the decision

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `salary-negotiation-prep` | Negotiate whichever offer(s) have room to improve |
| `job-description-analyzer` | Re-analyze each JD to compare role scope and fit |
| `interview-prep-generator` | Prepare final-round questions to clarify offer details |
| `meta-research-workflow` | Research company stability, culture, and Glassdoor signals |
