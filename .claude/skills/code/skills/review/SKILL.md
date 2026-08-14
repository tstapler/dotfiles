---
description: Comprehensive code review — 5 parallel specialized agents (testing, code quality, architecture, database, security) → adversarial skeptic pass to filter false positives → severity-labeled findings [BLOCKER]/[CRITICAL]/[MAJOR]/[NIT] capped for actionability.
---

# Comprehensive Code Review

Perform a multi-dimensional code review using five specialized agents in parallel, filter through an adversarial skeptic pass, then consolidate results with severity labels and code snippets.

## Review Dimensions

1. **Testing Quality** — anti-patterns, ADR compliance, test confidence
2. **Code Quality** — SOLID, Clean Code, design patterns, performance, concurrency
3. **Architecture** — layering, DDD, technical debt, API compatibility, system-level performance
4. **Database** — query performance, schema design, transaction safety
5. **Security** — OWASP Top 10 per-category checklist

## Usage

Review a specific directory:
```
/code:review src/main/java/com/example/service
```

Review the entire project:
```
/code:review .
```

Review a specific component:
```
/code:review src/main/java/com/example/UserService.java
```

## Implementation Steps

### Step 0: Generate Diff Summary + Relevance Detection

Before launching agents, generate a structured 3-sentence summary of what this diff does and determine which review dimensions are relevant:

```bash
git log --oneline -5
git diff HEAD~1 --stat
git diff HEAD~1 -- ${1:-.} | head -200
```

Synthesize: *"This change modifies N files. It [main change in one clause]. Key affected areas: [list of modules/services]."*

Store as `DIFF_SUMMARY`. Inject at the top of every agent prompt in Step 1.

**Relevance detection** — scan the diff output and set these flags:

- `HAS_DB_CODE`: true if the diff contains any of: `.sql` files, migration files, ORM annotations (`@Entity`, `@Repository`, `@Table`, `@Column`, `@Query`, `@OneToMany`, etc.), SQL strings (`SELECT`, `INSERT`, `UPDATE`, `DELETE`, `CREATE TABLE`), Prisma schema changes, TypeORM decorators, Hibernate/JPA code, Ent schema files (`ent/schema/`).
- `HAS_TESTS`: true if the diff contains test files (files matching `*_test.go`, `*.test.ts`, `*.spec.ts`, `*.spec.java`, `Test*.java`, files in `__tests__/` or `tests/`).
- `HAS_SECURITY_SENSITIVE`: true if the diff touches auth/crypto/input-handling code (files/functions with names containing: auth, login, password, token, session, encrypt, decrypt, hash, secret, credential, permission, role, sanitize, validate, csrf; or imports of crypto/jwt/bcrypt libraries).

These flags determine which agents launch in Step 1.

