---
description: Check a design doc for unsubstantiated claims, missing citations, and internal incoherence — does every factual statement have a source the reader can check, and does the doc's own logic hold together? One check in the design-doc-review pipeline — run standalone or via design-doc-review:review.
---

# design-doc-review:evidence

Claim-verification check only — this skill does not evaluate prose quality (see `design-doc-review:readability`) or topic coverage (see `design-doc-review:outline`). It answers: **is every factual claim in this doc backed by a source the reader can check, and does the doc's reasoning actually connect claim to conclusion?**

**Target**: {{args}} — a file path, or a doc already in context.

## Framework

This check mechanizes CLAUDE.md's own "Evidence and Claims" section — that section is the standard, this skill is the automated pass against it. Don't re-derive different rules; apply the ones already agreed:

- Every factual statement carries a source the reader can check — a PR/issue URL, `repo/path/file.ext:42`, a doc/dashboard URL, or the exact command and its output. Naming a source without a link pushes verification onto the reader — that's a finding, not a pass.
- Rationales ("why") are claims too, and are a common place to invent one — check them with the same rigor as facts.
- "Consistent with" is not "because of" — a causal claim needs the evidence to actually support causation, not mere correlation-in-time.
- Confidence should be labeled: VERIFIED (source opened / command run) vs. INFERRED/UNVERIFIED. A doc that states an inferred claim with the same confidence as a verified one is miscalibrated, not just imprecise.

### What to flag

- **Unsourced factual claim** — a specific, checkable assertion (a number, a behavior, "X does Y") with no link, file:line, or command output backing it. Bare assertions of fact are exactly what a fact-checker's "how do you know this?" test exists to catch — if the author can't point to where this came from, it shouldn't be stated as fact.
- **Source named but not linked** — "per the runbook" or "as Nick's doc says" without a URL. This is explicitly called out in CLAUDE.md: naming a source without a link is the same defect as no source, since it still pushes verification onto the reader.
- **Superlative or absolute without comparative proof** — "the fastest", "the only", "always", "never" stated as fact rather than rhetorical color. These require documentation of the comparison, not just assertion.
- **Confidence mismatch** — a claim phrased as settled fact when the doc's own evidence (or absence of it) only supports "probably" or "consistent with." Conversely, don't flag a claim correctly hedged as INFERRED/UNVERIFIED — that's precision, not a defect (see `design-doc-review:readability`'s hedged-language guardrail; the two checks should agree, not double-flag the same sentence from opposite directions).
- **Non-sequitur / unsupported causal leap** — the stated evidence doesn't actually get you to the stated conclusion (e.g., "latency dropped after the deploy, so the deploy fixed it" with no ruling-out of a concurrent cause). Flag the gap between what was shown and what was claimed.
- **Internal contradiction** — two statements in the same doc that can't both be true (a field described as "read-modify-write" in one section and "set-once" in another; a status marked "Not started" in one place and "in flight" in another). Cite both locations.
- **Stale or dangling citation** — a link, PR number, or file:line reference that plausibly no longer resolves (a PR referenced as "open" that other doc context suggests has since merged/closed, a line-number citation to a file that's been substantially rewritten elsewhere in the same review pass). Flag for re-verification; don't assume broken without checking if a check is feasible in this pass.

### What NOT to flag (proportionality guardrails)

- **Correctly hedged uncertainty** ("may indicate", "not verified", "consistent with X, though Y wasn't ruled out") — this is the doc doing its job, not a gap. Only flag hedging used to *avoid* a claim the author could have made concrete with evidence already in hand.
- **Claims that are definitional or self-evident within the doc's own stated model** — a term the doc itself defines two sections earlier doesn't need a citation every time it's used again.
- **Opinion/recommendation explicitly framed as judgment, not fact** — "we recommend X because it trades off Y for Z" is a reasoned position, not a factual claim requiring a citation, as long as the trade-off's factual inputs (Y, Z) are themselves sourced elsewhere in the doc.

### How to check a claim (verification depth, scaled to stakes)

1. **Does it have a link/path/command at all?** If not, that's the finding — don't chase down whether it's *true*, since it's already failing the "checkable" bar regardless.
2. **If it has one, does the link actually support the claim?** A relevant-looking link is not evidence if it doesn't substantiate the specific sentence attached to it — a citation to a whole file when the claim is about one method's behavior is weak sourcing, not fixed sourcing (though still better than nothing; note it as `notable`, not `blocking`).
3. **Weight by stakes, not count.** One unsupported claim underpinning the doc's actual decision outweighs several unsourced but low-consequence background details. A blocking finding is about a load-bearing claim; a nit is about an incidental one — don't let the count alone drive severity.

## Section-scoped invocation (long docs)

Like `design-doc-review:readability`, this check runs section-local on docs the coordinator has split by H2 for length. Internal-contradiction checking is the one sub-check that needs whole-doc awareness even when invoked per-section — the coordinator should additionally pass a short list of any other section's headline claims (one line each) so a per-section agent can catch a contradiction against a section it wasn't otherwise given. If that list isn't provided, skip the internal-contradiction check for this invocation and say so in the finding set (`"note": "internal-contradiction check skipped — no cross-section claim list provided"`), rather than silently passing.

## Severity

| Severity | Meaning |
|---|---|
| `blocking` | An unsourced or non-sequitur claim underpins the doc's actual decision/ask — a reviewer can't evaluate the ask without it |
| `notable` | Unsourced or weakly-sourced claim that isn't the decision itself, but materially supports a risk/consequence the doc asserts; internal contradiction found |
| `nit` | Missing citation on an incidental/background fact; batch these, don't report individually |

## Output

Write full analysis (the claim, why it fails, and the fix — a specific link/path/command to add, or a specific rewrite to correct scope) to `/tmp/lean-design-doc-review-evidence-<ts>.md`.

Return only this structured summary:

```json
{
  "category": "evidence",
  "status": "pass" | "fail",
  "count": <number of blocking+notable findings>,
  "findings": [
    {"section": "§3.2", "severity": "blocking", "claim": "one-line quote or paraphrase of the claim", "issue": "unsourced" | "source-named-not-linked" | "unsupported-superlative" | "confidence-mismatch" | "non-sequitur" | "internal-contradiction" | "stale-citation", "note": "what's missing and what would fix it"}
  ]
}
```

`status: "pass"` only if there are zero `blocking` findings. `notable`/`nit` findings can coexist with a `pass` status the same way `design-doc-review:readability` allows a non-blocking notable finding alongside an overall pass.

## When invoked standalone (not via the coordinator)

Print the summary as a table, one row per finding, with the claim, the issue type, and the specific fix (exact link/path to add, or exact rewrite). For `unsourced`/`source-named-not-linked` findings where you can locate the actual source in the repo or session context yourself (e.g. the claim clearly refers to a file you can find and cite precisely), propose the citation rather than just flagging the gap — but never invent a source or guess a plausible-looking link; if you can't verify it, say so and ask the author where it came from. Do not edit the file without confirmation.

## Related

- CLAUDE.md's "Evidence and Claims" section — the standard this check mechanizes; consult it directly for edge cases not covered above.
- `design-doc-review:readability`'s "Unquantified risk language" and hedged-language guardrail — adjacent checks; coordinate rather than double-flag the same sentence (readability asks "is this padded/imprecise", this check asks "is this actually sourced/coherent").
