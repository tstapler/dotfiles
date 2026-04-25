# Skills Index

Skills auto-activate based on task context. All skills located in `~/.claude/skills/`.

---

## MDD Phase Gate Reference

Use the correct command for each workflow phase. Never skip phases — each artifact is required input for the next.

| Phase | Command | Produces | Where |
|---|---|---|---|
| **1. Ideation** | `/plan:mdd-start` | `requirements.md` | `project_plans/<project>/` |
| **2. Research** | `/research-workflow` | `research/*.md` (stack, features, architecture, pitfalls) | `project_plans/<project>/research/` |
| **3. Planning** | `/plan:feature` or `/handy:plan` | `plan.md` + ADRs (via `/plan:adr`) | `project_plans/<project>/implementation/` + `decisions/` |
| **4. Validation** | `/quality:test-planner` | `validation.md` | `project_plans/<project>/implementation/` |
| **5. Implementation** | `/code:implement` | Code + tests | Target repo |
| **6. QA** | `/quality:does-it-work` + `/code:review` | Sign-off | Target repo |

**Key rule**: Open a fresh session before Phase 5. Planning context degrades implementation quality.

**Session hygiene**: Run `/knowledge:extract-learnings` at session end to capture instincts.

**Context health**: Run `/meta:context-audit` to check token budget.

---

### Code & Development

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `code-python` | Writing, reviewing, or debugging Python code; applying PEP 8, type annotations, uv package management, Pydantic DTOs, Typer CLIs, pytest patterns | "Write a Python CLI", "Add type hints to this module", "Fix this pytest failure" |
| `code-ast-grep` | Searching code by structure/syntax — function calls, class definitions, imports, decorators; any search where text matching isn't precise enough | "Find all callers of this method", "Find all async functions", "Search for usages of this decorator" |
| `code-gritql` | AST-based multi-file code transformations: rename methods/classes, migrate APIs, modernize patterns; always dry-run first | "Rename this method everywhere", "Migrate this API across the codebase", "Update all import paths" |
| `code-refactoring` | Orchestrating large structural refactors combining search (ast-grep) and transformation (gritql) with quality gates | "Refactor error handling across all controllers", "Rename method consistently throughout codebase" |
| `code-review` | Receiving or requesting code review; before claiming a task is complete; before committing or creating PRs; when feedback seems technically questionable; after fixing complex bugs | "Review this code", "Is this ready to commit?", "I got this review comment", "Check my fix before I push" |
| `code-archaeology` | Analyzing external codebases by cloning repos or extracting archives to temp dirs; reverse-engineering code to extract requirements, identify architectural patterns, and catalog design choices | "Analyze this repo", "Reverse engineer this codebase", "Extract requirements from this project", "What does this project do?" |
| `code-architecture-best-practices` | Designing or reviewing system architecture, class structures, modules, and data flows; applying SOLID, DDD, hexagonal architecture patterns | "Review this system design", "How should I structure this service?", "Apply clean architecture here" |
| `code-debugging` | Systematic debugging with proven frameworks; encountering bugs, test failures, or unexpected behavior; needs root-cause tracing, defense-in-depth validation, or verification before claiming a fix is complete | "Debug this failure", "Find root cause", "Verify this fix works", "Test is failing" |
| `code-root-cause-analysis` | Investigating errors with stack traces; debugging incidents or outages; finding historical context for similar issues; searching for past solutions in wiki | "Why is this failing?", "Find similar errors in wiki", "Debug this stack trace", "What caused this incident before?" |
| `code-java-api-discovery` | Discovering actual Java API signatures from compiled JARs; encountering unknown methods, pagination patterns, union types, or compilation errors | "What methods does this AWS SDK class have?", "Find the correct signature for this Java API" |
| `code-spring-boot` | Writing, reviewing, or designing Java/Spring Boot code; applying Spring conventions, testing patterns, dependency injection | "Review this Spring controller", "Write a Spring Boot service", "Fix this Spring test" |
| `code-strands` | Building agents with the AWS Strands Agents SDK; structuring prompts, multi-agent patterns, tool definitions | "Build a Strands agent", "Structure this multi-agent workflow", "Define tools for Strands" |

