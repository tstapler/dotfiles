# Findings: Declarative Formats/Tools for Specifying User Journeys and Flows

## Summary

There is no single dominant standard for "declarative, markdown-friendly user journey specs linked to tests" — the landscape splits into four lineages that solve overlapping but distinct problems:

1. **BDD/Gherkin family** (Cucumber, SpecFlow/Reqnroll, behave) — the most mature "living documentation" approach, but Gherkin is its own DSL wrapped in `.feature` files, not markdown itself.
2. **Gauge (ThoughtWorks)** — the only mainstream framework where specs are *literally* `.md` files with no separate DSL; markdown headings/lists double as the spec syntax, with step implementations bound via "concept" files. Reported usage growth per industry blog coverage [TRAINING_ONLY — verify magnitude], though it remains a niche player compared to Cucumber.
3. **State-machine/statechart family** (XState/Stately) — flows expressed as declarative JSON/JS config, not prose; strongest for *visualizing and formally verifying* transition logic, weakest for human prose readability without tooling.
4. **Component/story-level flow specs** (Storybook CSF + play functions) — flows expressed as executable JS "stories," good for granular UI interaction testing, not journey-level documentation.

Orthogonal to all of these: **Mermaid/PlantUML diagrams embedded directly in markdown** are the lowest-friction way to get a visual, versionable, diffable flow representation inside a plain `.md` file — but they are diagrams, not specs; nothing parses them back into executable test assertions without custom tooling. **Jeff Patton's user story mapping** is a physical/visual practice more than a file format — its digital "documentation format" incarnations (Markdown/YAML story maps, tools like StoriesOnBoard, Cardboard, avion.io) are not standardized and mostly proprietary/tool-locked.

No format surveyed natively combines: (a) markdown-native authoring, (b) machine-parseable structure, (c) built-in diagram rendering, and (d) direct linkage to automated test execution. Gauge comes closest on (a)+(d); Mermaid-in-markdown comes closest on (a)+(c); Gherkin comes closest on (b)+(d) at the cost of (a).

## Options Surveyed

