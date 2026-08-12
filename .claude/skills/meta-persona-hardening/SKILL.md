---
name: meta-persona-hardening
description: >-
  Harden an agent's persona/system-prompt file (SOUL.md-style: a git-tracked
  identity + process-gate document) against a concrete recurring failure, instead
  of doing a vague "improve the persona" pass. Mines a real incident, converts
  judgment-based process gates into low-judgment triggers, verifies every
  skill/resource name the persona references against what actually exists on
  disk, adds a cheap inline check reachable mid-edit, and adds a reuse check
  targeted at the mined failure. Language- and domain-agnostic — works for any
  persona file and any stack (Go, Python, TypeScript, ...), not just one agent.
when_to_use: "Improve/audit an agent's persona or system-prompt file after a real quality incident; add process gates to a persona file; verify skill references in a persona/SKILL.md are real; convert a subjective 'is this non-trivial' gate into concrete triggers"
---

# Persona Hardening

Personas drift the same way any long-lived document does: gates get written as
subjective judgment calls ("if this feels important, do X") because that was
true when written, references to other files/skills go stale as the ecosystem
around them changes, and expensive audit techniques get added once and never
wired into ordinary work. This skill is the repeatable procedure for closing
that gap, driven by one real failure at a time — not a general "make the
persona better" sweep.

**Precondition**: don't run this speculatively. It needs a real failure to
anchor to (Step 1) — hardening a persona against a hypothetical problem
produces vague, unfalsifiable gates nobody can verify caught anything.

## Step 1 — Mine a Concrete, Real Failure

Vibes ("the agent's output quality feels off") don't produce an actionable
gate. A specific, verifiable incident does. Look for a **repeated-fix
pattern** — the same category of bug independently reimplemented or the same
review comment posted more than once across a PR's revision history.

```bash
# GitHub: pull all review comments on a PR and look for repeats across commits
gh pr view <PR> --json reviews,comments --jq '.reviews[].body, .comments[].body'
gh api repos/<org>/<repo>/pulls/<PR>/comments --jq '.[] | "\(.path):\(.line) \(.body)"'

# Grep commit history for "fix" commits that touch the same function/file more than once
# in a short window — a same-symbol fix repeated 2+ times is a strong candidate
git log --oneline --all -- <suspect-file> | head -30
git log -p --follow -- <suspect-file> | grep -B5 'func \|def \|function ' | less

# jj colocated repos: same idea via jj log
jj log -r 'files(<suspect-file>)' --limit 30
```