### Version Control & Git

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `git-worktrees` | Starting new feature branches needing isolation; working on multiple features simultaneously; requiring clean dependency states or avoiding merge conflicts | "Create a worktree for auth feature", "Set up isolated workspace", "Work on feature without switching branches" |
| `git-upstream-fork` | Identifying commits in a locally-checked-out source repo that should be upstreamed; comparing fork divergence | "What changes should I upstream?", "Compare my fork to upstream" |
| `jj-version-control` | Using Jujutsu (jj) commands; working with revsets, bookmarks, anonymous branches; splitting/squashing commits; editing history; pushing to git remotes | "Commit with jj", "Split this change into multiple commits", "Rebase using jj", "Create bookmark" |
| `github-pr` | Working with GitHub pull requests; reviewing PRs, creating PRs, checking PR status, viewing comments, analyzing CI failures; using gh CLI commands | "Create a PR for this branch", "Review PR #123", "Check why CI failed", "List open PRs" |
| `github-actions-debugging` | Debugging GitHub Actions workflow failures; analyzing logs, identifying error patterns, syntax errors, dependency issues | "Why did my workflow fail?", "Fix this GitHub Actions error", "Debug CI pipeline" |
| `github-composite-actions` | Writing, debugging, or designing GitHub Actions composite actions; `uses:` field, input/output definitions | "Create a composite action", "Debug this reusable action", "Design GitHub Actions workflow" |
| `github-address-pr-comments` | Systematically addressing all open GitHub PR review comments; fixing code or declining with reasoning | "Address these PR review comments", "Respond to all review feedback" |
| `github-org-team-activity` | Looking up what people in a GitHub org have been working on; summarizing PRs, repos touched, and activity narrative for a given timeframe; supports display name or handle input | "What has Tyler Stapler been working on?", "Summarize team activity this sprint", "What repos has this person touched?", "Prep for 1:1 with teammate" |
| `fork-merge-plan` | Planning a bidirectional merge between a personal fork and upstream repo; both branches have diverged and you need to preserve functionality from both sides; produces a written plan with commit classification, conflict map, and merge strategy — no merge is executed | "Plan merging my fork with upstream", "What would conflict if I merged upstream?", "Create a merge plan for stapler-squad", "Classify commits before merging" |

### Infrastructure & DevOps

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `infra-homebrew` | Installing or managing macOS CLI tools or apps; a required tool is missing; troubleshooting formula conflicts or taps | "Install ast-grep", "Tool not found", "Upgrade all packages", "Add a Homebrew tap" |
| `infra-testing` | Running TestKube or PGBouncer tests on Kubernetes clusters; requires mandatory context verification to prevent wrong-cluster operations | "Run TestKube tests on staging", "Verify PGBouncer config", "Test database connection pooling" |
| `infra-docker-build-test` | Building and testing Docker images locally; validating before pushing; preventing CI/CD failures with pre-push checklist | "Build Docker image", "Test container locally before push", "Validate Dockerfile changes" |

### Product Management

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `pm-product-management` | Writing PRDs, creating outcome-based roadmaps, drafting user stories with acceptance criteria, scoping features, analyzing trade-offs, applying prioritization frameworks (RICE, MoSCoW, Kano, JTBD); acting as own PM for software projects | "Write a PRD for this feature", "Prioritize my backlog", "Create a roadmap", "Write user stories", "Scope this feature", "Should I build A or B?" |
| `pm-product-manager` | Evidence-based product management for roadmap decisions, feature prioritization, discovery interviews, metrics definition | "Define success metrics", "Run a discovery session", "Evaluate this feature request" |
| `pm-brand-guidelines` | Applying, documenting, or enforcing brand guidelines for any product or company | "Apply brand guidelines", "Document our brand standards", "Is this on-brand?" |
| `pm-brand-strategy` | Establishing or iterating on brand strategy and marketing direction; positioning, messaging, audience definition | "Define our brand strategy", "Position this product", "Refine our messaging" |

### Documentation — Writing Workflow (Diataxis-based, spec-driven)

Start here when writing any new document from scratch. Each command produces the artifact the next requires.

**Full workflow (guided)**: `/docs:write [topic]` — runs all phases in sequence with approval gates

**Step-by-step (manual)**:

| Phase | Command | Input → Artifact | When |
|---|---|---|---|
| **1. Define** | `/docs:define [topic]` | Interview → `audience-purpose.md` | Before any outline or draft |
| **2. Outline** | `/docs:outline` | audience-purpose → `outline.md` | After defining audience and type |
| **3. Draft** | `/docs:draft` | outline → draft document | After skeleton is set |
| **4. Review** | `/docs:review-clarity` | draft → annotated review | Before considering it done |
| **5. Polish** | `/docs:refine-writing` | draft → polished document | Final pass |

**Core principle**: Readers are foragers. Every document has exactly one Diataxis type (Tutorial / How-to / Reference / Explanation). Mixing types satisfies no reader.

**Improvement commands** (for existing documents):
- `/docs:prune` — remove duplication and outdated content
- `/docs:update` — update docs after code changes

### Knowledge Management

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `knowledge-synthesis` | Synthesizing knowledge from multiple sources into Zettelkasten notes; creating wiki pages with [[links]] and #[[tags]]; integrating academic research | "Synthesize this article into Zettel", "Create wiki page for concept", "Integrate research notes" |
| `knowledge-confluence-sync` | Publishing markdown to Confluence; crawling/downloading Confluence pages; syncing bidirectionally; checking sync status; resolving conflicts; managing comments; validating links | "Publish docs to Confluence", "Crawl Confluence page", "Download this Confluence page", "Check sync status" |

