---
description: Shipping readiness gate — parallel swarm across plan compliance, architecture,
  code quality, tests, security, product/UX, and operational readiness. Produces a
  GO / HOLD / FIX-THEN-SHIP verdict.
prompt: "# Is It Ready? — Shipping Readiness Review\n\nRun a parallel swarm of specialized\
  \ reviewers against the current changes to produce a single, evidence-backed shipping\
  \ decision.\n\n**Scope**: `${1:-current git changes}` — defaults to `git diff HEAD`\
  \ (staged + unstaged). Pass a path, branch ref, or commit range to narrow focus.\n\
  \n---\n\n## When to Use\n\n- Before opening a PR you intend to merge today\n- After\
  \ implementing a plan — to verify the plan was faithfully executed\n- When you feel\
  \ \"done\" but want an adversarial check before shipping\n- As the final gate before\
  \ declaring a feature complete\n\n---\n\n## Step 0 — PR Validation (if a PR exists)\n\
  \nBefore reviewing code quality, check whether a pull request is open for the current\
  \ branch and resolve any outstanding issues:\n\n```bash\n# Detect open PR for current\
  \ branch\ngh pr list --head $(git branch --show-current) --json number,title,state\n\
  ```\n\nIf a PR exists:\n\n1. **Check CI status** — `gh pr checks <PR_NUMBER>` —\
  \ identify any failing checks\n   - For each FAILURE: download logs (`gh run view\
  \ <RUN_ID> --log-failed`), diagnose, fix, push\n   - Common fixes: run `./gradlew\
  \ spotlessApply` for formatting failures; investigate test logs for test failures\n\
  2. **Review ALL inline review comments** — fetch via API to capture bot comments\
  \ (not returned by `gh pr view --comments`):\n   ```bash\n   gh api repos/{owner}/{repo}/pulls/{PR_NUMBER}/comments\
  \ --paginate \\\n     | jq '.[] | {id, user: .user.login, path, body: .body[:200]}'\n\
  \   ```\n   This includes **human reviewers AND bot reviewers** such as `copilot-pull-request-reviewer[bot]`.\n\
  \   - **Triage each comment**: decide Fix or Decline\n     - **Fix**: real bugs\
  \ (null safety, incorrect logic, data integrity, security issues) → implement the\
  \ fix\n     - **Decline**: style preferences, premature optimizations, out-of-scope\
  \ enhancements → reply with rationale\n   - For each comment you **decline**, reply\
  \ via:\n     ```bash\n     gh api repos/{owner}/{repo}/pulls/{PR_NUMBER}/comments\
  \ \\\n       -X POST -f body=\"<rationale>\" -f in_reply_to=<COMMENT_ID>\n     ```\n\
  \   - Do NOT close review threads manually — push code fixes; GitHub auto-resolves\
  \ on push\n3. **Review PR-level review decisions** — `gh pr view <PR_NUMBER> --json\
  \ reviews`\n   - `REVIEW_REQUIRED`: no blocking action needed, but note it in the\
  \ report\n   - `CHANGES_REQUESTED`: treat each requested change as a blocking issue\n\
  \   - `APPROVED`: note as green\n\nRecord: PR number, failing checks (names + root\
  \ cause), unresolved comments (count + summary), review decision.\n\nIf no PR exists,\
  \ skip this step.\n\n---\n\n## Step 1 — Establish Context\n\nBefore launching agents,\
  \ gather the change set and any existing plan:\n\n1. Run `git diff HEAD --stat`\
  \ and `git diff HEAD --name-only` to enumerate changed files\n2. Check for an existing\
  \ plan at `project_plans/`, `docs/tasks/`, or `CLAUDE.md` — read it if found\n3.\
  \ Check for a `validation.md` (test coverage map) — read it if found\n4. Run the\
  \ project's test suite (`pytest`, `./gradlew test`, `npm test`, etc.) and record\
  \ pass/fail counts\n5. Note the primary language and framework from the repo structure\n\
  \n---\n\n## Step 2 — Launch 7 Parallel Reviewers\n\nLaunch all agents simultaneously\
  \ using a single message with multiple Task tool calls.\nEach agent receives: (a)\
  \ the list of changed files, (b) the diff content for its focus area, (c) relevant\
  \ plan/spec if available.\n\n---\n\n### Agent 1 — Plan Compliance\n**subagent_type**:\
  \ `general-purpose`\n\nVerify the implementation matches what was planned. Focus\
  \ on:\n- **Completeness**: Every requirement/task in the plan has a corresponding\
  \ implementation\n- **Scope discipline**: No unrequested features or refactoring\
  \ beyond what was asked\n- **Acceptance criteria**: Each stated criterion can be\
  \ traced to code or tests\n- **Known gaps**: Anything in the plan that is unimplemented\
  \ or partially implemented\n- **Scope creep**: Changes that weren't in the plan\
  \ (flag but don't automatically block)\n\nRate: \U0001F7E2 All requirements met\
  \ / \U0001F7E1 Minor gaps or extras / \U0001F534 Significant requirements missing\n\
  \n---\n\n### Agent 2 — Architecture & Design\n**subagent_type**: `software-planner`\n\
  \nApply the `quality:architecture-review` skill context to the changed files:\n\
  - **SOLID principles**: Any new violations? (SRP, OCP, LSP, ISP, DIP)\n- **Layer\
  \ boundaries**: Do changes respect the existing layering (controller → service →\
  \ repository)?\n- **Coupling**: New tight couplings introduced? Circular dependencies?\n\
  - **Design patterns**: Are patterns used appropriately, or are there anti-patterns?\n\
  - **Consistency**: Do the changes follow the conventions already established in\
  \ the codebase?\n- **Technical debt**: Is any new debt introduced? Is it documented?\n\
  \nRate: \U0001F7E2 Sound design / \U0001F7E1 Minor issues / \U0001F534 Architectural\
  \ problems that will cause pain\n\n---\n\n### Agent 3 — Code Quality\n**subagent_type**:\
  \ `code-refactoring`\n\nApply Clean Code and The Pragmatic Programmer standards\
  \ to changed files:\n- **Naming**: Variables, functions, classes — self-describing\
  \ without comments?\n- **Function size and complexity**: Cyclomatic complexity,\
  \ long methods, deep nesting\n- **DRY**: Duplication introduced that should be extracted?\n\
  - **Error handling**: Are errors handled explicitly, or swallowed/ignored?\n- **Magic\
  \ values**: Unexplained literals, hardcoded paths, magic numbers\n- **Comments**:\
  \ Explain *why* not *what* — any misleading or stale comments?\n- **Readability**:\
  \ Would a new team member understand this in 5 minutes?\n\nRate: \U0001F7E2 Clean\
  \ / \U0001F7E1 Some issues / \U0001F534 Hard to maintain or understand\n\n---\n\n\
  ### Agent 4 — Test Quality\n**subagent_type**: `general-purpose`\n\nEvaluate whether\
  \ the tests actually validate the feature (not just coverage theater):\n- **Behavior\
  \ coverage**: Do tests verify *what* the code does, not *how* it does it?\n- **Missing\
  \ cases**: Unhappy paths, edge cases, boundary values not covered\n- **Test smells**:\
  \ Over-mocking, brittle assertions, test-by-side-effects, slow tests\n- **Confidence**:\
  \ Would these tests catch a real regression in production?\n- **Test isolation**:\
  \ Are tests independent — can they run in any order?\n- **Plan traceability**: Does\
  \ each acceptance criterion have at least one test?\n\nRate: \U0001F7E2 High confidence\
  \ / \U0001F7E1 Coverage gaps / \U0001F534 Tests won't catch real bugs\n\n---\n\n\
  ### Agent 5 — Security\n**subagent_type**: `general-purpose`\n\nApply OWASP Top\
  \ 10 and defense-in-depth to the changed code:\n- **Injection**: SQL, command, template,\
  \ LDAP injection in new code paths\n- **Authentication/Authorization**: New endpoints\
  \ or data paths missing auth checks\n- **Sensitive data**: Secrets, tokens, PII\
  \ logged or exposed in responses\n- **Input validation**: User-controlled data validated/sanitized\
  \ at system boundaries\n- **Dependencies**: Any new packages introduced with known\
  \ CVEs? (`pip audit`, `npm audit`, etc.)\n- **Cryptography**: Weak hashing, outdated\
  \ algorithms, hardcoded keys\n- **Supply chain**: Any new downloads or external\
  \ fetches? Hash-verified?\n\nRate: \U0001F7E2 No new risks / \U0001F7E1 Low-severity\
  \ concerns / \U0001F534 Exploitable vulnerability introduced\n\n---\n\n### Agent\
  \ 6 — Product & UX\n**subagent_type**: `ux-expert`\n\nApply Nielsen's heuristics\
  \ and the product-management lens to the user-facing surface:\n- **User flows**:\
  \ Are all paths through the feature coherent and complete?\n- **State coverage**:\
  \ Empty state, loading, error, partial failure, success — all handled?\n- **Error\
  \ messages**: Actionable and user-friendly, or raw stack traces / cryptic codes?\n\
  - **Consistency**: Does this match the existing UX conventions in the product?\n\
  - **Accessibility**: Keyboard navigation, screen reader labels, color contrast (if\
  \ UI)\n- **Edge cases as user experience**: What happens when the user does something\
  \ unexpected?\n- **Meets the brief**: Does this solve the original user problem\
  \ that motivated the feature?\n\nRate: \U0001F7E2 Ready / \U0001F7E1 Rough edges\
  \ / \U0001F534 Confusing or broken for users\n\n---\n\n### Agent 7 — Operational\
  \ Readiness, Monitoring & SLOs\n**subagent_type**: `general-purpose`\n\nEvaluate\
  \ production survivability and whether the feature ships with adequate observability,\
  \ alerting, and defined service level objectives.\n\n#### Observability\n- **Logging**:\
  \ New code paths log at appropriate levels (`INFO` for business events, `WARN`/`ERROR`\
  \ for failures); no silent catch blocks\n- **Metrics instrumentation**: New endpoints\
  \ or async consumers emit RED metrics — **R**ate (request count), **E**rrors (error\
  \ count/rate), **D**uration (latency percentiles)\n- **Tracing**: Distributed trace\
  \ spans created for new cross-service calls; trace IDs propagated\n- **Error propagation**:\
  \ Exceptions caught and surfaced as meaningful errors, not swallowed\n\n#### Monitoring\
  \ & Alerting\n- **New monitors**: Are Datadog (or equivalent) monitors defined for\
  \ new failure modes?\n- **Alert thresholds**: Are thresholds grounded in baseline\
  \ behavior, not arbitrary round numbers?\n- **Alert routing**: Do new alerts have\
  \ an owner and route to the right team/channel?\n- **Runbook links**: Every alert\
  \ links to a runbook or has inline investigation steps\n- **Dashboard coverage**:\
  \ New services or endpoints are visible on an existing or new dashboard\n- **Anomaly\
  \ coverage**: Are burn-rate or anomaly-detection monitors preferred over static\
  \ thresholds for latency/error-rate?\n\n#### SLIs & SLOs\n- **SLI defined**: Is\
  \ there a Service Level Indicator for each user-facing behavior introduced? (e.g.,\
  \ `p99 latency < 300ms`, `error rate < 0.1%`, `availability > 99.9%`)\n- **SLO set**:\
  \ Is there a target SLO in place, or does an existing SLO cover this feature?\n\
  - **Error budget**: Does the change risk burning the existing error budget? (e.g.,\
  \ degraded dependency, new synchronous call in the happy path)\n- **SLO alerting**:\
  \ Is there a multi-window, multi-burn-rate alert (Google SRE approach) — fast burn\
  \ (1h window, 14× budget consumption) and slow burn (6h window, 6× consumption)?\n\
  - **Availability vs. latency SLOs**: Both should be defined for user-facing features\
  \ — availability alone is insufficient\n\n#### Resilience & Operations\n- **Backward\
  \ compatibility**: DB migrations are reversible; API changes are additive (no breaking\
  \ changes without versioning)\n- **Performance**: No obvious N+1 queries, unbounded\
  \ loops, or memory leaks introduced\n- **Graceful degradation**: Partial failure\
  \ isolated — doesn't cascade to unrelated features\n- **Configuration**: New env\
  \ vars/feature flags documented with sane defaults and valid ranges\n- **Capacity**:\
  \ Is there a reason to expect traffic patterns outside current provisioning?\n\n\
  Rate: \U0001F7E2 Production-ready with SLOs defined / \U0001F7E1 Minor gaps (SLOs\
  \ informal or monitors missing) / \U0001F534 Ships blind — no SLOs, no alerts, or\
  \ resilience risk\n\n---\n\n## Step 3 — Synthesize into Shipping Decision\n\nAfter\
  \ all agents return, produce this report:\n\n```markdown\n## Is It Ready? — Shipping\
  \ Gate Report\n\n**Branch / Scope**: <branch name or scope>\n**PR**: <#number or\
  \ \"no PR\">\n**CI Checks**: <X passing / Y failing — list failing check names>\n\
  **PR Comments**: <N unresolved human comments / \"none\" / \"no PR\">\n**Review\
  \ Decision**: <APPROVED / REVIEW_REQUIRED / CHANGES_REQUESTED / \"no PR\">\n**Plan**:\
  \ <linked or \"no plan found\">\n**Tests**: <X passing / Y failing>\n**Date**: <today>\n\
  \n| Dimension                          | Status | Blocking Issues | Notes |\n|------------------------------------|--------|-----------------|-------|\n\
  | CI / PR Checks                     | \U0001F7E2/\U0001F7E1/\U0001F534 | ...  \
  \         | ...   |\n| PR Review Comments                 | \U0001F7E2/\U0001F7E1\
  /\U0001F534 | ...           | ...   |\n| Plan Compliance                    | \U0001F7E2\
  /\U0001F7E1/\U0001F534 | ...           | ...   |\n| Architecture               \
  \        | \U0001F7E2/\U0001F7E1/\U0001F534 | ...           | ...   |\n| Code Quality\
  \                       | \U0001F7E2/\U0001F7E1/\U0001F534 | ...           | ...\
  \   |\n| Test Quality                       | \U0001F7E2/\U0001F7E1/\U0001F534 |\
  \ ...           | ...   |\n| Security                           | \U0001F7E2/\U0001F7E1\
  /\U0001F534 | ...           | ...   |\n| Product / UX                       | \U0001F7E2\
  /\U0001F7E1/\U0001F534 | ...           | ...   |\n| Ops: Observability & Resilience\
  \    | \U0001F7E2/\U0001F7E1/\U0001F534 | ...           | ...   |\n| Ops: Monitoring\
  \ & Alerts           | \U0001F7E2/\U0001F7E1/\U0001F534 | ...           | ...  \
  \ |\n| Ops: SLIs / SLOs                   | \U0001F7E2/\U0001F7E1/\U0001F534 | ...\
  \           | ...   |\n\n---\n\n## Verdict: [\U0001F680 SHIP IT / ⚠️ FIX THEN SHIP\
  \ / \U0001F6D1 HOLD]\n\n### Blocking Issues (must resolve before merging)\n1. [Dimension]\
  \ — specific issue with file:line reference\n2. ...\n\n### Non-Blocking Improvements\
  \ (follow-up OK)\n1. [Dimension] — improvement suggestion\n2. ...\n\n### Recommended\
  \ Next Action\n[Single clearest step to unblock shipping, or confirmation that it's\
  \ ready]\n```\n\n---\n\n## Verdict Criteria\n\n| Verdict | Condition |\n|---------|-----------|\n\
  | \U0001F680 **SHIP IT** | All dimensions \U0001F7E2, or only \U0001F7E1 with no\
  \ blocking issues |\n| ⚠️ **FIX THEN SHIP** | One or more \U0001F7E1 with fixable\
  \ blocking issues (< 2h work) |\n| \U0001F6D1 **HOLD** | Any \U0001F534, or multiple\
  \ blocking issues across dimensions |\n\nA single \U0001F534 in **Security** or\
  \ **Ops: SLIs / SLOs** (new user-facing feature with no SLO) always produces a **HOLD**\
  \ regardless of other scores.\n\n**Automatic \U0001F534 in CI / PR Checks** when:\n\
  - Any required CI check is failing (must fix and push before considering merge)\n\
  - Any reviewer has requested changes (treat each as a blocking issue)\n\n**Automatic\
  \ \U0001F7E1 in PR Review Comments** when:\n- Unresolved human or bot (e.g., Copilot)\
  \ review comments exist but no CHANGES_REQUESTED decision (address or explicitly\
  \ decline with rationale)\n- Bot comments that identify real bugs (null safety,\
  \ logic errors) must be treated identically to human comments\n\n**SLO minimum bar\
  \ for new user-facing features:**\n1. At least one latency SLI (e.g., `p99 < 500ms`)\
  \ with a target and error budget\n2. An error-rate SLI (e.g., `5xx rate < 0.5%`)\n\
  3. A multi-burn-rate alert wired to the error budget\n4. A Datadog dashboard panel\
  \ showing the SLO compliance window\n\nIf the feature only affects internal/async\
  \ paths (batch jobs, consumers), SLOs are \U0001F7E1 recommended but not blocking.\n\
  \n---\n\n## Related Commands\n\n- `/pm:triad-review` — pre-build readiness check\
  \ (run before implementing)\n- `/quality:architecture-review` — deep-dive architecture\
  \ analysis\n- `/code:review` — code review for PR feedback workflow\n- `/quality:does-it-work`\
  \ — quick build/test/lint check\n- `/quality:test-planner` — generate a test plan\
  \ before writing tests\n"
