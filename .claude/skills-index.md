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

### Product & Project Management

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `product-management` | Writing PRDs, defining features, creating roadmaps, drafting user stories with acceptance criteria, scoping features, prioritizing backlogs, analyzing trade-offs. **Use before `@project-coordinator`** — PM artifacts (PRD, stories) are the upstream input for task decomposition. | "Write a PRD for this feature", "Create a roadmap", "Draft user stories for the sync feature", "Should I build X or Y?", "Prioritize my backlog" |

### Development & Code Quality

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `python-development` | Writing, reviewing, or debugging Python code; applying PEP 8, type annotations, uv package management, Pydantic DTOs, Typer CLIs, pytest patterns | "Write a Python CLI", "Add type hints to this module", "Fix this pytest failure" |
| `ast-grep` | Searching code by structure/syntax — function calls, class definitions, imports, decorators; any search where text matching isn't precise enough | "Find all callers of this method", "Find all async functions", "Search for usages of this decorator" |
| `gritql` | AST-based multi-file code transformations: rename methods/classes, migrate APIs, modernize patterns; always dry-run first | "Rename this method everywhere", "Migrate this API across the codebase", "Update all import paths" |
| `code-refactoring` | Orchestrating large structural refactors combining search (ast-grep) and transformation (gritql) with quality gates | "Refactor error handling across all controllers", "Rename method consistently throughout codebase" |
| `java-api-discovery` | Discovering actual Java API signatures from compiled JARs; encountering unknown methods, pagination patterns, union types, or compilation errors | "What methods does this AWS SDK class have?", "Find the correct signature for this Java API" |
| `code-archaeology` | Analyzing external codebases by cloning repos or extracting archives to temp dirs; reverse-engineering code to extract requirements, identify architectural patterns, and catalog design choices and problems | "Analyze this repo", "Reverse engineer this codebase", "Extract requirements from this project", "What does this project do?" |

### Version Control & Git Operations

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `git-worktrees` | Starting new feature branches needing isolation; working on multiple features simultaneously; requiring clean dependency states or avoiding merge conflicts | "Create a worktree for auth feature", "Set up isolated workspace", "Work on feature without switching branches" |
| `jj-version-control` | Using Jujutsu (jj) commands; working with revsets, bookmarks, anonymous branches; splitting/squashing commits; editing history; pushing to git remotes | "Commit with jj", "Split this change into multiple commits", "Rebase using jj", "Create bookmark" |
| `github-pr` | Working with GitHub pull requests; reviewing PRs, creating PRs, checking PR status, viewing comments, analyzing CI failures; using gh CLI commands | "Create a PR for this branch", "Review PR #123", "Check why CI failed", "List open PRs" |
| `fork-merge-plan` | Planning a bidirectional merge between a personal fork and upstream repo; both branches have diverged and you need to preserve functionality from both sides; produces a written plan with commit classification, conflict map, and merge strategy — no merge is executed | "Plan merging my fork with upstream", "What would conflict if I merged upstream?", "Create a merge plan for stapler-squad", "Classify commits before merging" |

### Infrastructure & DevOps

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `homebrew` | Installing or managing macOS CLI tools or apps; a required tool is missing; troubleshooting formula conflicts or taps | "Install ast-grep", "Tool not found", "Upgrade all packages", "Add a Homebrew tap" |
| `infrastructure-testing` | Running TestKube or PGBouncer tests on Kubernetes clusters; requires mandatory context verification to prevent wrong-cluster operations | "Run TestKube tests on staging", "Verify PGBouncer config", "Test database connection pooling" |
| `docker-build-test` | Building and testing Docker images locally; validating before pushing; preventing CI/CD failures with pre-push checklist | "Build Docker image", "Test container locally before push", "Validate Dockerfile changes" |
| `fbg-terraform-changes` | Navigating or modifying FBG's shared Terraform infrastructure; adding services, modifying configs, extending modules | "Add new service to Terraform", "Update RDS config", "Extend EKS module" |

### Product & Project Management

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `product-management` | Writing PRDs, creating outcome-based roadmaps, drafting user stories with acceptance criteria, scoping features, analyzing trade-offs, applying prioritization frameworks (RICE, MoSCoW, Kano, JTBD); acting as own PM for software projects | "Write a PRD for this feature", "Prioritize my backlog", "Create a roadmap", "Write user stories", "Scope this feature", "Should I build A or B?" |

