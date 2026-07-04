# Findings: Testing & Traceability — Keeping Declarative Journey Specs Linked to Automated Tests

## Summary

Once a journey is written declaratively, three different linking strategies show up across the ecosystem, trading granularity against authoring cost:

1. **Annotation-embedded traceability** (Serenity BDD/Thucydides, Cucumber + tags) — the spec file itself *is* the source of truth; a runner executes it directly (Gherkin steps map 1:1 to step-definition code) or annotates code with references back to the spec (`@Story`, `@Issue`, JIRA tags). Traceability is automatic because there's one artifact, not two kept in sync.
2. **Generated-artifact traceability** (Playwright's Planner/Generator/Healer agents) — a markdown plan is produced by exploring the live app, then a *separate* generation step turns it into executable TypeScript. The link between markdown and code is implicit (same repo, same PR) unless a team adds explicit back-references — the weakest-traceability option of the three but lowest authoring cost.
3. **External contract/matrix traceability** (RTM tools, Pact broker) — spec and test live in the app repo, but a third system independently records which requirement/consumer-expectation maps to which verified test run, decoupling "is this still true" from the app's own CI output.

No tool solves *staleness detection* well by default — every tool either (a) fails loudly when the automated test breaks (Gherkin/Serenity: step definitions throw or assert-fail) or (b) requires an explicit re-verification workflow (Pact: provider verification must be re-run; Playwright Planner: plan must be manually/agent re-explored). None detect "the human/business meaning of the spec has silently drifted from what the UI actually does" without re-running against a live app or a human re-reading the diff — this is the fundamental gap this project's Claude Skill should target.

## Options Surveyed

**1. Requirements Traceability Matrices (RTM) — general tooling & practice.** An RTM maps requirement → test case → execution result, traditionally a spreadsheet, now increasingly a live dashboard. Modern tools (Parasoft DTP, SpiraTeam, TestRail, Kualitee, Xray for Jira, qTest) auto-populate the matrix by ingesting CI results (JUnit XML / Cucumber JSON) joined against requirement IDs in test names, tags, or a linked tracker. RTM is a downstream reporting layer any declarative spec can feed as long as tests are tagged with a stable requirement/journey ID. [thectoclub.com RTM tools 2026, Parasoft blog, testomat.io RTM guide]

**2. Serenity BDD / Thucydides — living documentation + traceability.** The most mature "living documentation" tool here. Requirements organize as a directory hierarchy (folders = higher-level requirements, feature files = leaf requirements) or integrate with JIRA. Execution produces an aggregate report showing not just pass/fail but **what requirement was tested and how** — step-by-step narrative via the Screenplay pattern. Closest existing analog to "spec stays verified as app evolves": the report regenerates every CI run, so drift surfaces as a broken/pending step, not silent staleness. [serenity-bdd.github.io/docs/reporting/living_documentation]

**3. Cucumber Studio & Gauge reports.** Cucumber Studio (SmartBear, formerly HipTest) hosts Gherkin centrally, letting non-technical stakeholders edit scenarios, syncing to feature files executed by CI (Cucumber-JVM/JS), with its own execution-status dashboard. Gauge (ThoughtWorks) generates a self-contained HTML report per run preserving markdown rendering — the HTML report *is* the living documentation, regenerated each run from the same markdown that is the spec, no separate "studio" needed. `[TRAINING_ONLY — verify]` — search did not surface current Gauge/Cucumber Studio docs directly (the combined query returned mostly Playwright+Cucumber+Allure results); above reflects prior product knowledge, flagged for re-verification.

**4. Playwright test.step() nested reporting + Trace Viewer.** `test.step()` wraps a block of actions with a name; the HTML reporter renders these as a collapsible nested tree per test, giving coarse spec-line → report-line traceability if step names mirror the declarative journey doc verbatim. Trace Viewer is a separate `.zip` artifact capturing DOM snapshots, network, console, and action timeline, attachable to any CI-failed run for full replay. [playwright.dev/docs/trace-viewer] `[TRAINING_ONLY — verify]` on 2026-specific UI details.

**5. Playwright Agents: Planner → Generator → Healer.** Confirmed live, and already present locally at `/home/tstapler/dotfiles/.claude/skills/playwright-test-planner.md` (mirrors `node_modules/playwright/lib/agents/playwright-test-planner.agent.md`, shipped since Playwright v1.56 — also found cached at v1.57.0 and v1.58.0 under `~/.cache/yarn/`, `~/.npm/_npx/`, and several project `node_modules/`). Pipeline:
- **Planner**: calls `planner_setup_page` once, explores via `browser_*` MCP tools, calls `planner_save_plan` to write markdown (conventionally under `specs/`) with numbered steps, expected outcomes, explicit "assume blank/fresh state" per scenario. Structurally close to what this project wants as a "declarative journey spec."
- **Generator**: consumes the saved markdown and produces executable Playwright TypeScript. The markdown→test link is created here but is a **one-time code-generation event** — not a live binding. Once generated, the files are independent; nothing re-syncs them if the app UI changes.
- **Healer**: re-runs failing generated tests and auto-repairs broken selectors/assertions, but only repairs the *generated code* — it never updates the markdown plan. After a Healer pass, the markdown spec can silently drift from what the test code now actually verifies. This is a concrete, named staleness failure mode: any auto-healing pipeline needs to also re-emit an updated markdown spec, or traceability silently breaks.
[github.com/microsoft/playwright playwright-test-planner.agent.md, playwright.dev/docs/test-agents, dev.to "Playwright Agents: Planner, Generator, and Healer in Action", testdino.com/blog/playwright-test-agents, browserstack.com/guide/playwright-agent, shipyard.build/blog/playwright-test-planner-agent]

**6. Consumer-Driven Contract Testing (Pact) as an analog pattern.** Pact's model: the consumer writes an expectation against a mock provider; this produces a generated JSON contract (not hand-authored) published to a **Pact Broker**, the analog of a traceability dashboard — it visualizes which consumer-provider pairs are verified against which versions ("can-i-deploy"), flagging contracts never verified against a real provider (analog to "spec exists but drifted"). Pactflow's "Drift" feature enforces a provider's OpenAPI spec against real running behavior, explicitly targeting the staleness problem — Pactflow's blog frames this as urgent because AI-generated code accelerates spec/implementation divergence with no human noticing. Transferable lesson: **contracts are generated from real interactions, not hand-maintained**, and a broker actively tracks verification recency rather than trusting a static document. Documented cost: "Pact's Dependency Drag" — CDC can block parallel development since a consumer can't safely proceed until a provider verifies the contract. [pactflow.io/blog/schemas-can-be-contracts, docs.pact.io, baeldung.com Pact JUnit CDC, blog.risingstack.com CDC with Pact, pactflow.io/what-is-consumer-driven-contract-testing, specmatic.io "Pact's Dependency Drag", docs.pact.io/implementation_guides/javascript, sqaexperts.com Pact 2026 guide]

**7. Coverage dashboards / journey-coverage visualization.** No single dominant tool for *journey-level* (multi-step, end-to-end) coverage emerged distinctly from feature-level coverage tooling. What exists: (a) RTM-style dashboards generalizable to journeys if each journey is modeled as a "requirement"; (b) Serenity's requirements tree, naturally suited to nested journeys; (c) Gauge's/Playwright's native HTML reports, which show spec/scenario pass-fail but don't aggregate "journey completion %" by default. Gap: no surveyed tool gives an out-of-the-box journey-coverage dashboard equivalent to code-coverage tooling — it would need custom rollup from tagged scenario results.

**8. Spec-drift / staleness detection.** Staleness detection is **reactive, not proactive** everywhere surveyed:
- Gherkin/Serenity/Gauge: drift surfaces only when the test *runs* and fails. A "pending"/"skipped" test for a removed feature can persist indefinitely without failing.
- Playwright Planner/Generator/Healer: drift surfaces when Healer's repair diverges from the original markdown plan, or when Generator isn't re-run after a Planner re-explore — nothing forces markdown and generated code to regenerate together.
- Pact/Pactflow Drift: the only tool surveyed explicitly marketed as solving spec staleness proactively — verifies real provider behavior continuously, not just at consumer-test time.
- General RTM practice: matrices are "live" only if CI results are auto-ingested; manually-maintained spreadsheets are called out as an explicit anti-pattern ("Requirements Traceability Matrix: Why Excel Isn't Enough in 2026" — Kualitee).

## Trade-off Matrix

| Approach | Traceability granularity (spec line → test → run result) | Report/dashboard output quality | Staleness/drift detection capability | CI integration effort |
|---|---|---|---|---|
| Serenity BDD / Thucydides | High — Gherkin step ↔ step-definition ↔ requirement tree, narrated per-step | High — purpose-built living-documentation site, regenerated every run | Medium — reactive only (broken step fails build); no idle/passive drift detection | Medium — Serenity runner + JUnit/Cucumber integration, JIRA plugin optional |
| Gauge (markdown-native) | High — markdown steps are literally the executable spec (no spec-text drift, only implementation drift) | High — self-contained HTML report per run, preserves markdown formatting | Medium — same reactive model; step implementation can still diverge from markdown intent | Low-Medium — first-class CLI/CI plugins, markdown is source of truth |
| Cucumber Studio + Cucumber runner | Medium-High — bidirectional sync between hosted scenarios and repo, execution status in Studio UI | Medium-High — dedicated dashboard but a second system to keep synced | Low-Medium — sync lag between Studio and repo is itself a drift vector `[TRAINING_ONLY — verify]` | Medium — commercial product, needs sync tooling/API keys |
| Playwright test.step() + Trace Viewer | Medium — step names nest in report but no structural link to a markdown journey doc unless kept in sync manually | High — best-in-class visual replay/debugging (DOM, network, console, timeline) | Low — purely a debugging/reporting tool, no spec-tracking mechanism | Low — native to Playwright, zero config for nesting, trace capture is a flag |
| Playwright Planner/Generator/Healer | Low-Medium — markdown and generated code linked only by generation-time provenance; Healer fixes code without updating markdown | Medium — plan itself is readable; no aggregate dashboard across many plans | Very Low — reactive only through Healer (fixes code, not spec); no detection that spec text is now wrong | Low — built into Playwright CLI/MCP; plan regeneration is manual/agent-triggered, not CI-automated |
| RTM tools (TestRail/Xray/SpiraTeam/Parasoft DTP) | High if tags/IDs disciplined; low otherwise | High — purpose-built dashboards, trend charts, executive views | Medium — live if CI-fed automatically; ~zero if manually maintained | Medium-High — usually paid, requires CI ingestion + ID-tagging convention |
| Pact / Pactflow (contract-testing analog) | High for its narrow slice (API shape) — contract generated from real interaction | High — Pact Broker "can-i-deploy" matrix, verification history per version | High — Pactflow Drift is the only tool surveyed built specifically for proactive drift detection | Medium-High — requires broker service, provider-verification CI step, versioning discipline, cross-team coupling |

## Risk and Failure Modes

- **Silent test-code drift from markdown intent**: Playwright's Generator→Healer flow can auto-repair a selector/assertion, changing what the test verifies, while the markdown plan is never touched — the most relevant risk to this project's markdown-first journey format.
- **Tag/ID discipline decay**: RTM traceability depends entirely on consistent requirement/journey ID tagging; renames or copy-pastes silently orphan history.
- **Zombie specs**: A skipped/pending scenario for a removed feature can persist indefinitely without failing CI.
- **Dashboard fragmentation**: Teams running Cucumber Studio + Serenity + a separate RTM tool end up with three non-reconciling sources of truth.
- **Cross-team coupling cost (Pact)**: "Dependency Drag" — CDC can block parallel development, a cost worth weighing if this pattern is borrowed.
- **AI-acceleration risk**: Pactflow explicitly flags AI-generated specs/code as accelerating drift since no human naturally notices divergence during authoring — directly relevant since the eventual Claude Skill will itself be AI-authoring/maintaining journey specs and needs a built-in re-verification step.

## Migration and Adoption Cost

- **Serenity BDD**: Medium-high — JVM-centric, Screenplay pattern; poor fit for a JS/TS or polyglot markdown-first workflow.
- **Gauge**: Low-medium — markdown is already the native spec format, conceptually closest fit, but introduces a whole new test-runner ecosystem rather than layering onto existing Playwright/Jest.
- **Cucumber Studio**: Medium — commercial SaaS, needs non-engineering buy-in to justify sync overhead.
- **Playwright test.step() + Trace Viewer**: Very low — already available in any Playwright install, zero new infrastructure.
- **Playwright Agents (Planner/Generator/Healer)**: Low — ships with Playwright ≥1.56, confirmed present locally (multiple cached versions found), usable today via MCP tool calls. Lowest-friction path to prototype the "markdown journey → executable test" bridge.
- **RTM tooling**: Medium-high — typically paid, requires ID-tagging retrofit and ongoing dashboard maintenance.
- **Pact/Pactflow**: High — requires a broker, provider-verification CI wiring, cross-team process change; best treated as a *pattern to borrow*, not a *tool to adopt*, since there's no "UI provider" equivalent to verify against.

## Operational Concerns

- **CI wiring**: Serenity/Gauge/Cucumber report generation must run even on failure (non-`continue-on-error`) or living-documentation output silently stops updating.
- **Report hosting**: HTML output needs a publishing step (GitHub Pages, artifact upload, S3) to be a persistent "current state" view rather than a transient CI artifact.
- **Trace storage cost**: Playwright traces are heavyweight (DOM snapshots + network + video); retaining them for every run (not just failures) has real storage/cost implications.
- **Agent-triggered plan regeneration**: No cheap way to "diff" whether a re-explored Playwright plan meaningfully differs from the last saved one without a human/LLM semantic-review step — a design problem the eventual Claude Skill needs to solve directly.
- **Cross-tool identity**: Any traceability scheme spanning journey-spec → test → dashboard needs one stable ID system (journey slug, requirement key) referenced consistently across markdown front-matter, test tags, and CI result parsing.

## Prior Art and Lessons Learned

- Serenity BDD's core insight — report around requirements/journeys tested, not just test files run — is the right mental model for the eventual Claude Skill's output.
- Gauge's choice to make markdown *directly executable* removes an entire class of drift (spec text and step-definition text can't diverge because they're the same artifact) — worth considering for the journey format's design goal.
- Playwright's Planner/Generator/Healer split is a workable three-phase pipeline (explore → author spec → generate tests → self-heal) mapping closely onto this project's goal, but its explicit weak point (Healer fixes code without updating spec) is a concrete anti-pattern to avoid by design.
- Pact/Pactflow's "Drift" framing (AI now authors both spec and implementation, so nobody notices divergence) is directly relevant — this project should assume its own AI-authored journey specs need an active re-verification loop, not one-time generation.
- The "RTM as Excel is dead" critique reinforces that any traceability layer for journeys must be CI-fed/automated, or it will be stale on day one.

## Open Questions

- Does Gauge's markdown-is-the-spec model transfer well to a JS/TS/Playwright-centric stack, or would it be a redundant second test runner? Not resolved this pass — flagged `[TRAINING_ONLY — verify]`.
- What does Cucumber Studio's actual sync mechanism look like today (webhook-based? one-way import/export)? Not confirmed via search this session.
- Can Playwright's Healer (or a wrapper) be made to emit a diff against the original markdown plan so drift becomes visible rather than silent? No existing feature/plugin found for this — appears to be a genuine build-it-yourself requirement.
- Are there existing open-source "journey coverage" dashboards rolling up tagged BDD scenario results into per-journey completion percentages? Not found this pass — flagged as a genuine gap.
- How would a Pact-Broker-style "can-i-deploy" gate look for UI journeys specifically (journey spec verified against current build within N days, or CI blocks merge)? Promising pattern, no direct UI-testing analog found.

## Recommendation

Prototype directly on **Playwright's built-in Planner/Generator agents** (already installed locally, zero new infrastructure) as the execution/traceability backbone, but explicitly patch its weakest point — Healer silently diverging from markdown — by designing the Claude Skill to: (a) keep the markdown journey doc as the single hand-edited source of truth with stable per-scenario IDs/front-matter, (b) require `test.step()` names to mirror the markdown's step titles verbatim (cheap, enforceable, gives free nested-report traceability), and (c) borrow Pact/Pactflow's core pattern — not the tool — of active, periodic re-verification (re-run Planner exploration on a schedule or pre-merge, semantically diff the new plan against the last-saved one) rather than Playwright's default one-shot generate-and-forget model. This gets Gauge/Serenity-level traceability discipline without adopting a second test runner, and directly targets the staleness-detection gap no single surveyed tool solves out of the box.

## Pending Web Searches

None — all 5 allotted searches were used (Playwright agent/planner, Serenity BDD, Pact/contract-drift, RTM/dashboard tooling, Gauge/Cucumber Studio/trace viewer). Two follow-ups flagged as valuable with more budget:
- "Gauge markdown spec Playwright integration 2026"
- "Cucumber Studio sync API webhook feature files 2026"
