---
description: Check whether a piece of writing's actual register matches its declared audience and tone (from writing:scope). One check in the writing pipeline — run standalone or via writing:full.
---

# writing:tone

Prose can pass every structure/readability/humanize check and still be wrong for its reader — too formal for a Slack-adjacent PR description, too casual for a decision document a VP will act on, or written for domain experts when the actual audience is cross-functional. This check is the one that catches *mismatch*, not quality in isolation.

**Target**: {{args}} — a file path, or text already in context. **Requires** the scope from `writing:scope`: `{audience, tone, doc_type, purpose}`. If invoked standalone without a scope, run `writing:scope`'s Step 1 detection first and state your inferred scope before proceeding — don't guess silently.

## What to check

Given the declared `{audience, tone}`, scan for mismatches:

- **Register mismatch** — tone reads more formal/dense than declared (jargon-per-sentence, passive constructions, hedge-heavy) when `tone` was declared "direct/conversational" or "match my own voice"; or too casual (contractions, unexplained shorthand) when `tone` was declared "formal/decision-document".
- **Audience mismatch** — undefined jargon/acronyms on first use when `audience` is "cross-functional" or "external"; over-explained basics that waste an expert reader's time when `audience` is "expert peers."
- **Purpose drift** — the text spends effort on something the stated `purpose` doesn't need (e.g., a PR description narrating implementation history when its purpose is "get this reviewed and merged," not "document how I got here" — that content belongs in a commit message or the PR's own history, not the description a reviewer reads first).
- **Voice drift** (only when `tone` is "match my own voice") — passages that read like generic AI output rather than the author's established cadence. Don't re-run the full `writing-humanize` audit here; just flag *where* voice drift is worst so that skill's fixes land in the right spots.

## What NOT to flag

- Formality that the *doc type* requires regardless of general "readability" preferences — a design doc's evidence citations, a legal notice's precise phrasing. Register and rigor are different axes; don't flag rigor as a tone problem.
- A single instance of jargon that the doc itself defines inline right after first use — that's handling the audience gap correctly, not failing to.

## Severity

| Severity | Meaning |
|---|---|
| `blocking` | The mismatch is doc-wide — the whole piece is pitched at the wrong audience or register, not a few passages |
| `notable` | Localized passages drift from the declared tone/audience with a clear fix |
| `nit` | A single word/phrase choice, batch these |

## Output

```json
{
  "category": "tone",
  "status": "pass" | "fail",
  "scope": {"audience": "...", "tone": "...", "doc_type": "..."},
  "count": <number of blocking+notable findings>,
  "findings": [
    {"section": "...", "severity": "notable", "mismatch": "too-formal" | "too-casual" | "undefined-jargon" | "over-explained" | "purpose-drift" | "voice-drift", "note": "one line: what's wrong + the fix direction"}
  ]
}
```

`status: "pass"` only if there are zero `blocking` findings and the doc-wide register matches the declared scope.

## When invoked standalone (not via the coordinator)

Print the findings with the declared scope restated at the top, then ask whether to apply the rewrites. Don't apply a tone rewrite that would also require re-running `writing-humanize` or `design-doc-review:readability` findings first if those haven't been checked yet — tone fixes on top of unfixed structural/readability issues just rewrite the same passage twice.