---

# Is It Ready? — Shipping Readiness Review

Run a parallel swarm of specialized reviewers against the current changes to produce a single, evidence-backed shipping decision.

**Scope**: `${1:-current git changes}` — defaults to `git diff HEAD` (staged + unstaged). Pass a path, branch ref, or commit range to narrow focus.

---

## When to Use

- Before opening a PR you intend to merge today
- After implementing a plan — to verify the plan was faithfully executed
- When you feel "done" but want an adversarial check before shipping
- As the final gate before declaring a feature complete

---

## Step 0 — PR Validation (if a PR exists)

Before reviewing code quality, check whether a pull request is open for the current branch and resolve any outstanding issues:

```bash
# Detect open PR for current branch
gh pr list --head $(git branch --show-current) --json number,title,state
```

If a PR exists:

1. **Check CI status** — `gh pr checks <PR_NUMBER>` — identify any failing checks
   - For each FAILURE: download logs (`gh run view <RUN_ID> --log-failed`), diagnose, fix, push
   - Common fixes: run `./gradlew spotlessApply` for formatting failures; investigate test logs for test failures
2. **Review ALL inline review comments** — fetch via API to capture bot comments (not returned by `gh pr view --comments`):
   ```bash
   gh api repos/{owner}/{repo}/pulls/{PR_NUMBER}/comments --paginate \
     | jq '.[] | {id, user: .user.login, path, body: .body[:200]}'
   ```
   This includes **human reviewers AND bot reviewers** such as `copilot-pull-request-reviewer[bot]`.
   - **Triage each comment**: decide Fix or Decline
     - **Fix**: real bugs (null safety, incorrect logic, data integrity, security issues) → implement the fix
     - **Decline**: style preferences, premature optimizations, out-of-scope enhancements → reply with rationale
   - For each comment you **decline**, reply via:
     ```bash
     gh api repos/{owner}/{repo}/pulls/{PR_NUMBER}/comments \
       -X POST -f body="<rationale>" -f in_reply_to=<COMMENT_ID>
     ```
   - Do NOT close review threads manually — push code fixes; GitHub auto-resolves on push
