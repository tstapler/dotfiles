# Research Synthesis: Declarative User Journey Tracking → Claude Skill

## Decision Required
What declarative spec format, testing-linkage mechanism, and Claude Skill architecture should be used to define, track, test-link, and iteratively improve user journeys across the user's apps.

## Context
The user wants every user journey in their apps documented in a lightweight, ideally markdown-based declarative format, kept linked to automated tests so journeys stay verifiably implemented (not just described), and maintained over time by a Claude Skill that can extract journeys from code, check they're still accurate, and enrich them as the app evolves. This repo already has a one-shot journey-*discovery* skill (`ux-journey-mapper`) and adjacent test-planning/docs skills, but nothing that persists a spec, links it to tests, or detects drift — that's the gap this research fills.

## Options Considered

| Option | Summary | Key Trade-off |
|--------|---------|---------------|
| Gherkin/BDD (Cucumber, Reqnroll, behave) | Given/When/Then DSL in `.feature` files, mature CI/living-doc tooling | High test-linkage rigor, but not markdown and not GitHub-rendered |
| Gauge (ThoughtWorks) | Specs are literally `.md` files, steps bound via "concepts" | Best markdown-native fit, but small ecosystem, own test runner |
| XState/statecharts | Journeys as executable state-machine config, auto-visualized | Diagram never drifts from logic, but requires an architectural commitment far beyond documentation |
| Mermaid-in-markdown | `journey`/`flowchart` diagrams embedded in `.md`, native GitHub rendering | Zero-cost, highest readability, but purely visual — no execution semantics, no drift enforcement |
| Playwright Planner/Generator/Healer agents | Already installed locally; explores live app → saves markdown plan → generates executable TS → self-heals broken tests | Lowest-friction path to markdown→test execution, but Healer silently patches code without updating the markdown spec |
| Pact/Pactflow (contract-testing analog, not directly adoptable) | Contracts generated from real interactions, broker actively tracks verification recency, "Drift" feature proactively re-verifies | Best-in-class proactive staleness detection *pattern* — no UI-testing equivalent tool exists, so only the pattern transfers |
| Single monolithic "journey" Claude Skill | One skill handling extract + verify + enrich | Simple to invoke, but mixes incompatible freedom-levels (open exploration vs. deterministic checks vs. gated authoring) in one file |
| Three-skill family (extract / verify / enrich) | Mirrors this repo's existing `ux-journey-mapper` → `quality:test-planner` → `docs:write` chain; each skill's freedom level matches its task | More moving pieces, but composable, independently schedulable, and matches Anthropic's own degrees-of-freedom guidance |

## Dominant Trade-off
**Authoring ease / non-engineer readability vs. machine-enforceable rigor.** Every format that renders beautifully in a PR and invites a PM or designer to edit it directly (plain markdown, Mermaid diagrams) has weak or no built-in mechanism to fail CI when it silently drifts from reality. Every format with strong test-linkage and drift-enforcement (Gherkin+Serenity, Pact/Pactflow) is either not markdown-native or has no equivalent in UI/journey testing. All three research threads converge on the same resolution: **don't pick one tool — build a thin markdown+frontmatter hybrid that borrows the readability of Gauge/Mermaid and the traceability discipline of Gherkin/Pact**, then use a Claude Skill (not a static tool) as the active agent that keeps the two in sync over time, since nothing in the existing ecosystem does that maintenance step for you.

## Recommendation

**Choose**: A markdown-first, YAML-frontmatter journey spec format, executed/verified via Playwright's existing Planner/Generator agents, maintained by a **three-skill Claude Skill family** (extract → verify → enrich).

