# Manifest-Driven Development
### The Stapler System — v1.0

> *Spec-anchored, knowledge-first, phase-gated AI development for the solo practitioner.*

---

## Naming

This system is called **Manifest-Driven Development** (MDD). The name does triple work:

1. **Manifest as artifact** — a declared statement of intent before action. You write manifests (requirements.md, plan.md, validation.md) before building, just as infrastructure engineers write Kubernetes manifests before deploying.
2. **Manifest as verb** — to manifest is to make something real from specification. Each phase manifests the previous artifact into concrete form.
3. **Manifest as philosophy** — opinionated constraints, declared upfront. Your CLAUDE.md is your manifest for how AI should behave in your work.

Runner-up: **Staple-Driven Development** (also SDD — same acronym as the broader pattern, personal to you).

---

## What This Is

MDD is a personal AI development system for a solo practitioner who works across two contexts — building tools for a personal knowledge wiki and delivering platform engineering work at FBG — using a single, unified workflow that treats spec artifacts as first-class, enforces phase gates, and routes all accumulated learning through a Logseq knowledge graph rather than flat memory files.

It is **not** a fleet manager. It is **not** a config pack. It is a workflow with opinions encoded in tools.

---

## Position in the SDD Taxonomy

Fowler (2025) defines three levels of spec-driven development:

| Level | Definition | This System |
|---|---|---|
| **Spec-first** | Write a spec before generating code | ✅ Always enforced via phase gate |
| **Spec-anchored** | Keep specs as living artifacts after the task | ✅ `project_plans/` persists; phases carry forward |
| **Spec-as-source** | Humans only edit specs, never code | ❌ Not this — human stays in the loop at every gate |

The key distinction Fowler makes — between **memory bank** (always-loaded context) and **spec** (task-scoped artifact) — is architecturally resolved here. Most SDD tools conflate them. This system keeps them as separate layers with different lifecycles.

One thing existing SDD tools don't do: treat the memory bank as a **living knowledge graph**. Kiro has 3 steering files. Spec-kit has a constitution.md. This system has a Zettelkasten wiki with bi-directional links, daily journals, and automated processing pipelines. The memory bank grows continuously and organically.

---

## The Core Opinions

These are the non-negotiables. They encode what has been learned through repeated experience.

1. **Spec before code, always.** No implementation session starts without requirements.md + plan.md + validation.md. This is not a suggestion.

2. **Planning context poisons implementation.** The research and debate that happens during planning degrades code generation quality. Fresh session before implementation is physics, not preference.

3. **Artifacts over memory.** Write down every phase output. Don't trust the context window to carry decisions. The file system is the source of truth.

4. **Parallel by default.** Research has four independent dimensions (stack, features, architecture, pitfalls). Implementation has independent tasks. Spawn agents, isolate context, synthesize from files.

5. **Validation maps to requirements.** Test coverage is designed before a line of code is written. validation.md traces test cases to requirements line-by-line.

6. **Verification before completion.** No completion claim without fresh evidence. Run the test. Read the output. Then say it passes.

7. **Context is a budget.** Skills loaded, MCP servers configured, CLAUDE.md length — these are token costs that degrade reasoning. Audit them deliberately.

8. **The wiki is the brain.** Session learnings flow into MEMORY.md then into Logseq. The knowledge graph is the memory bank, not a supplement. If it isn't in the wiki, it isn't known.

9. **Scale gates to problem size.** A two-line bug fix needs planning + verification. A new sync feature needs all six phases. The gates are real; the mandatory artifacts determine which ones to run.

---

## The Workflow

### Session Types

```
PLANNING SESSION
  Input:  User's idea
  Phases: Ideation → Research → Planning → Validation
  Output: requirements.md, research/*.md, plan.md, validation.md
  Rule:   Never write production code in a planning session

IMPLEMENTATION SESSION
  Input:  plan.md + validation.md (from a prior planning session)
  Phases: Implementation → QA
  Output: Code + passing tests + sign-off
  Rule:   Must start fresh; planning session context must not carry over

MAINTENANCE SESSION
  Input:  Bug report, review comment, or small change
  Phases: Planning + QA only (skip research for small changes)
  Output: Fix + verification
  Rule:   Scale formality to problem size
```