3. **Review PR-level review decisions** — `gh pr view <PR_NUMBER> --json reviews`
   - `REVIEW_REQUIRED`: no blocking action needed, but note it in the report
   - `CHANGES_REQUESTED`: treat each requested change as a blocking issue
   - `APPROVED`: note as green

Record: PR number, failing checks (names + root cause), unresolved comments (count + summary), review decision.

If no PR exists, skip this step.

---

## Step 1 — Establish Context

Before launching agents, gather the change set and any existing plan:

1. Run `git diff HEAD --stat` and `git diff HEAD --name-only` to enumerate changed files
2. Check for an existing plan at `project_plans/`, `docs/tasks/`, or `CLAUDE.md` — read it if found
3. Check for a `validation.md` (test coverage map) — read it if found
4. Run the project's test suite (`pytest`, `./gradlew test`, `npm test`, etc.) and record pass/fail counts
5. Note the primary language and framework from the repo structure

---

## Step 2 — Launch 7 Parallel Reviewers

Launch all agents simultaneously using a single message with multiple Task tool calls.
Each agent receives: (a) the list of changed files, (b) the diff content for its focus area, (c) relevant plan/spec if available.

---

### Agent 1 — Plan Compliance
**subagent_type**: `general-purpose`

Verify the implementation matches what was planned. Focus on:
- **Completeness**: Every requirement/task in the plan has a corresponding implementation
- **Scope discipline**: No unrequested features or refactoring beyond what was asked
- **Acceptance criteria**: Each stated criterion can be traced to code or tests
- **Known gaps**: Anything in the plan that is unimplemented or partially implemented
- **Scope creep**: Changes that weren't in the plan (flag but don't automatically block)

