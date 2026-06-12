---
description: "Phase 6 — Dynamic idiom review, architecture review, refactor pass, then correctness + test gate before shipping."
user-invocable: true
---

# sdd:6-verify

Review the implementation across three layers — language idioms, architecture quality, and correctness — before shipping. Findings in the first two layers may loop back to Phase 5 for a refactor pass. Test failures always block.

## Three-Layer Review Model

```
Layer 1 — Idioms & Best Practices   (parallel agents, dynamically matched to diff)
Layer 2 — Architecture & Design     (parallel agents, pattern-level)
Layer 3 — Correctness & Tests       (inline, hard gate)

Verdicts:
  🔁 REFACTOR  → structural issues → return to /sdd:5-implement, fix, re-run /sdd:6-verify
  ❌ BLOCKED   → test failures, security holes, or missing acceptance criteria
  ✅ PASS      → all three layers clean → proceed to /sdd:7-ship
```

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Get the diff and fingerprint the technology surface:**
   ```bash
   git diff main...HEAD --stat
   git diff main...HEAD
   ```

   For each changed file, identify: file extension, imported packages/frameworks, and any
   technology-specific patterns (e.g. `entgo`, `connectrpc`, `vanilla-extract`, `testing.T`).
   Build a **technology surface map** — one entry per distinct technology detected:

   ```
   Example surface map:
   - Go (files: scanner.go, vcsreader.go) — packages: go-git, sync, context
   - TypeScript/React (files: DormantBranchCard.tsx) — frameworks: React, vanilla-extract
   - Protobuf (files: unfinished.proto) — version: proto3
   - SQL migration (files: 001_add_branches.sql) — engine: SQLite
   - Ent ORM (files: schema/branch.go) — generated: yes
   ```

