# User-Level Claude Code Commands

These commands are available across **all your projects** and help with common development workflows.

## Agent Architecture & Best Practices

All commands in this repository follow a consistent agent delegation pattern for maximum effectiveness:

### Agent Delegation Pattern

Commands use the `@task [agent-name]` syntax to delegate work to specialized agents:

```markdown
@task agent-name

Execute the task with specific instructions and context
```

### XML Format for Complex Prompts

**Best Practice**: Complex command prompts should use XML format for structured, hierarchical instructions. XML provides:
- Clear hierarchical organization of instructions
- Easy parsing and validation
- Consistent structure across commands
- Better LLM comprehension of complex requirements

**Example Structure**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<prompt>
    <system>Agent role and expertise</system>
    <role>
        <primary>Primary responsibility</primary>
        <expertise>
            <area>Domain 1</area>
            <area>Domain 2</area>
        </expertise>
    </role>
    <approach>
        <step number="1">...</step>
    </approach>
</prompt>
```

### Agent Roster

| Agent | Purpose | Used By |
|-------|---------|---------|
| `doc-quality-analyzer` | Documentation freshness and quality analysis | /docs:update, /docs:prune |
| `technical-writing-coach` | Writing style and clarity improvement | /docs:refine-writing |
| `postgres-optimizer` | Database schema optimization | /db:review |
| `project-coordinator` | Project planning and task organization | /plan:status, /plan:next-step, /plan:sync, /db:review (phase 2) |
| `software-planner` | Feature planning with architectural design | /plan:feature |
| `jira-project-manager` | Jira ticket creation with FBG standards | /jira:* |
| `prompt-engineering` | Agent and command refinement | /meta:refine |
| `code-refactoring` | Code quality improvements | /quality:* |
| `knowledge-synthesis` | Knowledge base integration | /knowledge:* |

## Documentation Management (`/docs:*`)

| Command | Purpose | Frequency |
|---------|---------|-----------|
| **/docs:update** | Update docs impacted by recent code changes | After features, before PRs |
| **/docs:prune** | Remove duplication and consolidate documentation | Monthly maintenance |
| **/docs:refine-writing** | Improve documentation writing style and clarity | As needed for doc improvements |

**Agents Used:**
- `doc-quality-analyzer` - Systematically analyzes documentation freshness, accuracy, and completeness using Diataxis framework
- `technical-writing-coach` - Improves documentation writing style, clarity, and impact following technical writing best practices

### Key Features
- ✅ Diataxis framework for documentation organization
- ✅ Automatic freshness analysis based on code changes
- ✅ Duplication and consolidation detection
- ✅ Technical writing quality improvements (clarity, conciseness, precision)
- ✅ Git-integrated documentation updates

### Coming Soon
- **/docs:validate** - Check documentation quality before releases

## Database Operations (`/db:*`)

| Command | Purpose | Frequency |
|---------|---------|-----------|
| **/db:review** | Comprehensive PostgreSQL schema analysis and optimization | Quarterly reviews |

**Agents Used:**
- `postgres-optimizer` - Comprehensive PostgreSQL schema analysis using database engineering principles (Phase 1)
- `project-coordinator` - Organizes optimization findings into actionable ATOMIC tasks (Phase 2)

### Key Features
- ✅ Comprehensive schema analysis (indexes, normalization, cardinality)
- ✅ Unused/missing index identification
- ✅ Query performance analysis with EXPLAIN
- ✅ Anti-pattern detection (N+1, over-indexing, under-indexing)
- ✅ Zero-downtime migration strategies
- ✅ AIC-compliant task breakdown for optimizations

### Coming Soon
- **/db:optimize** - Execute specific database optimizations
- **/db:migrate** - Plan and document database migrations

## Jira & Confluence (`/jira:*`)

| Command | Purpose | Frequency |
|---------|---------|-----------|
| **/jira:create** | Create well-structured Jira tickets following INVEST principles | As needed for new work |
| **/jira:plan** | Break down features into manageable stories and epics | During project planning |
| **/jira:doc** | Create Confluence documentation using Diataxis framework | After features, during planning |
| **/jira:incident** | Handle production incidents with proper bug tickets | Emergency response |

**Agent Used:** `jira-project-manager` - Embodies FBG standards with strict hierarchy enforcement (Features → Epics → Stories → Sub-tasks), INVEST principles validation, and zero tolerance for formatting violations.

### Key Features
- ✅ Strict hierarchy compliance (no Story-as-parent violations)
- ✅ Automatic INVEST framework validation
- ✅ Proper Jira formatting with escaped code blocks
- ✅ Complete acceptance criteria in dedicated fields
- ✅ "TylerBot" label for tracking
- ✅ Diataxis documentation framework for Confluence

### Coming Soon
- **/jira:update** - Modify existing tickets while maintaining standards
- **/jira:link** - Create proper dependencies and issue links

## Project Planning (`/plan:*`)

| Command | Purpose | Frequency |
|---------|---------|-----------|
| **/plan:status** | Review progress and get next action recommendation | Daily (start of session) |
| **/plan:sync** | Update all plans to reflect current project state | Weekly/bi-weekly |
| **/plan:next-step** | Analyze TODO.md, curate documentation, recommend optimal next step | When deciding what to work on |
| **/plan:feature** | Comprehensive feature planning with architecture + LLM-optimized tasks | Before starting new features |

**Agents Used:**
- `project-coordinator` - Strategic planning, TODO.md analysis, and task coordination for /plan:status, /plan:next-step, /plan:sync
- `software-planner` - Comprehensive feature architecture and LLM-optimized task decomposition for /plan:feature

**Prompt Format**: All /plan commands use **XML format** for structured, hierarchical instructions (see Agent Architecture section above)

### Key Features
- ✅ ATOMIC-INVEST-CONTEXT (AIC) framework enforcement
- ✅ Context boundaries (3-5 files, 1-4 hours per task)
- ✅ TODO.md curation and Git integration
- ✅ Generates `docs/tasks/{feature-name}.md` documentation
- ✅ Software engineering principles (DDD, design patterns, architecture)
- ✅ Epic → Story → Task hierarchical breakdown
- ✅ XML-structured prompts for complex planning workflows

### Coming Soon
- **/plan:create** - Create new AIC-compliant task or project plan
- **/plan:archive** - Archive completed plans and update references

## Meta-Development (`/meta:*`)

| Command | Purpose | Frequency |
|---------|---------|-----------|
| **/meta:new-agent** | Create new specialized agent with proper structure | When new domain expertise needed |
| **/meta:new-command** | Create new slash command with namespace organization | When new workflow needed |
| **/meta:refine** | Improve existing agents, commands, or prompts | When enhancing effectiveness |

**Agent Used:** `prompt-engineering` - Expert in prompt design, agent creation, and command refinement using established patterns and best practices.

### Key Features
- ✅ Transform basic prompts into comprehensive, structured instructions
- ✅ Design agents with proper specialization boundaries
- ✅ Create commands with optimal namespace organization
- ✅ Refine existing content for clarity and actionability
- ✅ Apply XML/YAML/Markdown patterns appropriately
- ✅ Ensure context efficiency and quality standards

### When to Use Meta Commands
- **Creating Agents**: Need specialized domain expertise that warrants dedicated agent
- **Creating Commands**: New workflow that fits into existing or new namespace
- **Refining Content**: Existing agent/command needs improvement or expansion
- **Prompt Engineering**: Transform basic idea into professional, actionable prompt

## Git & Version Control (`/git:*`)

| Command | Purpose | Frequency |
|---------|---------|-----------|
| **/git:commit** | Create commits using Conventional Commits format | After completing features or fixes |
| **/git:identify-unmerged-changes** | Identify changes not yet merged to main branch | Before releases or syncs |
| **/git:merge-worktree-to-main** | Merge worktree changes to main branch safely | When integrating long-running branches |

### Key Features
- ✅ Conventional Commits format enforcement
- ✅ Safe merging with conflict detection
- ✅ Branch state analysis and tracking

## Code Quality & Refactoring (`/quality:*`)

| Command | Purpose | Frequency |
|---------|---------|-----------|
| **/quality:does-it-work** | Review if changes are ready for commit and review | Before commits and PRs |
| **/quality:find-refactor-candidates** | Identify files needing refactoring using metrics | Monthly code health reviews |
| **/quality:refactor-code** | Refactor code following principles and best practices | When addressing technical debt |
| **/quality:test-planner** | Create comprehensive testing plan based on changes | Before implementing new features |

**Agent Used:** `code-refactoring` - Applies software engineering principles, design patterns, and best practices from authoritative literature to improve code quality while preserving behavior.

### Key Features
- ✅ SOLID principles and design pattern application
- ✅ Language-specific idiom modernization
- ✅ Maintainability-focused refactoring
- ✅ Automated test planning and coverage analysis

## Knowledge Management (`/knowledge:*`)

| Command | Purpose | Frequency |
|---------|---------|-----------|
| **/knowledge:return-zettel** | Create comprehensive Zettelkasten note for Logseq | When capturing important insights |
| **/knowledge:synthesize-knowledge** | Analyze external content and integrate into knowledge base | When researching new topics |

**Agent Used:** `knowledge-synthesis` - Systematically analyzes external content, researches supporting/contradicting evidence, creates book zettels, and maintains synthesis tracking.

### Key Features
- ✅ Logseq-optimized Zettelkasten format
- ✅ Semantic interconnections between notes
- ✅ Evidence-based synthesis with citations
- ✅ Daily journal integration for tracking

## Usage Examples

### Daily Workflow
```bash
# Start your day
/plan:status  # "What should I work on next?"
```

### Creating Jira Tickets
```bash
# Create a new feature story
/jira:create Add user authentication with OAuth2 support

