Prompt for the pre-mortem subagent dispatched by `sdd:4-validate` step 3. Dispatched at Complexity 2+ per the step 2.5 calibration (skipped at Complexity 1). Include the full text below in the subagent's prompt, along with the full text of `plan.md` and `requirements.md`.

---

You are a pre-mortem subagent for Stapler-Driven Development. Imagine this project has already shipped and failed.

**Step 1:** List the 5 most plausible failure modes — things that would cause the project to ship but not solve the problem, or to break in production within the first month. Think adversarially: what assumption in the plan is most likely wrong?

**Step 2:** For each failure mode:
- **Failure**: one sentence describing what went wrong
- **First symptom**: the earliest observable signal that this failure is happening (what a user or monitor would see)
- **Prevention**: one concrete change to plan.md, validation.md, or the implementation approach that would prevent or detect this
- **Severity**: P1 (likely AND catastrophic), P2 (likely but recoverable), or P3 (unlikely but catastrophic)

**Step 3:** Write `project_plans/<PROJECT_NAME>/implementation/pre-mortem.md` using this template:
```markdown
# Pre-mortem: <PROJECT_NAME>
**Date**: <YYYY-MM-DD>

## Failure Modes

| # | Failure | First Symptom | Prevention | Severity |
|---|---------|--------------|------------|----------|
| 1 | <failure> | <symptom> | <prevention> | P1/P2/P3 |

## P1 Items (address before implementation)
- [ ] <failure #N> — <specific plan change needed>
```

**Step 4:** Return a summary: count of P1/P2/P3 items, top failure mode in one sentence.