3. **For each technology in the surface map, select the review approach:**

   ### Skill lookup table (check this first)

   #### Go

   | Technology / Pattern | Skill | Focus areas |
   |---|---|---|
   | Go — general idioms | `go-development` | error wrapping (errors.Is/As), interface sizing (accept interfaces, return structs), naming (receiver names, unexported fields), zero-value usability |
   | Go — concurrency | `go-development` | goroutine lifecycle, context cancellation propagation, channel directionality, sync.Mutex vs sync.RWMutex, double-checked locking anti-patterns, goroutine leak detection |
   | Go — performance hot paths | `go:optimize` | alloc-free hot paths (AllocsPerRun), sync.Pool usage, map pre-allocation, early-return guards before heap allocs, avoid string([]byte) in loops |
   | Go — testing | `go-development` | table-driven tests, t.Helper() usage, testify assert vs require, subtests (t.Run), avoiding global state in tests |
   | Go — ORM / database (ent) | research agent | see Rust section below for how to invoke the research fallback |
   | Go — RPC / ConnectRPC | research agent | idem |
   | Go — go-git / VCS ops | `code-go-git` | per-repo `sync.Mutex` (NOT RWMutex) covering full iterator lifetime; never cache `CommitIter` or `*Worktree`; `wt.Status()` is concurrency-unsafe and pathologically slow on large repos |

   #### Rust

   | Technology / Pattern | Skill | Focus areas |
   |---|---|---|
   | Rust — general idioms | research agent | ownership & borrowing (prefer borrows over clones), `?` operator vs `unwrap`, `Into`/`From` conversions, iterator chaining over manual loops, `#[derive]` completeness |
   | Rust — error handling | research agent | `thiserror` for library errors, `anyhow` for application errors, never use `.unwrap()` in library code, `Box<dyn Error>` only as last resort |
   | Rust — async / Tokio | research agent | `async fn` in traits (RPITIT), `tokio::spawn` lifecycle, `select!` cancellation safety, avoiding blocking in async context (`spawn_blocking`), `Arc<Mutex<T>>` vs channels |
   | Rust — unsafe | research agent | mandatory `// SAFETY:` comment on every `unsafe` block, minimize unsafe surface, prefer safe abstractions |
   | Rust — performance | research agent | zero-copy parsing, `Cow<str>` for optional ownership, avoid `Box<dyn Trait>` in hot paths, `#[inline]` only when benchmarked |
   | Rust — CLI (clap) | research agent | derive API vs builder API, subcommand structure |
   | Rust — WebAssembly (wasm-bindgen) | research agent | `JsValue` error handling, avoiding panics in WASM |

   #### Frontend

   | Technology / Pattern | Skill | Focus areas |
   |---|---|---|
   | TypeScript / React / Next.js | `ui-react-best-practices` | hook dependency arrays, unnecessary re-renders, prop drilling vs context, discriminated unions, component single-responsibility |
   | CSS / vanilla-extract / CSS Modules | `ui-web-design-guidelines` | no hardcoded hex (use `vars`), no magic zIndex numbers, `createPortal` for fixed overlays, no inline `style={{}}` for layout |
   | UI component composition | `ui-composition-patterns` | compound components, render props vs composition, controlled vs uncontrolled |
   | Design system tokens | `ui-design-system` | token usage consistency, no one-off values |

   #### Data & Infrastructure

   | Technology / Pattern | Skill | Focus areas |
   |---|---|---|
   | SQL / database schema | `db:review` | index coverage, nullable correctness, migration reversibility |
   | Database antipatterns | `db:antipatterns` | N+1 queries, missing transactions, over-wide SELECT |
   | Type-level design | `type-driven-design` | branded types, discriminated unions, make invalid states unrepresentable |
   | Protobuf / gRPC | research agent | field numbering, backward-compatible additions only, reserved fields for deleted numbers |

   ### Fallback: research → synthesize → skill candidate analysis (for anything NOT in the table above)

   If a technology has no matching skill, run a **three-step pipeline** before dispatching
   the idiom review. Steps 1 and 2 run sequentially (2 depends on 1); step 3 runs in
   parallel with the Layer 1 review agents.

   #### Step F-1: Research agent — fetch current idioms

   Spawn a research agent with this prompt:
   > "Research current best practices and idiomatic patterns for `<technology> <version>` as of 2026.
   > Include: error handling conventions, naming rules, anti-patterns to avoid, performance
   > considerations, and patterns that are idiomatic vs. common-but-wrong.
   > Also note: any recent breaking changes or deprecations in the last 12 months that affect
   > code review decisions.
   > Output format: a numbered checklist of max 15 items, each tagged [ERROR] [NAMING]
   > [PERF] [ANTI-PATTERN] or [STYLE] so reviewers can filter by concern type."

   #### Step F-2: Synthesis — distill into a reviewable checklist

   After the research agent returns, synthesize its output into a structured review checklist:
   ```
   Technology: <name> <version>
   Source: <research agent summary>
   Checklist:
   1. [ERROR] <item> — severity: MUST FIX if violated
   2. [NAMING] <item> — severity: SUGGEST
   ...
   ```
   This checklist becomes the review prompt for the idiom agent on this technology's diff slice.

   #### Step F-2.5: Append to observations log

   After synthesizing the checklist, always append an entry to `~/.claude/logs/observations.md`:
   ```
   [YYYY-MM-DD] [SKILL-CANDIDATE] <technology> — hit sdd:6-verify research fallback in
   <PROJECT_NAME>. Focus areas: <top 3 checklist items>. Score pending (F-3).
   ```
   If this technology has a prior entry in the log, note the recurrence count:
   `(occurrence 2 — prev: YYYY-MM-DD)`. This count feeds into the F-3 recurrence score.

   #### Step F-3: Skill candidate analysis (parallel with Layer 1 review)

   Simultaneously with dispatching the Layer 1 review, spawn a **skill candidate agent**:

   > "Analyse whether the following research findings for `<technology>` are stable enough to
   > warrant creating a permanent idiom review skill in the `sdd:6-verify` lookup table.
   >
   > Score against these criteria (each 0–2):
   > - **Recurrence** (0–2): How likely is this technology to appear in future diffs?
   >   0 = one-off experiment, 1 = occasional, 2 = core stack
   > - **Stability** (0–2): Are the idioms stable and unlikely to change?
   >   0 = rapidly evolving, 1 = mostly stable, 2 = very stable
   > - **Actionability** (0–2): Are there ≥8 checklist items with clear MUST FIX / SUGGEST grades?
   >   0 = vague, 1 = partially actionable, 2 = fully actionable
   > - **Differentiation** (0–2): Does this need a dedicated skill, or is it covered by a broader
   >   existing skill with minor additions?
   >   0 = fully covered, 1 = partial gap, 2 = clearly distinct
   >
   > Total score: X/8
   >
   > If total ≥ 5:
   >   1. Invoke `/skill:create <group>-<technology-kebab-case> "Idiomatic review for <technology>"
   >      user` using the synthesized checklist as the SKILL.md core content.
   >   2. Add a new row to the skill lookup table in
   >      `~/dotfiles/plugins/sdd/commands/6-verify.md` (and sync to all cache paths) with
   >      the format:
   >      `| <Technology> | \`<skill-name>\` | <top 3 focus areas from checklist> |`
   >   3. Report: skill created at `~/.claude/skills/<skill-name>/`, lookup table updated.
   >
   > If total < 5:
   >   Report: score X/8 — not stable enough for a permanent skill yet. Re-evaluate after
   >   the next 2 occurrences of this technology in a diff.
   >
   > Research findings: `<paste Step F-2 checklist>`"

   This creates a self-improving ratchet: each research fallback either produces a new permanent
   skill (score ≥ 5) or records a data point toward the threshold. The lookup table grows
   automatically as the stack evolves.

