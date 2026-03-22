---
name: root-cause-analysis
description: Systematic investigation of errors, failures, and unexpected behaviors by searching personal-wiki history and external documentation. Use when debugging errors with stack traces, investigating incidents/outages, finding historical context for similar issues, analyzing recurring problems, or searching for past solutions. Combines Logseq knowledge base (journals, pages, incident notes) with web search for external docs. Follows structured methodology to extract error signatures, search historical context, identify patterns, and determine root cause.
---

# Root Cause Analysis

Systematic investigation of errors and failures using historical wiki knowledge and external documentation.

## When to Use This Skill

**Use for:**
- Debugging errors with stack traces or error messages
- Investigating incidents or outages
- Finding historical context for similar issues in personal-wiki
- Analyzing recurring problems across time
- Searching for past solutions or workarounds

**Don't use for:**
- Simple syntax errors (use direct debugging)
- Issues without error context (use exploratory debugging)
- Real-time incident response (use incident management workflows)

## Core Investigation Workflow

### Phase 1: Extract Error Signature

Before searching, extract the searchable error signature:

```
Error Signature Components:
1. Error type/class: NullPointerException, ConnectionRefused, OOMKilled
2. Error message (first line, sanitized)
3. Key stack frame: Class.method or function name
4. Service/component name
5. Error code (if present): HTTP 503, Exit code 137, SQLSTATE 42P01
```

**Quick Extraction Pattern:**
```
Given: "java.lang.NullPointerException: Cannot invoke method on null at com.example.UserService.getUser(UserService.java:42)"

Extract:
- Type: NullPointerException
- Location: UserService.getUser
- Searchable: "NullPointerException UserService" OR "getUser null"
```

### Phase 2: Search Historical Context (Wiki)

Search Logseq for historical occurrences and solutions:

**Search Locations:**
| Location | Pattern | Purpose |
|----------|---------|---------|
| Journals | `~/Documents/personal-wiki/logseq/journals/YYYY_MM_DD.md` | Time-based incident notes, daily debugging sessions |
| Pages | `~/Documents/personal-wiki/logseq/pages/*.md` | Zettelkasten notes on technologies, services, incidents |
| Incident pages | Pages with "Incident" or service names | Documented post-mortems, solutions |

**Recommended Search Strategy:**

```bash
# 1. Search for exact error message (escaped)
Grep pattern="NullPointerException" path="~/Documents/personal-wiki/logseq/"

# 2. Search for service/component name
Grep pattern="UserService" path="~/Documents/personal-wiki/logseq/pages"

# 3. Search for related technology + problem
Grep pattern="Java.*null|null.*pointer" path="~/Documents/personal-wiki/logseq/" -i

# 4. Search incident-related tags
Grep pattern="#\\[\\[incident\\]\\]|#\\[\\[debugging\\]\\]" path="~/Documents/personal-wiki/logseq/"
```

**Glob for Recent Context:**
```bash
# Recent journals (last 30 days likely most relevant)
Glob pattern="~/Documents/personal-wiki/logseq/journals/2026_01_*.md"

# Technology-specific pages
Glob pattern="~/Documents/personal-wiki/logseq/pages/*Java*.md"
Glob pattern="~/Documents/personal-wiki/logseq/pages/*Kubernetes*.md"
```

### Phase 3: Search External Documentation

After exhausting wiki knowledge, search externally for solutions.

**CRITICAL: Sanitize Before Web Search**

Remove from search queries:
- API keys, tokens, passwords
- Internal hostnames and IPs
- Customer/user identifiers
- Proprietary function/class names
- AWS account IDs, database names

**Safe to Search:**
- Open source library names and versions
- Public error codes and messages
- Technology names (Kubernetes, PostgreSQL, Java)
- Generic error patterns

**Search Strategy:**
```
1. [Technology] + [Error Type] + "root cause"
2. [Library Name] + [Error Message] + [Version]
3. [Error Code] + "fix" OR "solution"
4. GitHub issues: "[repo] [error message]"
5. Stack Overflow: "[technology] [error type]"
```

