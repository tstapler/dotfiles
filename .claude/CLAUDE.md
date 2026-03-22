# Claude Project Instructions

## Important Reminders

- Do what has been asked; nothing more, nothing less
- NEVER create files unless absolutely necessary
- ALWAYS prefer editing existing files to creating new ones
- NEVER proactively create documentation (*.md) unless explicitly requested
- Use the SUCCESS framework for communication style
- Only push the specific branch you're working on

## Tool Priority (CRITICAL)

Always prefer dedicated tools over Bash for these operations:

| Operation | Use This | NOT This |
|-----------|----------|----------|
| Read files | `Read` | `cat`, `head`, `tail`, `sed` |
| Edit files | `Edit` / `Write` | `sed`, `awk`, echo redirect |
| Find files | `Glob` | `find`, `ls` |
| Search text | `Grep` | `grep`, `rg` |
| Search code (structural) | `ast-grep` (`sg`) via Bash | `grep` for code patterns |
| Web search | `WebSearch` | — |
| Fetch URLs | `WebFetch` / `mcp__read-website-fast__read_website` | `curl` |

Reserve `Bash` exclusively for: git operations, running tests/commands, and system operations with no dedicated tool.

**Missing tools**: If a required CLI tool is not installed, use `WebSearch` to find the correct Homebrew formula, then install it with `brew install <formula>`. Use the `homebrew` skill for guidance.

## Code Editing

- Prefer `Edit` / `Write` tools for file changes
- Use the serena MCP server for complex multi-file structural edits when available

---

## Skills Index

Skills auto-activate based on task context. All skills located in `~/.claude/skills/`.

### Development & Code Quality

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `python-development` | Writing, reviewing, or debugging Python code; applying PEP 8, type annotations, uv package management, Pydantic DTOs, Typer CLIs, pytest patterns | "Write a Python CLI", "Add type hints to this module", "Fix this pytest failure" |
| `ast-grep` | Searching code by structure/syntax — function calls, class definitions, imports, decorators; any search where text matching isn't precise enough | "Find all callers of this method", "Find all async functions", "Search for usages of this decorator" |
| `gritql` | AST-based multi-file code transformations: rename methods/classes, migrate APIs, modernize patterns; always dry-run first | "Rename this method everywhere", "Migrate this API across the codebase", "Update all import paths" |
| `code-refactoring` | Orchestrating large structural refactors combining search (ast-grep) and transformation (gritql) with quality gates | "Refactor error handling across all controllers", "Rename method consistently throughout codebase" |
| `java-api-discovery` | Discovering actual Java API signatures from compiled JARs; encountering unknown methods, pagination patterns, union types, or compilation errors | "What methods does this AWS SDK class have?", "Find the correct signature for this Java API" |

### Version Control & Git Operations

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `git/worktrees` | Starting new feature branches needing isolation; working on multiple features simultaneously; requiring clean dependency states or avoiding merge conflicts | "Create a worktree for auth feature", "Set up isolated workspace", "Work on feature without switching branches" |
| `jj-version-control` | Using Jujutsu (jj) commands; working with revsets, bookmarks, anonymous branches; splitting/squashing commits; editing history; pushing to git remotes | "Commit with jj", "Split this change into multiple commits", "Rebase using jj", "Create bookmark" |
| `github-pr` | Working with GitHub pull requests; reviewing PRs, creating PRs, checking PR status, viewing comments, analyzing CI failures; using gh CLI commands | "Create a PR for this branch", "Review PR #123", "Check why CI failed", "List open PRs" |

### Infrastructure & DevOps

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `homebrew` | Installing or managing macOS CLI tools or apps; a required tool is missing; troubleshooting formula conflicts or taps | "Install ast-grep", "Tool not found", "Upgrade all packages", "Add a Homebrew tap" |
| `infrastructure-testing` | Running TestKube or PGBouncer tests on Kubernetes clusters; requires mandatory context verification to prevent wrong-cluster operations | "Run TestKube tests on staging", "Verify PGBouncer config", "Test database connection pooling" |
| `docker-build-test` | Building and testing Docker images locally; validating before pushing; preventing CI/CD failures with pre-push checklist | "Build Docker image", "Test container locally before push", "Validate Dockerfile changes" |
| `fbg-terraform-changes` | Navigating or modifying FBG's shared Terraform infrastructure; adding services, modifying configs, extending modules | "Add new service to Terraform", "Update RDS config", "Extend EKS module" |

### Documentation & Knowledge Management

| Skill | Invoke When | Examples |
|-------|------------|----------|
| `knowledge-synthesis` | Synthesizing knowledge from multiple sources into Zettelkasten notes; creating wiki pages with [[links]] and #[[tags]]; integrating academic research | "Synthesize this article into Zettel", "Create wiki page for concept", "Integrate research notes" |
| `markdown-confluence-sync` | Publishing markdown to Confluence; crawling/downloading Confluence pages; syncing bidirectionally; checking sync status; resolving conflicts; managing comments; validating links; troubleshooting page issues | "Publish docs to Confluence", "Crawl Confluence page", "Download this Confluence page", "Check sync status", "Resolve Confluence conflicts", "Validate Confluence links" |

### Browser Automation

| Skill | Invoke When | Examples |
|-------|------------|----------|
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

### Skill Usage Patterns

**Auto-activation**: Skills automatically activate when Claude detects relevant task context from your request.

**Explicit invocation**: You can explicitly reference a skill by name (e.g., "Use the python-development skill to...").

**Skill chaining**: Skills can invoke other skills (e.g., git/worktrees may use python-development for Python projects).

**Progressive disclosure**: Skills load context progressively - core instructions first, detailed references only when needed.