If session/PR history isn't available or doesn't surface anything (a new
agent, a private workspace with no PR trail), **ask the user for one concrete
incident** rather than inventing a generic principle. A single named example
("PR #479, the same check-then-mutate ordering bug reimplemented across three
sibling functions, caught only after 5 review rounds") is worth more than ten
abstract bullet points — it's what step 3/5 below get built against, and
it's the thing you cite later when explaining why a new gate exists.

Write the incident down in one or two sentences: **what broke, how many times
it recurred, and how it was ultimately caught.** That sentence is the spec
for every later step — if a proposed gate wouldn't have caught it, keep
looking for a better gate, don't ship a plausible-sounding one anyway.

## Step 2 — Read the Persona and Flag Judgment-Based Gates

Read the full persona/system-prompt file (e.g. `SOUL.md`, `AGENTS.md`,
`CLAUDE.md`, a system-prompt config). Grep it for the words that mark a
judgment call rather than a concrete condition:

```bash
grep -niE 'non-trivial|if (this|it) (feels|seems)|use (your )?judg?ment|when appropriate|as needed|significant|major (change|feature)|complex enough' <persona-file>
```

For each hit, ask: **which failure mode from Step 1 was this gate supposed to
catch, and why didn't it?** Usually the answer is that the gate delegates the
"should I stop and check" decision entirely to the agent's own in-the-moment
judgment, with no external signal forcing the check regardless of how the
agent feels about the change. Record each hit as `<line/section> — gate text
— what it should have caught but didn't`. This list is the direct input to
Step 4.

Don't stop at the first vague phrase found — a persona file typically has one
judgment gate per workflow decision point (when to plan first, when to write
tests first, when to ask for review); check each one against Step 1's
incident, not just the one that superficially matches.

## Step 3 — Audit Every Referenced Skill/Resource Name Against Disk

Persona files reference skills, scripts, or docs by name, and those names go
stale independent of the persona's content review. Treat every reference as
unverified until checked, in both directions:

```bash
# 1. Extract every skill-shaped reference from the persona file
grep -noE '`[a-z][a-z0-9-]+`' <persona-file> | sort -u

# 2. Get ground truth
ls ~/dotfiles/.claude/skills/            # or wherever this agent's skill set actually lives
# or, if the persona is for a different tool: check its own skill/plugin registry directly

# 3. Diff the two lists by hand — every reference must resolve to a real,
#    non-empty entry (check it's not an empty directory / stub)
```

**The two-round trap** (hit for real doing this on Aimee's `SOUL.md`): a
first correction can itself introduce a *new* wrong assumption. The initial
pass found `go-development`/`go-concurrency` referenced but missing, "fixed"
it to `golang-development`/`golang-concurrency` — and in the same pass
*assumed*, without checking, that `golang-development` and
`golang-concurrency` didn't exist yet either. Only a later, independent `ls`
of the skills directory revealed they were real, populated skills all along.
The lesson generalizes: **a plausible-sounding rename is still a guess until
verified by listing the real directory** — "this name looks more standard"
is not evidence.

Because of that trap, this step is not done after one correction pass.
**Explicit final gate**: after making any renames, re-run the `ls`/grep pair
above one more time, from scratch, against the edited file — not from memory
of what you just decided — and confirm every remaining reference resolves.
Do this even (especially) when you're confident the first pass was
already correct.

This same staleness pattern recurs **inside skill files themselves**, not
just personas — a skill's own "Related Skills" table can reference a skill by
a name that was never correct, or that changed since the table was written.
Run the same `grep`-refs-then-`ls`-ground-truth check on any skill file you
edit as part of this process, not only on the persona file.

## Step 4 — Convert Judgment Gates into Concrete Triggers

For each flagged gate from Step 2, replace "is this non-trivial" with an
explicit, checkable list of conditions — OR'd together, evaluated
mechanically, not felt out:

- Touching a file already known to be complex/high-churn (wire this to
  `code-hotspot-analysis`'s inline spot-check — see Step 5)
- Touching N or more files in one change (pick N from the team's own norms;
  3 is a reasonable default for "coordination risk starts here")
- Introducing a new package/service/module boundary
- Writing logic that resembles something that already exists elsewhere in
  the codebase (this is the direct trigger for Step 6's reuse check, and the
  one that would have caught the Step-1 incident if it existed already)

Example rewrite:

```diff
- If the change is non-trivial (new service, architecture decisions):
-   run the full spec-driven workflow.
+ Run the full spec-driven workflow if ANY of the following hold — don't rely
+ on a felt sense of "non-trivial":
+   - touches a file flagged by `code-hotspot-analysis`'s inline spot-check
+   - touches 3+ files
+   - introduces a new package/service/module boundary
+   - the logic being written resembles something that already exists
+     elsewhere (run the reuse check in `code-architecture-best-practices`
+     first — if it turns something up, this was never a "new logic" case)
```

Each condition must be mechanically checkable in under a minute — if a
condition itself requires judgment to evaluate, it hasn't actually replaced
the problem.

## Step 5 — Add a Cheap Inline Version of the Relevant Full-Audit Skill

A full audit technique (whole-codebase coupling/complexity analysis, a full
security sweep, a full architecture review) that only runs as a deliberate,
separately-invoked pass will never fire during ordinary edits — the agent has
no reason to reach for an expensive whole-codebase tool mid-task. Add a
30-second-or-less "Inline" subsection to that skill (not the persona file)
that:

- runs a narrow, single-file/single-function version of the same signal
  (e.g. `code-hotspot-analysis`'s Inline Spot-Check: `git log --oneline -20
  -- <file>` + `gocyclo <file>` instead of a whole-repo static+temporal
  coupling pass)
- states explicitly that it doesn't replace the full audit, only makes the
  signal reachable during normal work
- is the thing Step 4's concrete trigger actually points at, so the
  trigger has a real, fast check behind it instead of naming an audit nobody
  will run

This is a change to the **audit skill itself**, not the persona — the
persona's job (via Step 4) is just to force the moment where this check gets
invoked.

## Step 6 — Add a Reuse Check Targeted at the Mined Failure

If Step 1's incident was duplicated/reimplemented logic (the most common
shape — the same bug-prone pattern written more than once instead of
extracted once), add an explicit "search before you write" step to the
relevant architecture/style skill:

```markdown
## Reuse Check (Do This First)

Before writing new logic, search the codebase (`grep`/`ast-grep`) for an
existing function or pattern that already does something similar — reuse it
or extract a shared abstraction rather than reimplementing it per call site.
```

Scope this to the actual failure category found in Step 1 — if the incident
was an authz-ordering bug reimplemented across sibling functions, the reuse
check's example should say so, not stay generic. A generic "avoid
duplication" reminder is weaker than one that names the exact shape of bug
it exists to prevent.

## Step 7 — Final Verification Checklist

Do not call this done from a diff read alone. Run each of these explicitly:

1. **Re-grep every skill/resource reference** in every file touched
   (persona + any skill files) and **re-run `ls`/`Read` against the real
   directory** one more time — this is Step 3's trap-catching gate, repeated
   as a final pass, not skipped because "I already checked once."
2. **Confirm existence, not just plausibility**, for anything renamed —
   open the target file/directory, don't just trust that the new name looks
   right.
3. **Re-read the diff for proportionality** — a one-sentence gate rewrite
   shouldn't balloon into a paragraph of justification; keep the persona
   file's voice and length consistent with the rest of the document.
4. **Review the actual `git diff`/`jj diff` of any identity/persona file
   touched** before calling the task done — these files are usually
   sensitive (they define how an agent presents itself) and deserve a full
   manual read of the diff, not a summary-level "looks fine."

```bash
git diff -- <persona-file>          # or: jj diff <persona-file>
git diff --stat                      # confirm no unintended files changed
```

Only after all four pass should this be reported as complete.

## Anti-Patterns

- **Hardening against a hypothetical.** If Step 1 didn't produce a real,
  named incident, stop and get one before writing any gate — a gate built on
  a guess about what might go wrong doesn't generalize and can't be tested
  against the thing that actually happened.
- **Trusting your own correction.** The Step 3 trap is specifically about
  this: a "fix" to a wrong reference is not verified until it's re-checked
  against a fresh `ls`, independent of the reasoning that produced the fix.
- **Making the concrete trigger just as vague as the judgment gate it
  replaced.** "Touching something complex" is not more concrete than
  "non-trivial" — the replacement needs an actual command or file list behind
  it (Step 4/5).
- **Skipping the persona diff review because the change looks small.**
  Small diffs to identity-defining files still deserve the full read — a
  one-line change to a process gate changes behavior on every future task,
  which is a bigger blast radius than the line count suggests.

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `code-hotspot-analysis` | The full-audit skill this process's Step 5 (inline spot-check) was built for — read its Inline Spot-Check section as the worked example |
| `code-architecture-best-practices` | The skill this process's Step 6 (reuse check) was added to — its "Reuse Check" section is the worked example |
| `meta-cross-reference` | Complementary skill-reference audit, but scoped to a `SKILL.md`'s own Related Skills table rather than a persona file's prose references |
| `code-review` | Where the mined incident (Step 1) is usually first visible, as repeated review comments across rounds |
| `code-root-cause-analysis` | If the Step 1 incident needs deeper investigation (stack traces, logs) before it can be stated as a one-sentence spec |
