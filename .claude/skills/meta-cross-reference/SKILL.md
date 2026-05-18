---
name: meta-cross-reference
description: >-
  Audit a SKILL.md file for missing cross-references to related skills, or map
  a task description to the skills that should be combined to handle it. Writes
  inline section callouts and "Related Skills" tables using the canonical pattern.
  Use when improving an existing skill, building a new one, or determining which
  skills to activate for a complex multi-domain task.
when_to_use: "Add cross-references to a skill, audit SKILL.md for missing related-skill links, build a Related Skills table, find which skills apply to a task, map a feature to its skill stack"
---

# Cross-Reference Skills

## Two Modes

### Mode 1 — Skill Audit
Given a `SKILL.md` path: read it, identify gaps in skill cross-references, then write:
1. **Inline callouts** above the specific sections that benefit from a companion skill
2. A **Related Skills table** at the end of the file (create or update the existing one)

### Mode 2 — Task Mapping
Given a task description or feature request: identify which skills apply, in what order,
and whether any should run in parallel. Output a short activation plan.

---

## Process: Skill Audit

1. **Read** the target `SKILL.md` fully
2. **Identify the domain** — what problem space does this skill own?
3. **For each major section**, ask: does any skill in the catalog deepen, extend, or guard this topic?
4. **Determine placement**:
   - Companion that applies to **one specific section** → inline callout above that section header
   - Companion that applies to the **whole skill or multiple sections** → row in Related Skills table
5. **Write inline callouts** using this format (immediately before the `##` header):
   ```markdown
   > For X and Y, apply the `skill-name` skill.
   ```
6. **Write or update the Related Skills table** at the end of the file:
   ```markdown
   ## Related Skills

   | Skill | When to apply |
   |-------|--------------|
   | `skill-name` | One-line description of the trigger condition |
   ```
7. **Do not duplicate**: if a callout already exists for a skill, don't add it again

---

## Process: Task Mapping

1. Parse the task for domain signals (see catalog below)
2. Identify the **primary skill** (owns the main deliverable)
3. Identify **supporting skills** (apply before, during, or after)
4. Note any skills that should run **in parallel** (independent sub-tasks)
5. Output in this format:

```
Primary:    code-python
Before:     code-architecture-best-practices (design the layer structure first)
During:     type-driven-design (as domain model is built)
After:      code-review, security-review
Parallel:   —
```

---

## Skill Catalog

Read the system-reminder for the authoritative live list. Use this catalog for semantic matching.

### Code & Architecture

| Skill | Owns |
|-------|------|
| `code-architecture-best-practices` | SOLID, Clean Architecture, Hexagonal/DDD, module boundaries, dependency direction |
| `design-patterns` | GoF (Factory, Strategy, Observer…) and PoEAA (Repository, Service Layer, Unit of Work) |
| `type-driven-design` | Encoding invariants into the type system: NewType, smart constructors, sum types, refinement types, parse-don't-validate |
| `code-python` | Python standards: uv, type annotations, pytest, Pydantic, async, hexagonal, structlog |
| `code-spring-boot` | Spring Boot Java: layering, testing, security, data access |
| `go-development` | Go idioms, error handling, interfaces, testing |
| `code-refactoring` | Large structural refactors via `ast-grep` (scope) + `gritql` (transformation) with quality gates |
| `code-ast-grep` | Structural code search — find all usages of a pattern across files |
| `code-gritql` | Automated multi-file code transformations (renames, API migrations, bulk modernization) |

### Debugging & Quality

| Skill | Owns |
|-------|------|
| `code-debugging` | Systematic 4-phase bug investigation: root cause → pattern analysis → hypothesis → fix; defense-in-depth validation; verification before claiming done |
| `code-root-cause-analysis` | Error + incident investigation via stack traces, Logseq history search, log correlation |
| `code-review` | Receiving PR feedback with technical rigor; requesting a `code-reviewer` subagent; verification gates before completion claims |
| `code-archaeology` | Understanding an unfamiliar codebase via git history, grep, call graphs |
| `quality:find-test-smells` | Identify brittle, over-mocked, or poorly scoped tests |
| `quality:reflect-and-fix` | Post-task self-review: check for regressions, missed edge cases, anti-patterns |
| `quality:architecture-review` | Evaluate structural decisions against architecture principles |

### Testing & Infrastructure

| Skill | Owns |
|-------|------|
| `infra-testing` | TestKube, PGBouncer, Kubernetes integration test execution |
| `infra-docker-build-test` | Docker build + test pre-push validation checklist; CI failure prevention |
| `infra-homebrew` | Homebrew formula install/upgrade; missing CLI tool resolution |
| `ui-playwright` | Playwright E2E test writing and debugging |