### Phase Gates

```
Ideation ──────────────────→ requirements.md
          AskUserQuestion
          interview

Research ──────────────────→ research/stack.md
          Parallel agents:    research/features.md
          stack | features    research/architecture.md
          architecture |      research/pitfalls.md
          pitfalls

Planning ──────────────────→ implementation/plan.md
          /plan:feature
          reads: requirements.md
                 research/*.md

Validation ────────────────→ implementation/validation.md
           /quality:test-planner
           reads: plan.md
           maps:  test cases → requirements (line by line)

═══════════════ MANDATORY FRESH SESSION ════════════════

Implementation ─────────────→ code + passing tests
               /code:implement
               reads: plan.md + validation.md

QA ─────────────────────────→ sign-off or fix plan
   /quality:does-it-work
   /code:review
```

### Artifact Directory

```
project_plans/<project>/
├── requirements.md          ← ideation output
├── research/
│   ├── stack.md
│   ├── features.md
│   ├── architecture.md
│   └── pitfalls.md
├── decisions/
│   └── ADR-NNN-*.md         ← architecture decisions (Phase 3, on demand via /plan:adr)
└── implementation/
    ├── plan.md              ← planning output
    └── validation.md        ← validation output (before code)
```

---

## Memory Architecture

Three distinct layers with different lifetimes and loading semantics:

```
Layer 1: Always-Loaded (session context)
─────────────────────────────────────────
~/.claude/CLAUDE.md          phase gates, tool rules, workflow
~/.claude/MEMORY.md          accumulated instincts (← currently empty; needs hooks)
~/.claude/skills-index.md    skill dispatch table
~/.claude/RTK.md             role + domain context

Layer 2: Project-Scoped (task context)
───────────────────────────────────────
project_plans/<project>/     spec artifacts (requirements, research, plan, validation)
<repo>/CLAUDE.md             repo-specific rules

Layer 3: Knowledge Graph (long-term memory)
────────────────────────────────────────────
logseq/pages/                Zettelkasten notes — concepts, tools, decisions
logseq/journals/             Daily entries — observations, meeting notes, learnings
                             Processed via: [[Needs Synthesis]], [[Needs Research]],
                             [[Book Recommendation]], [[Needs Handy Plan]]
```

**The key architectural insight:** Layer 3 is the memory bank. Most SDD tools treat context documents as a few flat files. Here, the memory bank is a living knowledge graph that grows continuously and is processed by automated pipelines. When you learn something during a session, it flows:

```
session insight → MEMORY.md (Layer 1) → journal entry (Layer 3) → zettel (Layer 3) → wiki links
```

---

## Comparison: Gastown

Gastown (Yegge, 2025) is a multi-agent fleet orchestration system for 20-30 simultaneous worker agents across multiple repositories. Its optimization target is **throughput** — how fast can 30 agents collectively deliver work without losing state between restarts.

| Dimension | Gastown | This System |
|---|---|---|
| **Scale** | Fleet (20-30 agents) | Solo practitioner + subagents |
| **Optimization target** | Throughput across agents | Quality per artifact |
| **State persistence** | Dolt (git-backed SQL) ledger | `project_plans/` + Logseq |
| **Memory** | Per-agent JSONL session replay | Cross-session knowledge graph |
| **Agent lifecycle** | Witness-managed Polecats (persistent identity, ephemeral sessions) | Phase-fresh sessions (no persistent agent identity) |
| **Work routing** | Capability-based dispatch (planned) | Phase gates (human decides) |
| **Knowledge** | Agent work history CVs | Zettelkasten with bi-directional links |
| **Monitoring** | Deacon/Witness/Dogs watchdog chain | Verification gates before each phase |
| **Attribution** | Every action attributed to named agent | Human review at every gate |
| **Core metaphor** | Steam engine — pistons must fire | Spec forge — manifests become metal |