### Documentation & Knowledge Management

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `knowledge-synthesis` | Synthesizing knowledge from multiple sources into Zettelkasten notes; creating wiki pages with [[links]] and #[[tags]]; integrating academic research | "Synthesize this article into Zettel", "Create wiki page for concept", "Integrate research notes" |
| `markdown-confluence-sync` | Publishing markdown to Confluence; crawling/downloading Confluence pages; syncing bidirectionally; checking sync status; resolving conflicts; managing comments; validating links; troubleshooting page issues | "Publish docs to Confluence", "Crawl Confluence page", "Download this Confluence page", "Check sync status", "Resolve Confluence conflicts", "Validate Confluence links" |

### Web Fetching & Browser Automation

| Tool / Skill | Invoke When | Examples |
|--------------|------------|----------|
| `mcp__read-website-fast__read_website` | Reading a single URL and getting clean Markdown back; fetching docs, articles, or pages for analysis; prefer over WebFetch. **Context warning**: large pages dump full content into context — if the page is long, save the result to `/tmp` and reference the path instead of holding it in context | "Read this page", "Get the content of this URL", "Fetch these docs" |
| `mcp__website-downloader__download_page` | Saving a single fully-rendered page to disk; JavaScript-heavy pages that require a real browser | "Save this page locally", "Download this SPA page" |
| `mcp__website-downloader__download_website` | Recursively downloading a site to local disk for offline analysis; crawling a domain | "Download this site", "Archive this docs site locally", "Crawl and save these pages" |
| `playwright-skill` | Browser automation, web testing, screenshotting pages, testing login flows, checking responsive design, validating links, or automating any browser interaction; auto-detects local dev servers | "Test this page", "Screenshot this URL", "Check for broken links", "Test the login flow", "Automate this form" |

### Debugging & Investigation

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `root-cause-analysis` | Investigating errors with stack traces; debugging incidents or outages; finding historical context for similar issues; searching for past solutions in wiki | "Why is this failing?", "Find similar errors in wiki", "Debug this stack trace", "What caused this incident before?" |
| `debugging` | Systematic debugging with proven frameworks; encountering bugs, test failures, or unexpected behavior; needs root-cause tracing, defense-in-depth validation, or verification before claiming a fix is complete | "Debug this failure", "Find root cause", "Verify this fix works", "Test is failing" |
| `code-review` | Receiving or requesting code review; before claiming a task is complete; before committing or creating PRs; when feedback seems technically questionable; after fixing complex bugs | "Review this code", "Is this ready to commit?", "I got this review comment", "Check my fix before I push" |

### Tooling & Meta-Development

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `prompt-engineering` | Creating or improving prompts, agents, commands, system instructions, SKILL.md files; applying XML tags, multishot examples, chain-of-thought, response prefilling | "Create a new agent", "Improve this prompt", "Add examples to SKILL.md", "Optimize context usage" |
| `model-selection` | Choosing appropriate Claude model (Opus 4.5, Sonnet, Haiku) for agents, commands, or Task tool invocations based on complexity, reasoning depth, cost/speed | "Which model should I use for this agent?", "Optimize agent model selection", "Choose model for complex reasoning task" |
| `research-workflow` | Performing multi-step research, fact-finding, web searches, verification tasks; using Brave Search, Puppeteer, or synthesizing information from sources | "Research best practices for X", "Find documentation for Y", "Verify claims about Z", "Search and synthesize findings" |
| `claude-technique-evaluator` | Evaluating new Claude/Claude Code techniques, tools, features, or workflow changes for adoption value; assessing blog posts, release notes, community tips against Anthropic best practices and current workflow fit | "Evaluate this Claude technique", "Is this prompting pattern worth adopting?", "Assess this new Claude Code feature", "Should I use extended thinking?" |
| `context-engineering` | Designing agent architectures; debugging context failures; optimizing token usage; implementing memory systems; building multi-agent coordination; evaluating agent performance | "Optimize context for this agent", "Why is my agent losing context?", "Design memory system", "Reduce token usage" |