### Web Fetching & Browser Automation

| Tool / Skill | Invoke When | Examples |
|--------------|------------|----------|
| `mcp__read-website-fast__read_website` | Reading a single URL and getting clean Markdown back; fetching docs, articles, or pages for analysis; prefer over WebFetch. **Context warning**: large pages dump full content into context — if the page is long, save the result to `/tmp` and reference the path instead of holding it in context | "Read this page", "Get the content of this URL", "Fetch these docs" |
| `mcp__website-downloader__download_page` | Saving a single fully-rendered page to disk; JavaScript-heavy pages that require a real browser | "Save this page locally", "Download this SPA page" |
| `mcp__website-downloader__download_website` | Recursively downloading a site to local disk for offline analysis; crawling a domain | "Download this site", "Archive this docs site locally", "Crawl and save these pages" |
| `ui-playwright` | Browser automation, web testing, screenshotting pages, testing login flows, checking responsive design, validating links, or automating any browser interaction; auto-detects local dev servers | "Test this page", "Screenshot this URL", "Check for broken links", "Test the login flow", "Automate this form" |

### UI & Frontend Design

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `ui-design-system` | Designing or building any UI — landing pages, dashboards, mobile apps, components; choosing styles, colors, fonts; reviewing UI quality; improving perceived professionalism of an interface | "Build a landing page for my SaaS", "What color palette fits a fintech app?", "Review this dashboard for UX issues", "Make this form more accessible" |
| `ui-react-best-practices` | Writing, reviewing, or refactoring React/Next.js code for performance; data fetching, bundle optimization, re-render issues, SSR patterns | "Review this React component", "Why is my Next.js page slow?", "Optimize my data fetching", "Fix this waterfall" |
| `ui-web-design-guidelines` | Auditing UI code against 100+ web best practices — accessibility, focus states, forms, animation, typography, images, performance, dark mode, i18n | "Review my UI", "Check accessibility", "Audit my design against best practices", "Review UX" |
| `ui-composition-patterns` | Refactoring React components with too many boolean props; designing flexible component APIs; compound components, state lifting, render props, React 19 patterns | "Refactor this component with boolean props", "Design a reusable component API", "Review my component architecture" |
| `ui-frontend-design` | Creating distinctive, production-grade frontend interfaces with high design quality; visual polish, component aesthetics, design tokens | "Design this component", "Make this page look professional", "Improve the visual quality of this UI" |
| `ui-android-ux-design` | Implementing Android UI features following Material Design 3 (Material You) principles; UX patterns for Android/Jetpack Compose | "Apply Material Design here", "Review this Android UI", "Implement this Android UX pattern" |
| `ui-logo-designer` | Designing or iterating on logos using SVG; brand mark creation | "Create a logo", "Design an icon for my app", "Iterate on this logo concept" |
| `ux-expert` | Strategic UX review using heuristics; evaluating user flows, interaction design, information architecture; accessibility audits; applying Nielsen/Krug/WCAG principles | "Review this user flow", "Evaluate my navigation structure", "Apply Nielsen heuristics to this screen" |

### Tooling & Meta-Development

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `meta-prompt-engineering` | Creating or improving prompts, agents, commands, system instructions, SKILL.md files; applying XML tags, multishot examples, chain-of-thought, response prefilling | "Create a new agent", "Improve this prompt", "Add examples to SKILL.md", "Optimize context usage" |
| `meta-model-selection` | Choosing appropriate Claude model (Opus 4.5, Sonnet, Haiku) for agents, commands, or Task tool invocations based on complexity, reasoning depth, cost/speed | "Which model should I use for this agent?", "Optimize agent model selection", "Choose model for complex reasoning task" |
| `meta-research-workflow` | Performing multi-step research, fact-finding, web searches, verification tasks; using Brave Search, Puppeteer, or synthesizing information from sources | "Research best practices for X", "Find documentation for Y", "Verify claims about Z", "Search and synthesize findings" |
| `meta-claude-technique-evaluator` | Evaluating new Claude/Claude Code techniques, tools, features, or workflow changes for adoption value; assessing blog posts, release notes, community tips against Anthropic best practices and current workflow fit | "Evaluate this Claude technique", "Is this prompting pattern worth adopting?", "Assess this new Claude Code feature", "Should I use extended thinking?" |
| `meta-context-engineering` | Designing agent architectures; debugging context failures; optimizing token usage; implementing memory systems; building multi-agent coordination; evaluating agent performance | "Optimize context for this agent", "Why is my agent losing context?", "Design memory system", "Reduce token usage" |
