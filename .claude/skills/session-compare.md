---
name: session-compare
description: Compare two Claude Code sessions by path or name. Extracts duration, model, all token buckets, estimated cost, human turns, tool calls, files touched, and generates a markdown conversation summary. CLI wrapper around ~/dotfiles/stapler-scripts/session-compare.
---

# Session Comparison

Compare two Claude Code sessions and produce a structured markdown report.

## When to use

- Evaluating different approaches (quick vs MDD, two prompt strategies, two models)
- Estimating cost difference between workflows
- Creating demo artifacts that show session metrics side-by-side
- Post-session retrospectives: "what did each approach actually cost?"

## How it works

The `session-compare` CLI parses `.jsonl` transcripts stored under `~/.claude/projects/` and outputs:

- Side-by-side metric table (duration, model, all 4 token buckets, cost)
- Per-session cost breakdown table
- Files touched (union, with per-session checkmarks)
- Full conversation summaries (user + assistant text, tool call annotations) — human-readable markdown, not raw JSONL

## Invocation

```bash
# By full .jsonl path
session-compare /path/to/session1.jsonl /path/to/session2.jsonl

# By project directory (picks newest .jsonl)
session-compare ~/.claude/projects/-Users-me-project-a ~/.claude/projects/-Users-me-project-b

# Fuzzy match on project dir name (partial string)
session-compare swift-hawk warm-spruce

# With custom labels and output file
session-compare path1 path2 --label1 "Quick approach" --label2 "MDD approach" --output report.md
```

## Instructions

1. Identify both session paths. Ask the user if not clear from context. Common locations:
   - `~/.claude/projects/<escaped-path>/<uuid>.jsonl`
   - Or the project directory containing the `.jsonl`

2. Run the CLI:

```bash
session-compare <session1> <session2> --label1 "<name1>" --label2 "<name2>" --output /tmp/session-comparison.md
```

3. Read the output and present the metrics table to the user inline.

4. If the user wants the report saved to a project location, copy `/tmp/session-comparison.md` to the appropriate path.

## CLI reference

```
session-compare <session1> <session2> [options]

Arguments:
  session1, session2   .jsonl file, project directory, or partial project name

Options:
  --output <file>      Write to file instead of stdout
  --label1 <name>      Label for session 1 (default: filename stem)
  --label2 <name>      Label for session 2 (default: filename stem)
```

## Pricing model (claude-sonnet-4-6, baked in)

| Bucket      | $/MTok |
|-------------|--------|
| Input       | $3.00  |
| Cache read  | $0.30  |
| Cache write | $3.75  |
| Output      | $15.00 |

Opus 4.7 and Haiku 4.5 pricing is also baked in — model auto-detected from transcript.

## Example output (abbreviated)

```markdown
# Session Comparison: quick vs mdd

| | quick | mdd |
|---|---|---|
| Duration | 9m 50s | 57m 05s |
| Model | claude-sonnet-4-6 | claude-sonnet-4-6 |
| Human turns | 4 | 57 |
| Output tokens | 4.7K | 24.8K |
| Cache read tokens | 401K | 5,891K |
| Estimated cost | $0.19 | $2.16 |
| Cost ratio | — | 11.4x |
```