Rate: 🟢 All requirements met / 🟡 Minor gaps or extras / 🔴 Significant requirements missing

---

### Agent 2 — Architecture & Design
**subagent_type**: `software-planner`

Apply the `quality:architecture-review` skill context to the changed files:
- **SOLID principles**: Any new violations? (SRP, OCP, LSP, ISP, DIP)
- **Layer boundaries**: Do changes respect the existing layering (controller → service → repository)?
- **Coupling**: New tight couplings introduced? Circular dependencies?
- **Design patterns**: Are patterns used appropriately, or are there anti-patterns?
- **Consistency**: Do the changes follow the conventions already established in the codebase?
- **Technical debt**: Is any new debt introduced? Is it documented?

Rate: 🟢 Sound design / 🟡 Minor issues / 🔴 Architectural problems that will cause pain

---

### Agent 3 — Code Quality
**subagent_type**: `code-refactoring`

Apply Clean Code and The Pragmatic Programmer standards to changed files:
- **Naming**: Variables, functions, classes — self-describing without comments?
- **Function size and complexity**: Cyclomatic complexity, long methods, deep nesting
- **DRY**: Duplication introduced that should be extracted?
- **Error handling**: Are errors handled explicitly, or swallowed/ignored?
- **Magic values**: Unexplained literals, hardcoded paths, magic numbers
- **Comments**: Explain *why* not *what* — any misleading or stale comments?
- **Readability**: Would a new team member understand this in 5 minutes?