Gastown's Propulsion Principle ("if work is on your hook, you run it") maximizes autonomous throughput. This system's inverse is the Fresh Session Principle ("planning context must not bleed into implementation") — which optimizes for artifact quality over agent velocity.

Gastown is for managing a factory. This system is for doing the work of a very good craftsperson.

---

## Comparison: ECC (everything-claude-code)

ECC is a config pack + skills library. It solves: "I have Claude Code and I want best-practice defaults." It is spec-agnostic — a collection of patterns, not a workflow.

This system is workflow-primary and uses ECC skills selectively. The skills that were worth adopting: none wholesale. The concepts worth distilling:

- **Instinct model** (continuous-learning-v2) → implemented as MEMORY.md + hooks (planned)
- **Context audit** → `/meta:context-audit` command (planned)
- **Session hooks** → session-end hook writing to MEMORY.md (planned)

ECC calls itself a "harness performance system." This system is a **practitioner discipline**.

---

## Comparison: SDD Tools (Kiro, Spec-Kit, Tessl)

Fowler's critique of existing SDD tools: one workflow can't fit all problem sizes; verbose markdown review overhead; false sense of control.

This system addresses each directly:

| Fowler Critique | SDD Tools | This System |
|---|---|---|
| One-size workflow | Kiro: 3 fixed docs; spec-kit: 8 docs per feature | Scale gates to problem size (2 phases for bugs, 6 for features) |
| Review overhead | Spec-kit creates many repetitive files | Minimal artifacts; each produces exactly one document |
| False sense of control | Tools don't enforce anything | Phase gates are enforced by "never skip phases" rule in CLAUDE.md |
| Memory bank ≠ spec confusion | Most tools conflate them | Architecturally separate (3-layer memory vs task-scoped project_plans/) |
| No iterative approach | Waterfall-like spec phases | Fresh session means you can re-run any phase with new information |

The system is closer to spec-kit's philosophy (constitution-backed, checklist-enforced) than Kiro's (lightweight, 3 docs). But it avoids spec-kit's verbosity by making artifacts minimal and single-purpose.

---

## System Health

**Good state looks like:**
- MEMORY.md has entries from recent sessions
- `project_plans/` has active specs in progress
- Skills inventory is audited (token budget known)
- Recent Logseq journal entries have been processed

**Warning signs:**
- MEMORY.md is empty (← current state; session learning loop is broken)
- `project_plans/` has stale, never-implemented specs
- Implementation started without a plan.md
- Completion claimed without running verification

**Known gaps (as of 2026-04):**
- ~~No context budget audit command~~ → ✅ `/meta:context-audit` built
- ~~No session learning capture~~ → ✅ `/knowledge:extract-learnings` built
- No automated session-end hook to populate MEMORY.md automatically (currently manual)
- No hook to suggest compaction at 80% utilization
- `stapler-learning` skill (Logseq-native instinct storage) not yet built

---

## Quick Reference

| Phase | Command | Reads | Writes |
|---|---|---|---|
| Ideation | `AskUserQuestion` | — | `requirements.md` |
| Research | `/research-workflow` | `requirements.md` | `research/*.md` |
| Planning | `/plan:feature` | `requirements.md` + `research/` | `implementation/plan.md` + `decisions/ADR-NNN-*.md` (on demand) |
| Validation | `/quality:test-planner` | `plan.md` | `implementation/validation.md` |
| Implementation | `/code:implement` | `plan.md` + `validation.md` | code |
| QA | `/quality:does-it-work` | implementation | sign-off |
| Knowledge | `/knowledge:process-journal-zettels` | journal entries | `logseq/pages/*.md` |
| Meta | `/meta:context-audit` (planned) | `~/.claude/**` | audit report |