**Lens check (dimension coverage) — do this before Step 1.** The five dimensions above are a *starter set, not a ceiling.* A review is only as good as its lens composition, so explicitly ask what dimensions THIS change demands that the standard agents may not cover, and launch a targeted reviewer (or widen an agent's scope) for any that are missing. From the diff, check for these commonly-missed lenses:

- **Multi-tenant / authz-scoping** — any list/query/filter/search API: does an *empty or absent* filter leak across tenants/users? Is per-tenant scoping enforced server-side, or must the caller apply it? This is the single most common blind spot on list APIs — add a dedicated reviewer when the change touches one.
- **Error-contract vs. callers** — if a return/error contract changed (now errors where it returned a value, or vice versa), does it break how existing callers branch on it? Grep the call sites.
- **Behavioral equivalence vs. the thing being replaced** — if this reimplements or swaps out an existing component, compare method-by-method against the original's *semantics*, not just abstract correctness.
- **Resource / credential lifecycle** — cached clients/tokens/connections that outlive their validity; goroutine/FD leaks; unbounded retries.
- **Backward / forward compatibility** — wire formats, serialized/persisted data, public APIs.
- **Operational / rollback** — is the change safely revertible; does it fail closed?

If a demanded lens isn't among the five, launch an extra targeted reviewer for it in Step 1 (same prompt shape as the Security agent: "Review ONLY &lt;lens&gt; in this diff"). Record any dimension you deliberately skip, and why.

---

### Step 0.5: Fetch Live PR Review Threads (if a PR exists)

This diff review is blind to feedback that's already been posted on GitHub — a bot or human reviewer's outstanding comment shouldn't be re-flagged as new, and a real gap here is what let a `pr-ship` gate loop trust a stale "all resolved" snapshot after a bitbot comment landed later uncaught. Use the same shared script `github-address-pr-comments` and `github:pr-ship` use, so all three stay on one aggregation implementation:

```bash
PR=$(gh pr list --head "$(git branch --show-current)" --json number --jq '.[0].number')
```

If no open PR exists for the current branch, skip this step and note "No open PR — live thread check skipped" in the report.

Otherwise:
```bash
REPO_NWO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
OWNER="${REPO_NWO%%/*}"; REPO_NAME="${REPO_NWO##*/}"
python3 ~/.claude/scripts/pr-threads.py summary --owner "$OWNER" --repo "$REPO_NAME" --pr "$PR" [--hostname <enterprise-host-if-applicable>]
```

Store the `unresolved` array as `LIVE_THREADS`. Inject a summary of it into every Step 1 agent's prompt alongside `DIFF_SUMMARY` — e.g. "Known outstanding review threads: [file:line — one-line summary]. Do not re-report these as new findings; note in your output if your finding overlaps one." This keeps the diff-based agents from duplicating what's already tracked live on GitHub, and surfaces threads that predate this review run.

Also fetch check-run findings — bots like bitbot post mutation-testing gaps and risk assessments as a check run with `conclusion: neutral`, which never shows up in `reviewThreads` and doesn't fail the PR, so a "review comments" pass alone misses it (a real gap this skill had until it was caught reviewing PR #501):

```bash
python3 ~/.claude/scripts/pr-threads.py checkruns --owner "$OWNER" --repo "$REPO_NAME" --pr "$PR" [--hostname <enterprise-host-if-applicable>]
```

Store the `non_success` array as `LIVE_CHECKS`. Fold it into the same agent-prompt injection as `LIVE_THREADS`: a mutation-testing "potential gaps found" entry names the untested branch/behavior directly, so treat it as a pointer for the Testing Quality Agent rather than something to re-derive from scratch — and don't rely on `gh pr checks`' status column for this, it has been observed disagreeing with the check-run API's own `conclusion` field.

---

### Step 1: Parallel Agent Invocation

Launch only the relevant agents simultaneously based on the flags from Step 0. Each receives `DIFF_SUMMARY` from Step 0.

- **Testing Quality Agent**: Always launch.
- **Code Quality Agent**: Always launch.
- **Architecture Agent**: Always launch.
- **Database Agent**: Launch only if `HAS_DB_CODE` is true. If false, record "Database: No SQL or ORM code in diff — skipped." and proceed.
- **Security Agent**: Always launch (security issues can appear anywhere; OWASP checklist self-gates per category).

**Testing Quality Agent**: dispatch by language rather than a fixed framework persona — detect the diff's primary language(s) from file extensions before building the prompt (`*.go` → Go, `*.java`/`*.kt` → JVM, etc.), and tell the agent which skill(s) to load for that language so review language matches the codebase instead of defaulting to JVM/Spring vocabulary.

```
Agent(
  subagent_type: "testing-quality-master",
  description: "Review test quality in ${1:-.}",
  prompt: """
  CONTEXT: {DIFF_SUMMARY}

  Before reviewing: identify the primary language/framework of the code under review, then invoke the Skill tool for the matching testing skill to load its language-specific idioms and checklists before evaluating — e.g. `golang-testing` for Go, `spring-boot-testing` for Java/Spring, or the closest equivalent for anything else. If no matching skill exists, proceed with your general language-agnostic principles alone and say so.

  Review tests in ${1:-.} using a checklist approach — evaluate every item even after finding issues in prior categories.

  Checklist:
  1. Anti-patterns (apply the language-specific list from the loaded skill; if none, use these language-agnostic defaults):
     - Implementation coupling (asserting on internals/private state instead of observable behavior)
     - Over-mocking internal collaborators
     - Environment mismatches (fake/in-memory substitute diverging from production behavior, e.g. H2 instead of PostgreSQL)
     - Coverage theater (high line count, low behavior confidence)
     - Fragile tests that break on refactoring
     - Copy-paste test clusters that should be table-driven / parameterized (the loaded skill should say what idiomatic parameterization looks like in this language)

  2. Project/framework conventions from the loaded skill (e.g. ADR-0016/ADR-0017 + TestContainers for Spring; table-driven tests + `t.Run` subtests + `goleak` for Go) — flag deviations from the codebase's own established conventions, not just the skill's defaults.

  3. Test confidence:
     - Do tests verify behavior or implementation details?
     - Would these catch real production bugs?
     - New logic paths with zero test coverage?

  For each finding provide:
  - file:line
  - Issue description
  - Severity: BLOCKER / CRITICAL / MAJOR / NIT
  - Category confidence (0-100)
  - Suggested fix (code snippet required for BLOCKER/CRITICAL)
  """
)
```

**Code Quality Agent**:
```
Agent(
  subagent_type: "code-refactoring",
  description: "Review code quality in ${1:-.}",
  prompt: """
  CONTEXT: {DIFF_SUMMARY}

  Before reviewing: identify the primary language/framework of the code under review, then invoke the Skill tool for the matching code-quality skill (e.g. `golang-code-style`, `golang-design-patterns`, `golang-safety` for Go; `spring-boot-java-development` for Java/Spring) to load its idioms before evaluating. If none matches, proceed on the checklist below alone.

  Review code in ${1:-.}. Use a checklist approach.

  Checklist:
  1. SOLID principles:
     - Single Responsibility violations (>1 reason to change)
     - Open/Closed violations (modification instead of extension)
     - Liskov Substitution violations
     - Interface Segregation opportunities
     - Dependency Inversion improvements

  2. Clean Code:
     - Method length/complexity (>20 lines or cyclomatic complexity >5)
     - Naming clarity and consistency
     - DRY violations
     - Magic numbers/strings
     - Comment quality (only WHY is needed; WHAT is noise). Flag ANY comment/doc-comment over 5 lines or spanning more than one paragraph as MAJOR, even if every line is WHY-content — a multi-paragraph comment is a sign the WHY should be split (root cause vs. accepted tradeoff vs. pointer to a test) or trimmed to the one fact a reviewer would actually ask for. Suggested fix must show the trimmed version, not just note the issue.

  3. Design patterns:
     - Inappropriate pattern usage
     - Missing pattern opportunities
     - Anti-patterns present

  4. Performance (flag obvious patterns only — do not speculate):
     - Algorithmic complexity: nested loops over unbounded collections (O(n²) or worse)
     - Unbounded growth: collections that accumulate without eviction or pagination
     - Resource leaks: connections, file handles, streams not closed
     - Repeated expensive computations inside loops that could be hoisted
     - Blocking I/O in async/reactive contexts (sync calls inside coroutines, blocking the event loop)
     - Unnecessary serialization/deserialization in hot paths
     If not clearly present: skip this category rather than speculating.

  5. Concurrency (check if diff touches shared state or async code):
     - Shared mutable state accessed from multiple threads without synchronization
     - Race conditions: check-then-act without atomics
     - Lock ordering that could deadlock
     - Immutability violations on shared objects

  For each finding provide:
  - file:line
  - Issue description
  - Severity: BLOCKER / CRITICAL / MAJOR / NIT
  - Category confidence (0-100)
  - Suggested fix (code snippet required for BLOCKER/CRITICAL)
  """
)
```

**Architecture Agent**:
```
Agent(
  subagent_type: "software-planner",
  description: "Review architecture in ${1:-.}",
  prompt: """
  CONTEXT: {DIFF_SUMMARY}

  Before reviewing: identify the primary language/framework of the code under review, then invoke the Skill tool for the matching architecture skill (e.g. `golang-project-layout`, `golang-design-patterns` for Go; `spring-boot-java-development` for Java/Spring) to load its conventions before evaluating. If none matches, proceed on the checklist below alone.

  Review architecture in ${1:-.}. Evaluate every checklist category.

  Checklist:
  1. Architectural patterns:
     - Layered architecture consistency (controller → service → repository)
     - Dependency flow violations
     - Boundary enforcement
     - Separation of concerns

  2. Domain-Driven Design:
     - Entity and value object design
     - Aggregate boundary violations
     - Domain logic leaking into infrastructure layer
     - Repository pattern adherence

  3. Technical debt:
     - Temporary workarounds without tracking
     - Incomplete implementations
     - Deprecated API usage

  4. Dependency management:
     - Circular dependencies
     - Unnecessary coupling
     - Interface vs implementation dependencies

  5. API compatibility (always check this):
     - Do any public method/function signatures change?
     - Are shared schemas, DTOs, or event payloads modified in backward-incompatible ways?
     - Are existing callers of modified functions still satisfied?
     - Are interface contracts preserved for downstream consumers?

  6. System-level performance (flag only when clearly applicable):
     - New synchronous calls to remote services in a hot path (should be async or cached)
     - Missing caching on repeated identical external calls
     - N+1 service calls (calling downstream service once per item in a loop)
     - Pagination missing on endpoints or queries that could return unbounded result sets

  For each finding provide:
  - file:line or module
  - Issue description and architectural impact
  - Severity: BLOCKER / CRITICAL / MAJOR / NIT
  - Category confidence (0-100)
  - Suggested fix (code snippet required for BLOCKER/CRITICAL)
  """
)
```

**Database Agent** (if applicable):
```
Agent(
  subagent_type: "postgres-optimizer",
  description: "Review database code in ${1:-.}",
  prompt: """
  CONTEXT: {DIFF_SUMMARY}

  If no SQL, ORM, or migration code is present in this diff, respond: "Not applicable — no database code in diff." Otherwise:

  Checklist:
  1. Query performance:
     - N+1 query problems
     - Missing indexes for new query patterns
     - Inefficient joins or subqueries
     - Missing or broken pagination

  2. Schema design:
     - Normalization issues
     - Foreign key usage and referential integrity
     - Data type optimization
     - Index strategy

  3. PostgreSQL usage:
     - JSONB opportunities
     - Array types
     - Window functions where applicable
     - Native features underutilized

  4. Transaction management:
     - Missing transaction boundaries
     - Inappropriate isolation level
     - Potential deadlock patterns

  For each finding provide:
  - file:line or query location
  - Issue description and performance impact
  - Severity: BLOCKER / CRITICAL / MAJOR / NIT
  - Category confidence (0-100)
  - Suggested fix (code snippet required for BLOCKER/CRITICAL)
  """
)
```

**Security Agent** *(new)*:
```
Agent(
  subagent_type: "claude",
  description: "Security review in ${1:-.}",
  prompt: """
  CONTEXT: {DIFF_SUMMARY}

  You are a security reviewer. Review ONLY security issues. Do not report code quality, style, or architecture concerns.

  For each OWASP category below: (1) determine if the diff touches relevant code, (2) if yes, check for issues.

  1. Injection: SQL/command/LDAP/XSS. Look for string concatenation in queries, unescaped user input in templates.
  2. Broken authentication/authorization: Hardcoded credentials, weak sessions, missing auth checks, IDOR, privilege escalation.
  3. Sensitive data exposure: PII in logs, unencrypted sensitive storage, overly broad API responses.
  4. Security misconfiguration: Debug endpoints enabled, default credentials, unnecessary permissions.
  5. Vulnerable dependencies: New deps with known CVEs, major version downgrades of security libraries.
  6. Cryptographic failures: Weak algorithms (MD5/SHA1 for passwords), insecure random for tokens, hardcoded keys.
  7. Deserialization: Untrusted data passed to deserializers without type constraints.
  8. SSRF: User-controlled URLs passed to internal HTTP clients without allowlist.
  9. Access control: Missing authorization on new endpoints, path traversal risks.
  10. Insufficient logging: New security-relevant operations (auth, payments, admin) without audit logging.

  For each finding provide:
  - file:line
  - Issue description and exploit scenario
  - Severity: BLOCKER / CRITICAL / MAJOR / NIT
  - Category confidence (0-100): only report ≥75
  - Suggested fix with code snippet (required for all security findings)

  If no security issues found: "No security issues found. Categories checked: [list]."
  """
)
```

---

### Step 2: Skeptic Pass (adversarial filter)

After all five agents return, run an adversarial review to eliminate false positives.

```
Agent(
  subagent_type: "claude",
  description: "Adversarial skeptic pass on review findings",
  prompt: """
  You are a skeptical senior engineer. Your job is to challenge every finding from the parallel review agents and discard false positives.

  [INSERT ALL FINDINGS FROM STEP 1 HERE]

  For each finding, challenge on these criteria:
  1. Intentional? Is there a plausible reason a competent engineer would write it this way? If yes: DISCARD or DOWNGRADE.
  2. Actionable? Is the file:line specific? Is the suggested fix unambiguous? If no: DISCARD.
  3. Severity correct? Does the stated severity match the actual blast radius? If too high: DOWNGRADE.

  Rules:
  - DISCARD findings with category confidence < 75
  - DISCARD findings without a specific file:line
  - KEEP pre-existing issues — "not introduced by this diff" is NOT a reason to discard; if it is a real problem, it gets fixed
  - KEEP any finding that survives all challenges

  Output: For each finding — KEEP / DISCARD / DOWNGRADE with one-line reason.
  Then: Final consolidated list of kept/downgraded findings only.
  """
)
```

---

### Step 3: Consolidate Findings

Compile the final report after the skeptic pass.

**Severity definitions:**

| Label | Definition | Action |
|-------|------------|--------|
| `[BLOCKER]` | Security exploit, provable crash, breaking API change | Must fix before merge |
| `[CRITICAL]` | Logic error, data integrity risk, N+1 in hot path | Should fix in this PR |
| `[MAJOR]` | Missing test coverage, design improvement, unhandled recoverable error | Fix soon, can be follow-up |
| `[NIT]` | Naming, style beyond linter, optional polish | Author's discretion |

**Cap:** Report max 3 BLOCKER + 8 non-BLOCKER. If more found, state count and top items.

**Output template:**

```markdown
# Code Review Report

**Date**: [date]
**Path**: ${1:-.}
**Dimensions**: Testing, Code Quality, Architecture, Database, Security
**After skeptic pass**: N BLOCKER | N CRITICAL | N MAJOR | N NIT

---

## [BLOCKER] Must Fix Before Merge (N)

- `path/file.ext:42` — **[Security]** SQL injection: raw user input in query string.
  Fix: `db.query("SELECT * FROM users WHERE id = ?", [userId])`

---

## [CRITICAL] Should Fix in This PR (N)

- `path/file.ext:120` — **[Architecture]** Payment flow missing transaction boundary (lines 118–135).
  Fix: Wrap in `@Transactional` or explicit begin/commit.

---

## [MAJOR] Fix Soon (N)

- `path/file.ext:200` — **[Testing]** New `calculateDiscount()` path has no test coverage.

---

## [NIT] Optional (N)

- `path/file.ext:15` — **[Code Quality]** `processData()` name is vague; rename to reflect behavior.

---

## Dimensions Not Applicable

- **Database**: No SQL or ORM code in diff — skipped.

---

## Live PR Review Threads (unresolved)

- `path/file.ext:88` — @reviewer (opened [date]): one-line summary of the comment. Not yet addressed.

(Omit this section entirely if Step 0.5 found no open PR or zero unresolved threads.)

---

## Effort Estimate

- Critical path (BLOCKERs + CRITICALs): ~N hours
- Follow-up (MAJORs): ~N hours
```

---

### Step 4: Track with Project Coordinator

```
Agent(
  subagent_type: "project-coordinator",
  description: "Track code review findings",
  prompt: """
  Document the following code review findings for systematic remediation:

  [INSERT CONSOLIDATED REPORT FROM STEP 3]

  Using the Implementation Plan format:
  1. Create ATOMIC tasks per finding, grouped by severity
  2. Prioritization: BLOCKER → CRITICAL → MAJOR → NIT
  3. Batch related issues (same file, same pattern) for efficiency
  4. Define clear success criteria per task
  5. Link each task to specific file:line
  6. Track technical debt reduction metrics

  Deliverables:
  - Structured task list organized by priority and effort
  - Clear next actions for developers
  - Progress tracking mechanism
  """
)
```

---

## Parallel Execution Strategy

```
Step 0: Diff summary (fast, sequential prerequisite)
     ↓
Step 1: [Testing] [Code Quality] [Architecture] [Database] [Security]  ← parallel
     ↓
Step 2: Skeptic Pass (reads Step 1 output — sequential)
     ↓
Step 3: Consolidate → Severity-labeled report
     ↓
Step 4: Project Coordinator (optional)
```

**Performance:**
- 5 agents in parallel: ~8-12 minutes total
- Skeptic pass: ~2 minutes additional
- False positive reduction: ~30-40% fewer noise findings vs unfiltered parallel review

---

## Success Criteria

- ✅ All 5 dimensions evaluated (or "not applicable" stated with reason)
- ✅ Skeptic pass completed — no unfiltered raw findings in report
- ✅ Every BLOCKER/CRITICAL includes a code snippet suggested fix
- ✅ Severity labels on every finding
- ✅ Finding count within cap (≤3 BLOCKER + 8 non-BLOCKER reported)
- ✅ Dimensions not applicable to the diff are explicitly noted

---

## Review Pipeline — How These Commands Chain

`/code:review` is the diagnostic center of a larger workflow. Use commands before and after it:

```
[before]  /quality:does-it-work       — build/test/lint sanity check before requesting review
          /quality:find-test-smells   — deeper test-only analysis before review
          ↓
[review]  /code:review                — 5-agent parallel review + skeptic pass
          ↓
[after]   fix BLOCKER/CRITICAL findings
          /quality:reflect-and-fix    — after fixing bugs: make recurrence structurally impossible
          /quality:test-planner       — when review finds test coverage MAJOR gaps: plan tests
          /code:fix-loop              — auto-fix loop for remaining build/test/lint failures
          lean-agent-loop skill       — custom iterative check loops when categories differ from build/test/lint
          ↓
[ship]    /code:is-it-ready           — final shipping gate: 7-reviewer swarm → GO/HOLD/FIX-THEN-SHIP
```

**For deeper analysis on specific MAJOR findings:**
- `/quality:architecture-review` — deep architectural analysis (when Architecture agent finds systemic issues)
- `/quality:find-refactor-candidates` — when Code Quality agent flags many MAJOR refactoring needs
- `/code:refactor` — execute recommended refactorings
- `/security-review` — standalone security-only deep dive
- `/plan:feature` — plan MAJOR findings as tracked follow-up features

---

## Notes

- **Diff summary prefix** matters: LLM review accuracy improves significantly when agents know what the PR does before reading the diff
- **Skeptic pass** targets the largest practical improvement: filtering false positives before they reach the report
- **Severity caps** prevent review fatigue — a 15-item list is ignored; a 5-item list with fix suggestions gets fixed
- **Security agent** focuses exclusively on OWASP — a generalist agent misses 2/3 of security issues that a specialist catches
- **API compat in Architecture** catches the most commonly missed breaking-change bug class