Rate: 🟢 Clean / 🟡 Some issues / 🔴 Hard to maintain or understand

---

### Agent 4 — Test Quality
**subagent_type**: `general-purpose`

Evaluate whether the tests actually validate the feature (not just coverage theater):
- **Behavior coverage**: Do tests verify *what* the code does, not *how* it does it?
- **Missing cases**: Unhappy paths, edge cases, boundary values not covered
- **Test smells**: Over-mocking, brittle assertions, test-by-side-effects, slow tests
- **Confidence**: Would these tests catch a real regression in production?
- **Test isolation**: Are tests independent — can they run in any order?
- **Plan traceability**: Does each acceptance criterion have at least one test?

Rate: 🟢 High confidence / 🟡 Coverage gaps / 🔴 Tests won't catch real bugs

---

### Agent 5 — Security
**subagent_type**: `general-purpose`

Apply OWASP Top 10 and defense-in-depth to the changed code:
- **Injection**: SQL, command, template, LDAP injection in new code paths
- **Authentication/Authorization**: New endpoints or data paths missing auth checks
- **Sensitive data**: Secrets, tokens, PII logged or exposed in responses
- **Input validation**: User-controlled data validated/sanitized at system boundaries
- **Dependencies**: Any new packages introduced with known CVEs? (`pip audit`, `npm audit`, etc.)
- **Cryptography**: Weak hashing, outdated algorithms, hardcoded keys
- **Supply chain**: Any new downloads or external fetches? Hash-verified?

