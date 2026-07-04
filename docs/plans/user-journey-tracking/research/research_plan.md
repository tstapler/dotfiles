# Research Plan: Declarative User Journey Tracking → Claude Skill

## Decision this research informs
How should a Claude Skill declaratively define, track, test-map, and iteratively
improve user journeys across the user's apps — using markdown or another
lightweight declarative format — so journeys stay documented, testable, and
enriched over time?

## Local prior art already found (do not re-research, cite as-is)
- `.claude/skills/ux-journey-mapper/SKILL.md` — parallel-agent journey *discovery*
  from an existing app's code (story map + UX flow + Mermaid). Produces
  `docs/ux/journey-map.md`. Does NOT define a declarative spec format or link to
  automated tests — it's a one-shot mapping/documentation generator, not a
  tracking/testing system.
- `.claude/skills/ui-playwright/.../playwright-test-planner.agent.md` — Playwright's
  own built-in agent that explores an app via browser tools and saves a markdown
  test plan (`planner_save_plan`) with numbered steps + expected outcomes. This is
  the closest existing "declarative markdown journey → test" bridge.
- `.claude/skills/quality/skills/test-planner/SKILL.md` — maps code changes to test
  coverage, not journeys specifically.
- `.claude/skills/docs/skills/write/SKILL.md` — general docs-writing conventions
  (Diataxis-based), relevant for output formatting conventions only.

## Subtopics

### 1. Declarative journey/flow specification formats (external landscape)
**Search strategy**: web search for BDD/Gherkin ecosystem, markdown-native BDD
(Gauge), statechart-based flow specs (XState), Storybook CSF + interaction
testing, "living documentation," user story mapping, journey-mapping notations.
**Cap**: 5 searches.
**Axes for trade-off matrix**: human-readability, machine-parseability,
diagram/visualization support, ecosystem maturity, coupling to a specific test
runner, suitability for markdown-first authoring.

### 2. Testing & traceability tooling (spec → automated test → coverage)
**Search strategy**: web search for requirements traceability matrices, BDD
living-documentation tools (Serenity BDD/Thucydides), Cucumber Studio, Gauge
execution reports, Playwright test.step()/agent test-plan format, consumer-driven
contract testing analogs, journey coverage dashboards.
**Cap**: 5 searches.
**Axes**: traceability granularity (spec line → test → run result), report/dashboard
output, staleness detection (spec drift from code), CI integration effort.

### 3. Claude Skill authoring patterns for self-maintaining journey docs
**Search strategy**: primarily local synthesis (prior art above) + light web search
on Anthropic Agent Skills best practices and any public examples of
skills/agents that maintain living documentation or BDD specs.
**Cap**: 3 searches.
**Axes**: context efficiency (lean-agent-loop pattern), staleness/drift detection,
extraction vs. authoring workflow, integration with existing skills
(`ux-journey-mapper`, `quality:test-planner`, `docs:write`, `ui-playwright`).

## Synthesis output
`docs/plans/user-journey-tracking/research/synthesis.md` → feeds a follow-up
`/skill:create` invocation to build the actual Claude Skill.