### Security

| Skill | Owns |
|-------|------|
| `security-review` | Adversarial OWASP Top 10 audit: injection (SQL, OS, template), broken auth, secrets in code, dependency CVEs, insecure deserialization |

### Version Control & CI/CD

| Skill | Owns |
|-------|------|
| `github-pr` | GitHub PR creation, review, CI status, gh CLI patterns |
| `github-actions-debugging` | GitHub Actions workflow failure analysis: syntax errors, env issues, timeouts, permissions |
| `github-address-pr-comments` | Systematically address open review comments on a PR |
| `jj-version-control` | Jujutsu (jj) commits, rebases, bookmarks, revsets |
| `sync-remotes` | Sync git remotes (fork → upstream, multi-remote push) |

### Language-Specific Performance

| Skill | Owns |
|-------|------|
| `rust-profiling` | Rust flamegraphs, samply, perf, heaptrack — data collection |
| `rust-perf-tuning` | Rust optimization: allocations, hot loops, rayon, SIMD, LTO/PGO — applies fixes from profiling data |
| `go-profiling` | Go pprof, flamegraphs, benchmark analysis |
| `jvm-performance` | JVM heap, GC, threading, JIT tuning |
| `jfr-profiling` | Java Flight Recorder analysis |

### Meta / AI

| Skill | Owns |
|-------|------|
| `meta-prompt-engineering` | Prompt design: XML tags, few-shot examples, CoT, Claude 4-specific patterns |
| `meta-context-engineering` | Context optimization for agent systems: compaction, masking, caching, memory architectures |
| `meta-model-selection` | Choose the right Claude model (Opus/Sonnet/Haiku) for a given task |
| `meta-claude-technique-evaluator` | Evaluate whether a Claude technique (tool use, subagents, etc.) is appropriate |
| `meta-research-workflow` | Systematic multi-step web research: Brave Search, Puppeteer, source synthesis |

### Knowledge & Documentation

| Skill | Owns |
|-------|------|
| `knowledge-synthesis` | Zettelkasten notes for Logseq; wiki pages; interconnected knowledge with `[[links]]` |
| `knowledge-literature-review` | Survey a research area: key papers, arXiv/Semantic Scholar, citation graphs, reading lists |
| `code-archaeology` | (also in debugging) — understand existing code before modifying it |

### Planning & Workflow

| Skill | Owns |
|-------|------|
| `sdd:full` | Full SDD workflow: ideate → research → plan → validate → implement → verify → ship |
| `sdd:quick` | One-shot workflow for simple tasks that fit in a single context window |
| `plan:feature` | Feature planning with INVEST breakdown and implementation roadmap |
| `plan:fix-bug` | Bug fix planning with root cause + test strategy |

### UI / UX

| Skill | Owns |
|-------|------|
| `ui-react-best-practices` | React component patterns, hooks, state management |
| `ui-playwright` | Playwright E2E test authoring |
| `ux:review` | Heuristic UX evaluation |
| `ux:design` | UX/UI design guidance |

---

## Cross-Reference Affinity Pairs

These skills frequently appear together — use these as a quick matching guide:

| If the skill covers… | Also reference… |
|----------------------|-----------------|
| Domain modeling / entities | `type-driven-design`, `design-patterns` |
| Layered / hexagonal architecture | `code-architecture-best-practices` |
| Testing patterns | `code-debugging`, `quality:find-test-smells` |
| Async / concurrency | `code-debugging` (race conditions), `security-review` (DoS via unbounded concurrency) |
| HTTP clients / API integration | `security-review` (injection, auth), `code-debugging` |
| Logging / observability | `code-root-cause-analysis` |
| Configuration / secrets | `security-review` |
| Large refactors | `code-refactoring`, `code-ast-grep`, `code-review` |
| New feature implementation | `code-architecture-best-practices`, `security-review`, `code-review` |
| Performance-critical code | `rust-profiling` / `go-profiling` / `jvm-performance` (pick by language) |
| Docker / containers | `infra-docker-build-test`, `security-review` |
| CI/CD pipelines | `github-actions-debugging`, `infra-docker-build-test` |
| Prompt / agent design | `meta-prompt-engineering`, `meta-context-engineering`, `meta-model-selection` |

---

## Output Rules

- Reference skills by exact backtick name: `` `skill-name` ``
- Inline callouts: one sentence, start with the trigger condition ("When X…", "For Y…")
- Related Skills table: one row per skill, "When to apply" column is ≤15 words
- Never add a cross-reference to the skill being audited (no self-reference)
- If a skill isn't in the catalog but fits, check the system-reminder for the exact name before referencing it
- Prefer inline callouts for section-specific relationships; use the table for skills that apply broadly