### Gherkin / BDD (Cucumber, SpecFlow → Reqnroll, behave)
Given/When/Then plain-text DSL stored in `.feature` files, parsed by a Gherkin parser, bound to step-definition code (Java/Ruby/JS for Cucumber, C# for Reqnroll, Python for behave). Positioned as "living documentation": because the same text drives both human comprehension and test execution, docs can't silently drift from behavior — assuming the suite runs in CI and features aren't stale/skipped. **2025 ecosystem note**: SpecFlow (dominant .NET Gherkin tool) reached end-of-life in December 2024; **Reqnroll** is its actively maintained community fork with a compatibility package for migration — a live signal that single-vendor BDD tools carry maintenance risk even when the underlying format (Gherkin) persists. Gherkin is *not* markdown — `.feature` files use their own keyword syntax. It can be embedded in markdown code fences for documentation, but isn't natively an `.md` artifact. Strongest for step reuse and rich tooling (IDE plugins, CI reporters, Cucumber Studio for living-doc dashboards).

### Gauge (ThoughtWorks)
Specs are literally `.md` files: markdown H1 = specification title, H2 = scenario, list items = steps. No separate DSL beyond markdown itself. Steps bind to implementation code via a "concept" abstraction, decoupling spec prose from step glue code more cleanly than Cucumber's regex/annotation binding in some cases. Supports Java, C#, JavaScript/Node, Python, Ruby runners; integrates with Selenium/Taiku. Rich plugin architecture (HTML reports, IntelliJ/VSCode plugins, parallel execution, data-driven markdown tables). Because it's markdown, specs render natively and readably on GitHub/GitLab — a meaningful advantage over Gherkin `.feature` files, which GitHub does not syntax-highlight or render specially. Smaller community/ecosystem than Cucumber; fewer Stack Overflow answers, fewer third-party integrations [TRAINING_ONLY — verify current maintenance cadence].

### XState / Statecharts (Stately.ai)
Flows/UI states expressed as declarative JS/TS objects (or JSON) describing states, events, transitions, guards, and actions — based on David Harel's statechart formalism. Not markdown or prose-based; it's executable application logic, though the config is declarative and can be auto-visualized. Stately Studio / XState Visualizer renders the machine as an interactive flow diagram from the JSON config, with round-tripping between visual editor and code — a rare instance of diagram-as-source-of-truth staying in sync with execution. Because the machine literally *is* the app's runtime flow logic (when used to drive UI state), "documentation drift" is structurally prevented for the parts of the journey it governs — but this only covers app state transitions, not broader user/business journey narrative (e.g., "user receives email, clicks link 3 days later"). Steep adoption cost: requires modeling the app's control flow as a state machine — a real architectural commitment, not just a documentation exercise. `@xstate/test` (path-coverage-based model testing) can generate test paths from the machine definition — closest thing in this survey to "spec defines the test cases automatically" [TRAINING_ONLY — verify current package name/status in XState v5].

### Storybook CSF + Interaction Testing (play functions)
Component Story Format (CSF) stories are JS/TS modules; `play` functions attached to a story run after render and simulate user interaction (click, type, submit) using Testing Library-style queries, then assert outcomes. This is a *component-level* flow spec, not an app-level or multi-page journey spec. Visualized via the Storybook Interactions addon panel (step-through UI, pause/resume/rewind) and executed at scale via `@storybook/test-runner` (Jest + Playwright under the hood). Not markdown — pure code (Storybook autodocs generate MDX-like pages from stories, but the source of truth is TS/JS). Good complementary layer for "leaf" interactions inside a larger journey, but not a fit for the cross-page/cross-session journey narrative this project cares about.

### User Story Mapping (Jeff Patton)
Originally and still primarily a *physical/whiteboard practice*: user activities across the top (backbone), user tasks below, releases/priorities as horizontal slices going down. As a "documentation format" it has no standardized text/markdown representation. Digital tools (StoriesOnBoard, Cardboard, Avion, Miro/FigJam templates, some Jira plugins) each use proprietary JSON/DB schemas, not an open text format. Ad hoc markdown/YAML encodings exist informally (nested bullets: activity → task → story), but these are project-specific conventions, not an ecosystem-wide standard the way Gherkin or CSF are. Story maps describe the *product's* scope/priority structure more than a *specific user's runtime path* through a shipped app — useful for backlog/roadmap framing but not directly for "this is the flow, verify it still works." Better understood as a complementary planning artifact than a candidate spec format for this project.

### Mermaid / PlantUML Diagrams Embedded in Markdown
`flowchart`, `stateDiagram-v2`, and `journey` diagram types in Mermaid embed directly in a fenced ` ```mermaid ` code block inside a `.md` file; GitHub, GitLab, and most modern markdown renderers (Obsidian, Logseq, VS Code) render these natively without plugins. Mermaid has a dedicated `journey` diagram type purpose-built for user journeys (actors, tasks, satisfaction scores per step) — the most directly on-topic primitive found in this survey, though it's visualization-only (no execution semantics, no assertions). PlantUML is more powerful/verbose (full UML state/activity/sequence diagrams) but requires a rendering server or local Java+Graphviz; worse out-of-the-box GitHub rendering than Mermaid. Neither is machine-parseable for "extract structured steps and generate/validate tests" without custom parsing; some community scripts parse Mermaid state diagrams to scaffold XState machines or vice versa, but these aren't first-party features [TRAINING_ONLY — verify specific projects/maintenance status]. Best characterized as the "docs and communication" layer, not the "spec that drives tests" layer, unless paired with custom tooling.

### Robot Framework (plain-text keyword-driven format)
Uses a plain-text/pipe-or-space-delimited tabular syntax (not Markdown, though it also supports reStructuredText). Test cases are keyword sequences (higher-level, human-readable actions built from lower-level keywords/libraries) — conceptually similar to Gherkin's step reuse but with its own file format (`.robot`) and syntax rules. Strong "living documentation" story via `libdoc`/`testdoc` auto-generated HTML docs from the same source files that execute as tests. Mature, widely used in enterprise/QA-heavy orgs and hardware/embedded testing; large keyword library ecosystem (SeleniumLibrary, Browser Library/Playwright-based, RequestsLibrary). Not markdown-native and doesn't render nicely on GitHub by default; the tabular syntax has its own learning curve, arguably steeper than Gherkin for newcomers.

### Other markdown-first/YAML-adjacent formats worth flagging
- **Cucumber Studio / "living documentation" dashboards** — SaaS layer on top of Gherkin scenarios providing traceability between specs, test runs, and requirements; relevant prior art for the "keep docs in sync + link to tests" goal.
- **OpenAPI/AsyncAPI-style YAML specs** — not journey formats, but demonstrate a pattern worth borrowing: YAML/JSON schema-validated spec files that both humans read and tooling (codegen, test generation e.g. Schemathesis, Dredd) consume directly [TRAINING_ONLY — verify no existing "journey schema" standard already fills this gap].
- **Playwright/Cypress "test as documentation"** (`test.step()` naming, Cypress Cucumber preprocessor) — teams write structured `test.step()` blocks with human-readable names that HTML/trace reporters render as a step-by-step narrative — a "spec emerges from tests" alternative to "tests emerge from spec."
- No evidence found of a markdown-frontmatter-based journey-spec standard already established in the wider ecosystem — appears to be a genuine gap rather than something this project would duplicate.

## Trade-off Matrix

| Format/Tool | Human-readability | Machine-parseability | Diagram/viz support | Ecosystem maturity | Coupling to specific test runner | Markdown-first authoring fit |
|---|---|---|---|---|---|---|
| Gherkin (Cucumber) | High (prose-like) | High (formal grammar, many parsers) | Low natively (3rd-party like Cucumber Studio adds it) | Very high | Medium (Cucumber-family runners, format itself runner-agnostic) | Low (own DSL, not `.md`) |
| SpecFlow → Reqnroll | High | High (same Gherkin grammar) | Low natively | Medium-high, but in flux post-EOL migration [TRAINING_ONLY — verify] | High (.NET/NUnit/xUnit specific) | Low |
| behave (Python) | High | High | Low | Medium (solid, smaller than Cucumber-JVM) | High (Python-specific) | Low |
| Gauge | High (it's literally markdown) | Medium (structure parseable, less formal than Gherkin grammar) | Low natively | Low-medium (niche vs. Cucumber) | Medium (Gauge's own multi-language runners) | Very high |
| XState/Statecharts | Low-medium for non-devs; high once visualized | Very high (it IS structured data) | Very high (purpose-built visualizer, bidirectional editing) | High within frontend/state-mgmt niche, low outside | Low-medium (`@xstate/test` optional; framework-agnostic core) | Low (needs embedding/export) |
| Storybook CSF + play functions | Low for non-devs (TS/JS code) | High (structured, introspectable) | Medium (Interactions panel, not a journey diagram) | High within frontend component-testing niche | High (Storybook + test-runner/Playwright/Jest) | Low |
| User Story Mapping (Patton) | Very high as workshop artifact; medium as text | Low (no standard text format) | High as practice, tool-dependent digitally | Medium (well-known practice, fragmented tooling) | N/A (not a test format) | Low-medium (informal only) |
| Mermaid in markdown | High | Low-medium (parseable grammar, not designed for test-generation round-trips) | Very high (native GitHub/GitLab rendering, dedicated `journey` type) | High | None (pure documentation) | Very high |
| PlantUML in markdown | Medium-high | Low-medium | High (very expressive UML types) | High, but weaker default markdown rendering | None | Medium (needs plugin/proxy on GitHub) |
| Robot Framework | Medium-high (readable, own tabular syntax) | High (well-defined format, libdoc introspection) | Low-medium (auto-generated HTML docs, not flow diagrams) | High (long-established, esp. QA/embedded) | High (Robot Framework-specific) | Low |

## Risk and Failure Modes

- **Spec/test drift despite "living documentation" claims**: Gherkin's promise only holds if scenarios actually run in CI and failures block merges; orgs commonly let `.feature` files rot into aspirational documentation once step definitions are stubbed/skipped.
- **DSL/tooling churn**: SpecFlow's December 2024 EOL (superseded by Reqnroll) shows vendor/maintainer risk even for a widely adopted format layer — Gherkin survived, but .NET tooling forced a migration. Weight "how many independent implementations exist" (Gherkin: many; Gauge: few) as a resilience signal.
- **Niche-tool lock-in**: Gauge's markdown-native elegance is offset by a materially smaller contributor base than Cucumber; adopting it ties the format to a less battle-tested toolchain, harder to hire/onboard for.
- **State-machine over-modeling risk**: XState requires modeling the *entire* relevant control flow as explicit states/events; partial/bolted-on adoption (just for docs, without the app running on the machine) reintroduces the same sync problem as any manually maintained doc.
- **Diagram-as-documentation without enforcement**: Mermaid/PlantUML diagrams have zero mechanism to fail CI when the described flow diverges from actual app behavior, unless custom lint/parsing tooling is built. They look authoritative while silently going stale.
- **Component-level vs. journey-level scope mismatch**: Storybook play functions test interactions within a rendered story tree, not true multi-page/multi-session flows — treating CSF as journey documentation would understate real user journeys and give false confidence.
- **Story mapping format fragmentation**: no standard text encoding means any markdown/YAML convention invented for this project will be bespoke and untested by the wider community — expect ambiguous edge cases (branching journeys, conditional steps) with no prior art to borrow.

## Migration and Adoption Cost

- **Gherkin/Cucumber family**: Low-medium if the team already writes automated E2E/integration tests. Cost rises sharply retrofitting scenarios onto a large existing suite not originally organized around BDD steps.
- **Gauge**: Low authoring cost (markdown is near-zero learning curve), but non-trivial cost in concept/step binding and accepting a smaller-ecosystem dependency; harder to migrate away from later than Cucumber given fewer interchangeable tools.
- **XState**: High cost — effectively an architectural decision to adopt statecharts for state management, not just a docs choice. Only worth it if the team will actually drive UI/flow logic through the machine.
- **Storybook CSF/play functions**: Medium cost if Storybook is already in use for the component library; high cost to introduce solely for journey documentation given its primary purpose is component-driven development.
- **Mermaid-in-markdown**: Very low cost — works today in any markdown file, zero new tooling. Cost is entirely on the "keeping it honest" side, not authoring.
- **Story mapping**: Low cost as a workshop/planning practice; unclear/variable cost to formalize as a persisted, versioned text artifact since no standard exists.
- **Robot Framework**: Medium-high if the team has no existing keyword-driven test investment; the tabular syntax and separate ecosystem make it a harder sell purely for documentation.

## Operational Concerns

- **CI integration and gating**: Gherkin-family and Robot Framework run as first-class CI test suites with mature reporters (JUnit XML, Allure, Cucumber Studio dashboards); Mermaid diagrams and story maps have no native CI-runnable form — enforcement must be custom-built.
- **Multi-language/polyglot teams**: Cucumber, Gauge (Java/C#/JS/Python/Ruby), and Robot Framework support cross-stack teams well. XState and Storybook CSF are inherently JS/TS-bound.
- **Ownership and review workflow**: Markdown-native formats (Gauge, Mermaid-in-md) win here — PR reviews render diagrams/specs directly in GitHub/GitLab diffs without plugins, lowering the bar for non-engineers (PMs, designers) to review journey changes. Gherkin `.feature` files are readable but get no special GitHub rendering.
- **Versioning and diffability**: All text-based formats (Gherkin, Gauge markdown, Mermaid, Robot Framework, YAML) diff cleanly in git. XState/Storybook diff at the code level — noisier for non-technical stakeholders.
- **Traceability to requirements/tickets**: None of the surveyed formats have first-party "link this journey step to a Jira/Linear ticket and a specific automated test ID" out of the box; Cucumber Studio and Reqnroll+SpecSync-style tools approximate this via tags (`@JIRA-123`) mapped through external sync tools — the closest existing prior art for this project's traceability needs.

## Prior Art and Lessons Learned

- BDD's "living documentation" promise is real but conditional — it only holds when scenario failures are build-breaking, not advisory. Whatever format is chosen here, the linkage to automated tests must be enforced, not just nice-to-have traceability.
- Markdown-native authoring measurably lowers the bar for non-engineer contribution — Gauge's core bet, and the reason GitHub-rendered Mermaid diagrams get engagement from PMs/designers that `.feature` files don't. Strong argument for markdown-first (or markdown + embedded diagram) as the base layer for a Claude Skill designed to keep docs collaboratively up to date.
- Statecharts show "diagram derived automatically from spec" is achievable, but only when the spec doubles as executable logic. A lightweight-markdown approach won't get this property for free — would need custom tooling (e.g., a script rendering a Mermaid diagram from a structured markdown/YAML journey file).
- Tool-specific DSLs (Gherkin, Robot Framework) trade human-readability for machine-parseability and mature CI ecosystems — a hybrid (markdown body + structured YAML frontmatter for `test_id`, `linked_ticket`, `last_verified`) may capture more of both worlds than any single surveyed tool alone.
- Vendor/maintainer risk is real even for popular formats — SpecFlow's 2024 EOL/Reqnroll emergence favors designing the journey format around plain markdown/YAML (which nothing can deprecate) with pluggable/optional tool integrations, rather than binding the format to any one framework's DSL.

## Open Questions

- Is there a need for branching/conditional journeys (e.g., "if user has 2FA enabled, additional step"), and which surveyed format supports this without becoming unreadable? (XState handles natively; Gherkin/Gauge do not without scenario duplication or Outlines/tables.)
- Should "linked to automated tests" mean a loose reference (markdown link/tag) or a strict machine-enforced binding (CI fails if referenced test doesn't exist or hasn't run recently)? Materially changes which prior art applies.
- Are target readers non-engineers (PM/design/support), weighting markdown/Mermaid rendering quality heavily, or purely engineering, making Gherkin/Robot Framework's stronger tooling more attractive despite worse rendering?
- Is there appetite for a custom lightweight schema (YAML frontmatter + markdown body, validated against JSON Schema) as this project's own format, given no existing standard fully satisfies markdown-first + parseable + diagrammable + test-linked simultaneously? (Flag for subtopic 3/skill design.)
- How stable is Gauge's current maintenance status as of mid-2026 — is ThoughtWorks still actively resourcing it? [TRAINING_ONLY — verify; not confirmed by searches run in this pass.]
- What does `@xstate/test` or its XState v5 equivalent look like today, and is generating test paths from a statechart worth prototyping as a "spec-drives-tests" pattern outside full XState adoption? [TRAINING_ONLY — verify current package/API.]

## Recommendation

No existing format should be adopted wholesale. The strongest foundation is a **markdown-first, YAML-frontmatter-plus-body hybrid**, borrowing specific ideas from three surveyed tools rather than adopting any single one:

1. **From Gauge**: plain markdown (headings for journey name, list items for steps) as the human-readable body — lowest barrier to non-engineer review/contribution, renders natively on GitHub/GitLab.
2. **From Gherkin/Cucumber Studio + Reqnroll/SpecSync's traceability pattern**: YAML frontmatter fields (or inline tags) for machine-parseable metadata — linked test IDs, requirement/ticket references, "last verified" timestamps — enabling CI tooling to check staleness/broken links without requiring a full formal grammar.
3. **From Mermaid**: embed a `journey` or `flowchart` diagram directly in the same markdown file for visual review, accepting it needs hand-maintenance or (better) generation from the structured step list to avoid drift — a natural task for a Claude Agent Skill to automate/verify.

Explicitly avoid full Gherkin/Cucumber, Robot Framework, or XState as the *primary* spec format: they either aren't markdown-native (Gherkin, Robot Framework) or require an architectural commitment disproportionate to "declarative journey documentation" (XState, Storybook CSF). These remain valuable as *execution backends* — a markdown journey spec could compile down to or reference Playwright/Cypress/Cucumber step implementations for the actual automated test — but the authored source of truth should stay in plain markdown + YAML frontmatter for readability, diffability, and zero-tooling rendering.

## Pending Web Searches

None — all 5 planned queries were executed with live web access. Items flagged `[TRAINING_ONLY — verify]` reflect gaps in returned search results (Gauge's current maintenance velocity, exact current state of `@xstate/test` in XState v5) rather than skipped searches; a follow-up search on those two points would sharpen confidence if budget allows in a later pass.
