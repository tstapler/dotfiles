# Tool Access Tiers

This guide standardizes tool access patterns for agents to optimize context efficiency and enforce appropriate boundaries.

## Why Tool Restrictions Matter

### Context Efficiency
- Fewer tools = faster agent invocation
- Restricted tools = natural scope limiting
- Clear boundaries prevent scope creep

### Security & Safety
- Prevents unintended side effects
- Limits blast radius of errors
- Enforces principle of least privilege

### Focus
- Agents stay in their domain
- Tool availability guides behavior
- Reduces decision fatigue

## Tier Definitions

### Tier 1: Read-Only Analysis
**Tools**: `Read, Grep, Glob`

**Use Cases**:
- Code analysis without modification
- Documentation review
- Pattern discovery
- Codebase exploration

**Example Agents**:
```yaml
# Hypothetical read-only reviewer
tools: [Read, Grep, Glob]
```

**Characteristics**:
- Cannot modify files
- Cannot execute commands
- Pure analysis focus
- Minimal context load

---

### Tier 2: Read-Write Filesystem
**Tools**: `Read, Write, Edit, MultiEdit, Grep, Glob`

**Use Cases**:
- Code generation
- Documentation updates
- Refactoring
- File creation/modification

**Example Agents**:
```yaml
prompt-engineering:
  tools: [Read, Write, Edit, Glob, Grep, TodoWrite]
```

**Characteristics**:
- Can modify files
- Cannot execute shell commands
- Cannot make network requests
- Focused on code/docs

---

### Tier 3: Filesystem + Execution
**Tools**: `Read, Write, Edit, MultiEdit, Grep, Glob, Bash`

**Use Cases**:
- Testing and validation
- Build operations
- Git operations
- Deployment tasks

**Example Agents**:
```yaml
code-refactoring:
  tools: [Read, Edit, MultiEdit, Write, Bash, Grep, Glob, TodoWrite]
```

**Characteristics**:
- Can run shell commands
- Can modify and validate
- Build/test integration
- Higher risk operations

---

### Tier 4: Research + Filesystem
**Tools**: `Read, Write, Edit, Grep, Glob, WebFetch, mcp__brave-search__*, mcp__read-website-fast__*`

**Use Cases**:
- External research
- Documentation synthesis
- Best practices lookup
- API documentation fetching

**Example Agents**:
```yaml
software-planner:
  tools: [TodoWrite, Read, Grep, Glob, Bash, WebFetch, mcp__brave-search__brave_web_search, mcp__read-website-fast__read_website]
```

**Characteristics**:
- Can fetch external content
- Research-oriented
- Knowledge integration
- Planning focused

---

### Tier 5: Full Integration
**Tools**: `*` (all available tools)

**Use Cases**:
- End-to-end feature implementation
- Complex multi-phase workflows
- Cross-system integration
- Emergency debugging

**Example Agents**:
```yaml
feature-implementation:
  tools: *
```

**Characteristics**:
- Maximum flexibility
- Highest context overhead
- Use sparingly
- Reserved for orchestration agents

---

### Tier 6: MCP-Heavy Integration
**Tools**: Filesystem + specific MCP servers

**Use Cases**:
- Platform-specific operations (GitHub, Jira, etc.)
- External service integration
- API interactions

**Example Agents**:
```yaml
jira-project-manager:
  tools: [mcp__atlassian__*, TodoWrite, Read, Write, Edit]

pr-reviewer:
  tools: [Read, Grep, Glob, MultiEdit, Edit, mcp__github__*]
```

**Characteristics**:
- Platform-specific access
- API-driven workflows
- External service coordination

## Tool Categories Reference

### Filesystem Tools
| Tool | Purpose | Risk Level |
|------|---------|------------|
| `Read` | Read file contents | Low |
| `Write` | Create/overwrite files | Medium |
| `Edit` | Modify existing files | Medium |
| `MultiEdit` | Batch file modifications | Medium |
| `Glob` | Find files by pattern | Low |
| `Grep` | Search file contents | Low |

### Execution Tools
| Tool | Purpose | Risk Level |
|------|---------|------------|
| `Bash` | Run shell commands | High |
| `Task` | Spawn sub-agents | Medium |
| `TodoWrite` | Track tasks | Low |

### Network Tools
| Tool | Purpose | Risk Level |
|------|---------|------------|
| `WebFetch` | Fetch web content | Low |
| `mcp__brave-search__*` | Web search | Low |
| `mcp__read-website-fast__*` | Fast web reading | Low |