4. **Dispatch all Layer 1 and Layer 2 agents in a single parallel message.**

   ### Layer 1 — Language & Technology Idioms (one agent per technology in surface map)

   For each technology:
   - If it has a matching skill: use that skill as the `subagent_type`
   - If it needed a research agent in step 3: use `general-purpose` with the research checklist as context
   - Always scope the diff to only the files relevant to that technology
   - Standard prompt structure:
     > "Using the following idiom checklist for `<technology>`, review the attached diff.
     > For each finding: file:line, severity (MUST FIX / SUGGEST / NITPICK), and a concrete fix.
     > Do not flag issues outside this technology's scope.
     > Checklist: `<checklist from skill or research agent>`
     > Diff: `<diff slice for this technology>`"

   ### Layer 2 — Architecture & Design Quality (always two agents, regardless of technology)

   **Agent: Architecture review**
   - Use the `code-architecture-best-practices` subagent type
   - Prompt: "Review this implementation diff for architecture quality: SOLID violations,
     inappropriate coupling between packages, missing abstractions where duplication will hurt,
     over-engineering, testability of new components in isolation, and consistency with the
     existing architecture. Also read `project_plans/<PROJECT_NAME>/implementation/plan.md`
     to check whether the implementation matches the design intent.
     Diff: `<full diff>`"
   - Output: BLOCKER / CONCERN / NITPICK findings with rationale

   **Agent: Refactor candidates**
   - Use the `code-refactoring` subagent type
   - Prompt: "Review this diff for refactoring opportunities: repeated logic that could be
     extracted, functions doing more than one thing, names that don't reflect intent, dead
     code, and any pattern that will be painful to change in 6 months.
     Flag only things introduced in this diff — do not suggest out-of-scope changes.
     Diff: `<full diff>`"
   - Output: prioritised list of refactors with estimated effort

5. **Wait for all Layer 1 and Layer 2 agents to complete.**

6. **Classify findings and decide whether a refactor pass is needed:**

   | Severity | Action |
   |---|---|
   | Any BLOCKER from architecture review | 🔁 REFACTOR — return to Phase 5 |
   | ≥3 MUST FIX idiom findings in a single file | 🔁 REFACTOR — return to Phase 5 |
   | SUGGEST / CONCERN findings | Apply inline if <30 min total; otherwise note as follow-up |
   | NITPICK findings | Note only; do not block |

   If REFACTOR verdict: stop here. Return to `/sdd:5-implement` with a list of what to fix.
   Re-run `/sdd:6-verify` after the refactor. This REFACTOR → re-verify cycle follows the `lean-agent-loop` skill pattern — apply that skill if the cycle needs to be automated across multiple iterations.

7. **Layer 3 — Correctness & Tests** (only if Layers 1 + 2 did not trigger REFACTOR)

   a. **Verify acceptance criteria.** For each story in `plan.md`, confirm every acceptance
      criterion is met in the diff.

   b. **Run the test suite.** Use the appropriate command for the stack. Show the output —
      do not claim tests pass without running them.

   c. **Check security:** injection, auth gaps, exposed secrets, input validation at system boundaries.

   d. **Check error handling:** all errors from external calls (git, DB, RPC) are handled and
      surfaced appropriately.

8. **Output the verification report:**

```
## Verification Report — <PROJECT_NAME>

### Technology Surface
| Technology | Files | Review approach |
|---|---|---|
| Go | scanner.go, vcsreader.go | go-development skill |
| TypeScript/React | DormantBranchCard.tsx | ui-react-best-practices skill |
| Protobuf | unfinished.proto | research agent → checklist |

### Layer 1 — Idioms
| Technology | Findings | MUST FIX | Action taken |
|---|---|---|---|
| Go | 3 findings | 1 | Fixed inline |
| TypeScript | 2 findings | 0 | Noted as follow-up |
| Protobuf | 1 finding | 0 | Noted |

### Layer 2 — Architecture
| Finding | Severity | Action |
|---|---|---|
| <description> | BLOCKER / CONCERN / NITPICK | Fixed / follow-up / noted |

### Layer 3 — Correctness
| Story | Criterion | Status |
|---|---|---|
| 1.1.1 | <criterion> | ✅ |

### Tests
Tests: <N> passed, <N> failed, <N> skipped

### Security
<✅ No issues / ⚠️ Warnings / ❌ Blockers>

### Verdict
<✅ PASS — ready for /sdd:7-ship>
<🔁 REFACTOR — return to /sdd:5-implement: [list of issues]>
<❌ BLOCKED — fix N issue(s) before proceeding: [list]>
```

9. **If REFACTOR or BLOCKED**: list each issue with the exact file, line, and a concrete fix.
   Do not proceed until all violations are resolved and the full review is re-run.
