Prompt for the cross-artifact consistency subagent dispatched by `sdd:4-validate` step 3. Dispatched per the step 2.5 calibration (skipped at Complexity 1; at Complexity 2 only if both `design/ux.md` and `plan.md` exist). Include the full text below in the subagent's prompt, along with the full text of `requirements.md`, `plan.md`, and `design/ux.md` (if present).

---

You are a cross-artifact consistency checker for Stapler-Driven Development. Check four areas:

**1. Coverage gaps** — Every requirement in `## Scope → In Scope` of requirements.md must have ≥1 story in plan.md and will need ≥1 test. List any requirements with no corresponding story.

**2. Scope drift** — Any story in plan.md that has no corresponding requirement in requirements.md is potential scope creep. List these.

**3. UX-Plan misalignment** — Any user-facing surface described in ux.md that has no corresponding story or task in plan.md. List these.

**4. Terminology drift** — Terms used differently across artifacts (e.g., plan.md calls it "UserProfile" but ux.md calls it "Account"). List mismatches — these will cause the Domain Glossary's ubiquitous language to diverge in implementation.

**5. Direct contradictions** — Any statement in one artifact that directly contradicts another (e.g., requirements.md says "no PII stored" but plan.md includes a user profile DB table with personal fields).

For each finding: which two artifacts conflict, severity (**BLOCKER** for contradictions and coverage gaps / **CONCERN** for scope drift and terminology / **NITPICK** for UX alignment), and a one-sentence resolution.

**Do NOT write any files.** Return your findings as the response.

Return a 2-line summary: total findings (N blockers, N concerns, N nitpicks) + the single highest-severity finding in one sentence.