### MCP Integration Tools
| Tool | Purpose | Risk Level |
|------|---------|------------|
| `mcp__github__*` | GitHub operations | Medium |
| `mcp__atlassian__*` | Jira/Confluence | Medium |
| `mcp__datadog__*` | Monitoring/observability | Low |
| `mcp__playwright__*` | Browser automation | Medium |

## Tier Selection Decision Tree

```
Does the agent need to MODIFY files?
├── NO → Does it need EXTERNAL research?
│   ├── YES → Tier 4 (Research)
│   └── NO → Tier 1 (Read-Only)
└── YES → Does it need to RUN commands?
    ├── NO → Tier 2 (Read-Write)
    └── YES → Does it need EXTERNAL APIs?
        ├── NO → Tier 3 (Filesystem + Execution)
        └── YES → Does it need MULTIPLE MCP servers?
            ├── NO → Tier 6 (MCP-Heavy)
            └── YES → Tier 5 (Full Integration)
```

## Current Agent Tier Assignments

### Tier 2: Read-Write Filesystem
```yaml
- prompt-engineering: [Read, Write, Edit, Glob, Grep, TodoWrite]
```

### Tier 3: Filesystem + Execution
```yaml
- code-refactoring: [Read, Edit, MultiEdit, Write, Bash, Grep, Glob, TodoWrite]
- postgres-optimizer: [Read, Grep, Glob, Bash, Write, Edit]
```

### Tier 4: Research + Filesystem
```yaml
- software-planner: [TodoWrite, Read, Grep, Glob, Bash, WebFetch, brave-search, read-website]
- expert-writer: [Read, Write, Edit, Glob, Grep, WebFetch, brave-search]
- ux-expert: [Read, Write, Edit, Glob, Grep, WebFetch, brave-search, read-website, TodoWrite]
- knowledge-synthesis: [WebFetch, read-website, brave-search, Read, Write, Edit, MultiEdit, Glob, Grep, Task, TodoWrite]
```

### Tier 5: Full Integration
```yaml
- feature-implementation: *
- golang-test-debugger: *
- java-test-debugger: *
- spring-boot-testing: *
- log-parser-debugger: *
- github-debugger: *
```

### Tier 6: MCP-Heavy
```yaml
- jira-project-manager: [mcp__atlassian__*, TodoWrite, Read, Write, Edit]
- pr-reviewer: [Read, Grep, Glob, MultiEdit, Edit, mcp__github__*, mcp__brave-search__*]
- jj-stacked-pr: [Bash, Read, Write, Edit, Glob, Grep, TodoWrite, mcp__github__*]
- pr-description-generator: [Read, Bash, Grep, Glob, mcp__github__*]
```

## Optimization Opportunities

### Agents That Could Be Downgraded

```yaml
# Currently Tier 5, could be Tier 3:
golang-test-debugger:
  current: *
  proposed: [Read, Write, Edit, Bash, Grep, Glob, TodoWrite]
  reason: Doesn't need web fetch or MCP tools for test debugging

java-test-debugger:
  current: *
  proposed: [Read, Write, Edit, Bash, Grep, Glob, TodoWrite]
  reason: Focused on local test execution

log-parser-debugger:
  current: *
  proposed: [Read, Bash, Grep, Glob, TodoWrite]
  reason: Log analysis is primarily read + shell operations
```

### Adding Tools Judiciously

When an agent needs additional tools:
1. Start with the minimum tier
2. Add specific tools as needed
3. Document why each tool is required
4. Prefer explicit lists over `*`

## Context Management Benefits

### Fewer Tools = Faster Context
```
Tier 1 (3 tools):  ~200 tokens overhead
Tier 3 (7 tools):  ~500 tokens overhead
Tier 5 (all):      ~2000+ tokens overhead
```

### Explicit > Wildcard
```yaml
# Prefer this:
tools: [Read, Write, Edit, Bash, Grep, Glob]

# Over this:
tools: *
```

### MCP Tools Are Heavy
```
Each MCP server adds ~500-1000 tokens of schema
Only include MCP tools when specifically needed
```

## Best Practices

1. **Start Restrictive**: Begin with Tier 1-2, escalate as needed
2. **Document Rationale**: Explain why each tool is necessary
3. **Review Periodically**: Audit tool usage and downgrade if possible
4. **Explicit Lists**: Avoid `*` unless truly needed for orchestration
5. **MCP Minimalism**: Only include MCP servers actively used