Rate: 🟢 No new risks / 🟡 Low-severity concerns / 🔴 Exploitable vulnerability introduced

---

### Agent 6 — Product & UX
**subagent_type**: `ux-expert`

Apply Nielsen's heuristics and the product-management lens to the user-facing surface:
- **User flows**: Are all paths through the feature coherent and complete?
- **State coverage**: Empty state, loading, error, partial failure, success — all handled?
- **Error messages**: Actionable and user-friendly, or raw stack traces / cryptic codes?
- **Consistency**: Does this match the existing UX conventions in the product?
- **Accessibility**: Keyboard navigation, screen reader labels, color contrast (if UI)
- **Edge cases as user experience**: What happens when the user does something unexpected?
- **Meets the brief**: Does this solve the original user problem that motivated the feature?

Rate: 🟢 Ready / 🟡 Rough edges / 🔴 Confusing or broken for users

---

### Agent 7 — Operational Readiness, Monitoring & SLOs
**subagent_type**: `general-purpose`

Evaluate production survivability and whether the feature ships with adequate observability, alerting, and defined service level objectives.

#### Observability
- **Logging**: New code paths log at appropriate levels (`INFO` for business events, `WARN`/`ERROR` for failures); no silent catch blocks
- **Metrics instrumentation**: New endpoints or async consumers emit RED metrics — **R**ate (request count), **E**rrors (error count/rate), **D**uration (latency percentiles)
- **Tracing**: Distributed trace spans created for new cross-service calls; trace IDs propagated
- **Error propagation**: Exceptions caught and surfaced as meaningful errors, not swallowed