**Because**:
1. **Format** — plain markdown body (Gauge-style: heading = journey, list items = steps) for human/non-engineer readability and native GitHub/GitLab rendering, plus YAML frontmatter carrying machine-parseable fields (`journey_id`, linked `test_id`(s), `last_verified`, ticket/requirement refs) borrowed from Gherkin/Cucumber-Studio-style tagging, plus an embedded Mermaid `journey` or `flowchart` diagram for visual review. No single surveyed format (Gherkin, Gauge, XState, Storybook CSF, story mapping, Robot Framework) natively satisfies markdown-first authoring + machine-parseability + diagram support + test-linkage simultaneously — this hybrid captures the union at low cost since it's just markdown+YAML, nothing new to install.
2. **Test linkage** — build on Playwright's Planner/Generator agents, already installed and confirmed present in this repo (`.claude/skills/ui-playwright`), rather than adopting Gauge or Serenity BDD as a second test-runner ecosystem. This is the lowest-friction path to "markdown journey → executable test" available today.
3. **Drift/staleness** — explicitly patch Playwright's proven weak point (Healer repairs test code without updating the markdown plan) by requiring `test.step()` names to verbatim-mirror the journey markdown's step titles (cheap, enforceable, gives free nested-report traceability) and by borrowing Pact/Pactflow's *pattern* (not tool) of active, scheduled re-verification instead of one-shot generate-and-forget.
4. **Skill architecture** — a three-skill family (`journeys-extract`, `journeys-verify`, `journeys-enrich`) rather than one monolithic skill, because the three phases have genuinely different re-run cadences (extract: rare/on-demand; verify: every CI run/pre-commit, should be largely a deterministic script per Anthropic's guidance; enrich: periodic, gated by human approval to avoid clobbering hand-edited content) and different freedom levels. This mirrors the informal chain this repo already has (`ux-journey-mapper` discovery → `quality:test-planner` coverage-mapping → `docs:write` gated authoring) and directly follows Anthropic's own high/medium/low degrees-of-freedom framework for skill design.

**Accept these costs**: Building this hybrid format and the verify skill's deterministic script is genuinely new work — nothing off-the-shelf does it. The three-skill split is more moving pieces than a single command. `test.step()`-name discipline must be enforced by convention/lint, not by any existing tool.

**Reject these alternatives**:
- **Full Gherkin/Cucumber or Robot Framework as the primary spec format**: rejected because neither is markdown-native (own DSL/tabular syntax), losing the non-engineer-readability goal that's core to this project.
- **XState as the primary spec format**: rejected because it requires modeling the app's actual control flow as a state machine — an architectural commitment disproportionate to "declarative journey documentation," not just a docs choice.
- **Adopting Gauge or Serenity BDD as a new test-runner**: rejected because this repo (via `ui-playwright`) already has Playwright installed with a markdown-plan-generating agent built in; introducing a second test-runner ecosystem duplicates infrastructure for marginal format-purity gains.
- **Single monolithic journey-tracking skill**: rejected because it forces incompatible freedom-levels (high-freedom exploration, low-freedom deterministic checks, medium-freedom gated authoring) into one instruction set, and doesn't compose with skills this repo already has.
- **Adopting Pact/Pactflow directly**: rejected because there's no UI-testing "provider" equivalent to verify against — only the *pattern* (active scheduled re-verification, broker-style recency tracking) transfers, not the tool itself.

## Open Questions Before Committing
- [ ] What identity/slug scheme will journey frontmatter use, and does it support stable upsert on re-extraction (so re-running `journeys-extract` doesn't duplicate journeys)? — blocks the extract skill's idempotency design.
- [ ] Should `journeys-verify` be a bundled deterministic script (test-ID/file-existence cross-reference) with an LLM escalation only for semantic drift, or full LLM judgment every run? — affects whether it's cheap enough to run on every PR.
- [ ] Can Playwright's Healer (or a thin wrapper) be made to emit a diff against the original markdown plan so code-level drift becomes visible instead of silent? No existing feature does this — needs a build-vs-skip decision.
- [ ] Where should the three skills live in this repo's taxonomy (new `journeys` group parallel to `ux`, `quality`, `docs`)?

A spike/prototype on the Playwright Planner→markdown→Generator round-trip (with `test.step()` name mirroring) is recommended before finalizing the skill's SKILL.md files, since the verify skill's whole design depends on how cleanly that mirroring holds up in practice.

## Sources
- `docs/plans/user-journey-tracking/research/findings-declarative-formats.md`
- `docs/plans/user-journey-tracking/research/findings-testing-traceability.md`
- `docs/plans/user-journey-tracking/research/findings-skill-design.md`
