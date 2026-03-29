# Skill: stapler-squad-rules

Use this skill when working in the claude-squad/stapler-squad repo and you need to:
- Review the approval analytics to understand what Claude is doing
- Identify gaps in the rules engine (commands not covered by any rule)
- Decide whether to add, modify, or retire an auto-approval rule
- Investigate why a session is generating lots of manual review requests

## How to access the analytics

Navigate to **http://localhost:8543/rules** in your browser (the server must be running — `make restart-web` if not).

The page has two panels:
1. **Approval Rules Panel** (top) — shows all active rules with their trigger counts
2. **Approval Analytics Panel** (bottom) — time-series data, coverage gaps, program breakdowns

Use the **7 / 14 / 30 / 90 day** window selector to change the time range.

---

## Reading the analytics to find new rules

### 1. Rule Coverage Gaps section

This is the most important section for finding missing rules. It appears at the bottom of the analytics panel when any decisions went unmatched.

- **Gap rate** — what percentage of decisions had no matching rule and fell through to manual review by default. Above 30% is high; below 10% is good.
- **Uncovered Tools** — Claude Code tool types (Bash, Write, Edit, etc.) that are frequently escalating without a rule match.
- **Uncovered Bash Programs** — specific executables (git, npm, docker, etc.) whose commands frequently escape all rules.

**Action**: For each row in these tables, click "Add rule →" to open the rules editor. Then:
- If the program is consistently safe in your workflow → add an **auto-allow** rule
- If the program is consistently risky → add an **auto-deny** rule
- If it depends on the specific command → add a **command pattern** rule

### 2. Top Triggered Rules

Shows which rules fire most often. Useful for:
- Verifying that important rules are actually being used (not stale)
- Finding rules that fire so often they might need sub-rules for finer control
- Identifying if the default escalate path is larger than expected

### 3. Top Tools

Shows which Claude Code tools are most active overall. If a tool like `Bash` is dominant but has a high coverage gap rate, it means the existing Bash rules are too narrow.

### 4. Top Bash Programs

Shows which executables Claude uses most via the `Bash` tool. If a program appears here but NOT in the "Uncovered Programs" list, it means an existing rule is already handling it — good. If it appears in both, it needs a rule.

### 5. Top Python Imports

Shows Python modules imported in inline `-c` invocations. High use of `requests`, `urllib`, or `httpx` suggests Claude is making HTTP calls from Python — worth adding a rule if you want to review those.

---

## Deciding what rules to add

Use this checklist when looking at the coverage gap data:

```
□ What tool is unmatched? (Bash, Write, Edit, Read, etc.)
□ If Bash: what program? (git, npm, curl, docker, …)
□ Is this program category safe in my workflow? (vcs=usually safe, network=review)
□ What subcommands are most common? (git commit vs git push have different risk)
□ Is there a pattern in the command text I can use? (regex on command field)
□ Should this be auto-allow, auto-deny, or explicit escalate?
```

**Safe patterns to auto-allow:**
- Read-only VCS commands: `git status`, `git log`, `git diff`
- Package-manager info queries: `npm list`, `pip show`
- Build commands that don't touch secrets or deploy: `go build`, `cargo build`
- Test runners that don't require network: `go test`, `pytest ./...`

**Patterns to auto-deny:**
- Commands writing to `.env` or credential files
- `rm -rf` on non-tmp paths
- `curl` / `wget` piped to `sh` or `bash` (supply chain risk)
- Commands containing secrets (handled automatically by the secret scanner)

**Patterns to escalate (explicit):**
- `git push` (changes remote state)
- `npm publish`, `cargo publish` (deploys packages)
- Any cloud CLI deploy commands (`kubectl apply`, `terraform apply`)

---

## How to create a rule

1. Go to **http://localhost:8543/rules**
2. Scroll to the **Add Custom Rule** form at the bottom of the Rules panel
3. Fill in:
   - **Name** — descriptive, e.g. "Allow go test"
   - **Decision** — auto_allow / auto_deny / escalate
   - **Tool Name** — exact tool name, e.g. `Bash` (case-sensitive)
   - **Command Pattern** — regex on the full command text, e.g. `^go\s+test\b`
   - **Reason** — explain why this rule exists (shown to Claude on deny)
   - **Alternative** — (optional) suggest what Claude should do instead
   - **Priority** — higher number = evaluated first (seed rules are at 1000/100/50)
4. Click **Save Rule**

Rules take effect immediately without a restart.

---

## Rule pattern tips

```
# Match a specific program exactly (starts with):
^git\s

# Match git read-only subcommands:
^git\s+(status|log|diff|show|branch|remote|describe)\b

# Match any npm install variant:
^npm\s+(install|i|ci)\b

# Match curl/wget downloads to disk:
^(curl|wget)\s+.*\s+-[oO]

# Match python -c with requests import (network calls):
^python3?\s+-c\s+.*\bimport\s+requests\b

# Deny writes to credential files:
\.(env|pem|key|p12|pfx|credentials)$
```

---

## Keeping rules evergreen

Review the analytics weekly or after major changes to your workflow:

1. **Check top uncovered programs** — new tools Claude is using that need rules
2. **Check stale rules** — rules in the Rules panel that haven't triggered recently may be too specific or no longer needed
3. **Check manual review rate trend** — if it's rising, you have new patterns to cover; if it's stable and low, rules are healthy
4. **After adding a new Claude skill or tool** — Claude may start using new programs; check the analytics a day later

---

## Backend files (for code changes)

| File | Purpose |
|------|---------|
| `server/services/classifier.go` | Rule matching engine + seed rules |
| `server/services/rules_service.go` | RPC handlers + proto mapping |
| `server/services/analytics_store.go` | JSONL analytics storage + aggregation |
| `server/services/approval_handler.go` | HTTP hook handler + secret scanner + domain checker |
| `server/services/secret_scanner.go` | Regex patterns for plaintext secret detection |
| `server/services/domain_checker.go` | RDAP-based new-domain escalation |
| `server/services/command_parser.go` | Bash AST parser + Python import extractor |
| `proto/session/v1/types.proto` | Proto definitions (run `make proto-gen` after changes) |
| `web-app/src/components/sessions/ApprovalAnalyticsPanel.tsx` | Analytics UI |
| `web-app/src/components/sessions/ApprovalRulesPanel.tsx` | Rules management UI |