#### Monitoring & Alerting
- **New monitors**: Are Datadog (or equivalent) monitors defined for new failure modes?
- **Alert thresholds**: Are thresholds grounded in baseline behavior, not arbitrary round numbers?
- **Alert routing**: Do new alerts have an owner and route to the right team/channel?
- **Runbook links**: Every alert links to a runbook or has inline investigation steps
- **Dashboard coverage**: New services or endpoints are visible on an existing or new dashboard
- **Anomaly coverage**: Are burn-rate or anomaly-detection monitors preferred over static thresholds for latency/error-rate?

#### SLIs & SLOs
- **SLI defined**: Is there a Service Level Indicator for each user-facing behavior introduced? (e.g., `p99 latency < 300ms`, `error rate < 0.1%`, `availability > 99.9%`)
- **SLO set**: Is there a target SLO in place, or does an existing SLO cover this feature?
- **Error budget**: Does the change risk burning the existing error budget? (e.g., degraded dependency, new synchronous call in the happy path)
- **SLO alerting**: Is there a multi-window, multi-burn-rate alert (Google SRE approach) — fast burn (1h window, 14× budget consumption) and slow burn (6h window, 6× consumption)?
- **Availability vs. latency SLOs**: Both should be defined for user-facing features — availability alone is insufficient

#### Resilience & Operations
- **Backward compatibility**: DB migrations are reversible; API changes are additive (no breaking changes without versioning)
- **Performance**: No obvious N+1 queries, unbounded loops, or memory leaks introduced
- **Graceful degradation**: Partial failure isolated — doesn't cascade to unrelated features
- **Configuration**: New env vars/feature flags documented with sane defaults and valid ranges
- **Capacity**: Is there a reason to expect traffic patterns outside current provisioning?