# Break down a large feature
/jira:plan Implement real-time notification system

# Document a new API
/jira:doc REST API endpoints for user management

# Handle a production incident
/jira:incident Database connection pool exhaustion in prod
```

### Meta-Development Workflows
```bash
# Create a new agent for specialized domain
/meta:new-agent database-migration database-migrations sonnet

# Create a new command in existing namespace
/meta:new-command quality:analyze personal "Analyze code quality metrics"

# Refine an existing agent
/meta:refine The postgres-optimizer agent needs better indexing strategy guidance

# Transform a basic prompt
/meta:refine "Act as a technical writer for API documentation"
```

### After Code Changes
```bash
/docs:update  # Analyzes git diff and updates relevant docs
```

### Weekly Maintenance
```bash
# Keep plans synchronized
/plan:sync  # Updates TODO.md and all task files
```

### Monthly Maintenance
```bash
/docs:prune  # Consolidates and removes outdated documentation
/db:review   # Comprehensive schema optimization analysis
```

## Command Conventions

### Naming and Organization

1. **Use namespace prefixes for related commands** - Commands should be grouped by domain:
   - `/docs:*` - Documentation operations
   - `/db:*` - Database operations
   - `/jira:*` - Jira ticket creation and Confluence documentation (FBG)
   - `/plan:*` - Project planning
   - `/task:*` - Task management
   - `/git:*` - Git/version control operations
   - `/quality:*` - Code quality and refactoring
   - `/knowledge:*` - Knowledge management (Zettelkasten)
   - `/meta:*` - Meta-development (creating agents/commands)

2. **Naming conventions**:
   - Use kebab-case for command names (e.g., `test-plan`, not `testPlan`)
   - Use descriptive but concise names (e.g., `sync` not `synchronize-all-plans`)
   - Avoid redundant namespace in command name (e.g., `/docs:update` not `/docs:update-docs`)

3. **When to create a new command vs. extending an existing one**:
   - ⚠️ **Check existing commands first** - Can your functionality be added as context to an existing command?
   - ✅ **Create new command** if it serves a distinctly different purpose
   - ❌ **Don't create** if it's just a variation of an existing workflow
   - Example: `/docs:update` handles doc updates after code changes. Don't create `/docs:update-api` for API docs specifically - add that as context to the existing command.

### Directory Structure

Commands are organized in namespaces using subdirectories:

```
~/.claude/commands/
├── docs/
│   ├── update.md           → /docs:update
│   ├── prune.md            → /docs:prune
│   └── refine-writing.md   → /docs:refine-writing
├── db/
│   └── review.md           → /db:review
├── jira/
│   ├── create.md           → /jira:create
│   ├── plan.md             → /jira:plan
│   ├── doc.md              → /jira:doc
│   └── incident.md         → /jira:incident
├── plan/
│   ├── status.md     → /plan:status
│   ├── sync.md       → /plan:sync
│   ├── next-step.md  → /plan:next-step  (comprehensive TODO analysis + AIC)
│   └── feature.md    → /plan:feature    (architecture + task documentation)
├── meta/
│   ├── new-agent.md    → /meta:new-agent
│   ├── new-command.md  → /meta:new-command
│   └── refine.md       → /meta:refine
├── git/
│   ├── commit.md                    → /git:commit
│   ├── identify-unmerged-changes.md → /git:identify-unmerged-changes
│   └── merge-worktree-to-main.md    → /git:merge-worktree-to-main
├── quality/
│   ├── does-it-work.md              → /quality:does-it-work
│   ├── find-refactor-candidates.md  → /quality:find-refactor-candidates
│   ├── refactor-code.md             → /quality:refactor-code
│   └── test-planner.md              → /quality:test-planner
├── knowledge/
│   ├── return-zettel.md         → /knowledge:return-zettel
│   └── synthesize-knowledge.md  → /knowledge:synthesize-knowledge
└── [namespace]/
    └── [command].md
```

### Adding New Commands

1. **Choose or create appropriate namespace directory**:
   ```bash
   mkdir -p ~/.claude/commands/[namespace]
   ```

2. **Create command file** using kebab-case naming:
   ```bash
   touch ~/.claude/commands/[namespace]/[command-name].md
   ```

3. **Use standard template**:
   ```markdown
   ---
   title: Command Title
   description: Brief description (1-2 sentences)
   ---

   # [Purpose/Goal]

   [Detailed instructions for Claude]

   ## Agent Usage (if applicable)

   This command uses the `[agent-name]` agent to accomplish [task].
   ```

### Before Creating a New Command - Checklist

- [ ] Have I checked if an existing command could handle this?
- [ ] Is this functionality distinct enough to warrant a separate command?
- [ ] Have I chosen the correct namespace?
- [ ] Does my command name follow kebab-case conventions?
- [ ] Is the command name concise but descriptive?
- [ ] Have I documented which agent (if any) the command uses?

## Project-Specific Commands

For project-specific commands (like database schema review or project docs), those go in `.claude/commands/` within each repository.