### Phase 4: Correlate Evidence

Cross-reference findings from wiki and external sources:

**Correlation Checklist:**
- [ ] Same error signature in wiki history?
- [ ] Same root cause identified before?
- [ ] Different root cause, same symptoms?
- [ ] External docs confirm wiki hypothesis?
- [ ] Version/environment differences?

**Pattern Recognition:**
```
If found in wiki:
  - Check if previous solution still applies
  - Note any environment differences
  - Check if underlying issue was truly fixed

If found externally:
  - Validate against local environment
  - Check version compatibility
  - Note any prerequisites
```

### Phase 5: Document Root Cause

Structure findings for clarity:

```markdown
## Root Cause Analysis: [Brief Title]

### Error Signature
- Type: [Error class/type]
- Message: [Sanitized error message]
- Location: [Service/function]

### Historical Context
- Previous occurrences: [Wiki references with dates]
- Related incidents: [Links to incident pages]

### Root Cause
[Clear explanation of why the error occurred]

### Evidence
1. [Evidence point 1 with source]
2. [Evidence point 2 with source]

### Resolution
- Immediate fix: [Action taken]
- Long-term solution: [If different]
- Prevention: [How to avoid recurrence]

### References
- Wiki: [[Related Page]]
- External: [URL]
```

## Quick Reference

### Error Type to Search Strategy

| Error Type | Wiki Search | External Search |
|------------|-------------|-----------------|
| NullPointer/TypeError | Service name + "null" | [Lang] null pointer best practices |
| Connection refused | Service + "connection" + port | [Service] connection refused [port] |
| OOMKilled/OutOfMemory | Service + "memory" OR "OOM" | [Tech] memory leak diagnosis |
| Timeout | Service + "timeout" + dependency | [Tech] timeout configuration |
| Permission denied | Service + "permission" OR "auth" | [Tech] permission denied [context] |
| Database deadlock | "deadlock" + table/service | [DB] deadlock detection [version] |

### Logseq Search Patterns

```bash
# Find incident-related content
Grep pattern="incident|outage|postmortem" path="~/Documents/personal-wiki/logseq/pages" -i

# Find debugging sessions in journals
Grep pattern="debugging|troubleshoot|root cause" path="~/Documents/personal-wiki/logseq/journals" -i

# Find technology-specific notes
Grep pattern="\\[\\[Kubernetes\\]\\]|\\[\\[Java\\]\\]" path="~/Documents/personal-wiki/logseq/"

# Find error patterns
Grep pattern="Exception|Error|Failed|Timeout" path="~/Documents/personal-wiki/logseq/" output_mode="content" -C 3
```

### Time-Based Journal Search

Recent issues are often most relevant:

```bash
# This month's journals
Glob pattern="~/Documents/personal-wiki/logseq/journals/2026_01_*.md"

# Specific date range (incident period)
Glob pattern="~/Documents/personal-wiki/logseq/journals/2026_01_{20..28}.md"
```

## Security Boundaries

### Safe for Wiki Search (Internal)
- Full error messages with stack traces
- Internal service names
- Database table names
- Internal URLs and IPs
- Customer-specific identifiers

### Requires Sanitization for Web Search
| Category | Example | Sanitize To |
|----------|---------|-------------|
| API Keys | `Authorization: Bearer sk-abc123...` | `[REDACTED]` |
| Internal URLs | `https://internal.company.com/api` | `[internal endpoint]` |
| Customer IDs | `user_id: 12345678` | `[user identifier]` |
| AWS Resources | `arn:aws:iam::123456789012:role/MyRole` | `[AWS role ARN]` |
| DB Connections | `jdbc:postgresql://db.internal:5432/prod` | `postgresql connection` |

### Never Search Externally
- Production credentials
- Customer PII
- Internal architecture details
- Proprietary algorithm names
- Security vulnerability details (until patched)

## Progressive Context

- For technology-specific error patterns: see `references/error-patterns.md`
- For advanced wiki search strategies: see `references/search-strategies.md`
- For detailed sanitization rules: see `references/sanitization-rules.md`