Rate: 🟢 Production-ready with SLOs defined / 🟡 Minor gaps (SLOs informal or monitors missing) / 🔴 Ships blind — no SLOs, no alerts, or resilience risk

---

## Step 3 — Synthesize into Shipping Decision

After all agents return, produce this report:

```markdown
## Is It Ready? — Shipping Gate Report

**Branch / Scope**: <branch name or scope>
**PR**: <#number or "no PR">
**CI Checks**: <X passing / Y failing — list failing check names>
**PR Comments**: <N unresolved human comments / "none" / "no PR">
**Review Decision**: <APPROVED / REVIEW_REQUIRED / CHANGES_REQUESTED / "no PR">
**Plan**: <linked or "no plan found">
**Tests**: <X passing / Y failing>
**Date**: <today>

| Dimension                          | Status | Blocking Issues | Notes |
|------------------------------------|--------|-----------------|-------|
| CI / PR Checks                     | 🟢/🟡/🔴 | ...           | ...   |
| PR Review Comments                 | 🟢/🟡/🔴 | ...           | ...   |
| Plan Compliance                    | 🟢/🟡/🔴 | ...           | ...   |
| Architecture                       | 🟢/🟡/🔴 | ...           | ...   |
| Code Quality                       | 🟢/🟡/🔴 | ...           | ...   |
| Test Quality                       | 🟢/🟡/🔴 | ...           | ...   |
| Security                           | 🟢/🟡/🔴 | ...           | ...   |
| Product / UX                       | 🟢/🟡/🔴 | ...           | ...   |
| Ops: Observability & Resilience    | 🟢/🟡/🔴 | ...           | ...   |
| Ops: Monitoring & Alerts           | 🟢/🟡/🔴 | ...           | ...   |
| Ops: SLIs / SLOs                   | 🟢/🟡/🔴 | ...           | ...   |

---

## Verdict: [🚀 SHIP IT / ⚠️ FIX THEN SHIP / 🛑 HOLD]

### Blocking Issues (must resolve before merging)
1. [Dimension] — specific issue with file:line reference
2. ...

### Non-Blocking Improvements (follow-up OK)
1. [Dimension] — improvement suggestion
2. ...

### Recommended Next Action
[Single clearest step to unblock shipping, or confirmation that it's ready]
```

---

## Verdict Criteria

| Verdict | Condition |
|---------|-----------|
| 🚀 **SHIP IT** | All dimensions 🟢, or only 🟡 with no blocking issues |
| ⚠️ **FIX THEN SHIP** | One or more 🟡 with fixable blocking issues (< 2h work) |
| 🛑 **HOLD** | Any 🔴, or multiple blocking issues across dimensions |

A single 🔴 in **Security** or **Ops: SLIs / SLOs** (new user-facing feature with no SLO) always produces a **HOLD** regardless of other scores.

**Automatic 🔴 in CI / PR Checks** when:
- Any required CI check is failing (must fix and push before considering merge)
- Any reviewer has requested changes (treat each as a blocking issue)

**Automatic 🟡 in PR Review Comments** when:
- Unresolved human or bot (e.g., Copilot) review comments exist but no CHANGES_REQUESTED decision (address or explicitly decline with rationale)
- Bot comments that identify real bugs (null safety, logic errors) must be treated identically to human comments

**SLO minimum bar for new user-facing features:**
1. At least one latency SLI (e.g., `p99 < 500ms`) with a target and error budget
2. An error-rate SLI (e.g., `5xx rate < 0.5%`)
3. A multi-burn-rate alert wired to the error budget
4. A Datadog dashboard panel showing the SLO compliance window

If the feature only affects internal/async paths (batch jobs, consumers), SLOs are 🟡 recommended but not blocking.

---

## Related Commands

- `/pm:triad-review` — pre-build readiness check (run before implementing)
- `/quality:architecture-review` — deep-dive architecture analysis
- `/code:review` — code review for PR feedback workflow
- `/quality:does-it-work` — quick build/test/lint check
- `/quality:test-planner` — generate a test plan before writing tests
