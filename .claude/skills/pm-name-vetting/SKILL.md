---
description: "Generate candidate project names from researched themes (mythology, trade metaphors, foreign-language words, puns, jargon — mined via web research, thesauruses and sub-agent rounds, not model recall), then vet them for conflicts with existing software projects and return a clean shortlist. Use standalone or from a pm-brand-strategy session."
---
# Project Name Vetting

You are a naming researcher. Your job is to vet candidate project names for conflicts with existing software projects, then return a clean shortlist of names that are genuinely available — saving the user from falling in love with a name that's already taken.

This skill is typically invoked from within a `pm-brand-strategy` session, but can be run standalone on any list of names.

---

## Input

Names can come from:
1. **Explicit list** — user provides names to vet
2. **Brand context** — read `.claude/product-marketing-context.md` and extract the `name_candidates` section if present
3. **Inline brainstorm** — names generated during the current conversation

Always confirm the list before beginning: *"Vetting these N names: <list>. Starting searches now."*

**Default when no explicit list is given: run the Generation Protocol below first.** Do not fill the list from whatever names come to mind — model recall clusters on the same overused names (Atlas, Hermes, Forge, Nexus…). Candidates must come from researched sources.

---

## Generation Protocol (build the candidate list from research, not memory)

Read [naming-patterns.md](naming-patterns.md) first: it catalogues the naming patterns (mythology, trade-tool metaphor, descriptive, pun/portmanteau, foreign-language, jargon, geography, taxonomy, coinage, and more), with how to mine each. Run these rounds, using background sub-agents (general-purpose, one per theme, in a single parallel message) for rounds 2–3:

1. **Brief.** From the project's purpose, derive: what it does (verbs/nouns), who uses it, the feel (tool, craft, exploration…), and constraints (CLI-typeable, short, pronounceable). Write 5–8 **themes**, each tied to a pattern in `naming-patterns.md` (e.g. "surveyor's trade tools" = metaphor; "minor Greek deities of measure/boundary" = mythology; "Latin/Welsh words for 'to see/measure'" = foreign language; plus at least one pun/portmanteau theme and one descriptive-but-distinctive theme).
2. **Mine (web research, per theme).** Each sub-agent searches for source material — Wikipedia/Theoi/Perseus pantheon pages, Wiktionary/etymonline, trade glossaries, taxonomy and place-name lists — and records **raw terms with the source URL**. Minimum ~30 raw terms per theme. Prefer minor figures, epithets, and obscure-but-pronounceable terms over famous ones.
3. **Expand.** Run each promising term through related-word sources: Datamuse (`https://api.datamuse.com/words?ml=<meaning>`, `rel_trg=`, `sl=` for sounds-like), thesaurus sites, Wiktionary translations/derived terms, and a second sub-agent round per theme that explicitly avoids terms already seen. Cross-pollinate patterns (mythology × tool metaphor, jargon × affix coinage).
4. **Filter.** Drop terms that fail the criteria in `naming-patterns.md` (pronounceable, spellable, typeable, short, no bad meaning in major languages, not a household brand). Keep ≤ 20 finalists with the pattern and source recorded for each so the choice is explainable.
5. **Hand off** the finalists to the Search Protocol below.

Record the themes, raw-term sources, and finalists in the vetting output so the list is auditable.

---

## Search Protocol

For each candidate name, run **all four checks in parallel** using web search. Do not skip checks to save time — a name that passes three but fails one is still conflicted.

### Check 1: GitHub
Search: `"{name}" site:github.com`

Flag as **CONFLICTED** if:
- A repository with the **exact name** has >100 stars
- A popular org or widely-used tool uses the name as its primary identifier
- The name is already a GitHub org name for an active project

Flag as **AMBIGUOUS** if:
- Repos exist but are forks, archived, or <100 stars
- The name is used in a different technical domain (e.g., a name used for a Rust game engine that you're positioning as a Go CLI tool)

### Check 2: Package registries
Run the registries directly — WebSearch cannot query them. Where the CLIs exist: `npm view {name} name version`, `cargo search {name} --limit 3` (look for an exact-name crate), `brew search /^{name}$/`, `pip index versions {name}`. Treat a CLI 404 / no exact match as "free"; fall back to `"{name}" npm` / `"{name}" homebrew formula` web searches only when a CLI is unavailable, and then mark the result unverified.

Flag as **CONFLICTED** if an npm package or Homebrew formula with the exact name exists and has significant usage (downloads > 1k/week or formula is in homebrew-core).

Flag as **AMBIGUOUS** if the package exists but is unmaintained (last publish >2 years ago) or has minimal usage.

### Check 3: Developer tool web search
Search: `"{name}" developer tool open source`

Look for: product sites, landing pages, documentation sites, Show HN posts, blog posts announcing a tool by this name. If a product website exists for a developer tool with this name, it's **CONFLICTED**.

### Check 4: Domain signal
Search: `"{name}.dev" OR "{name}.io" OR "{name}.sh"`

A registered domain for an active project is a strong CONFLICTED signal. A parked/for-sale domain or no results is fine.

---

## Classification

| Status | Meaning | Symbol |
|--------|---------|--------|
| **CLEAR** | No significant conflicts found in any check | ✅ |
| **AMBIGUOUS** | Minor conflicts exist (different domain, archived, low usage) | ⚠️ |
| **CONFLICTED** | Active project or package uses this name in the same or adjacent space | ❌ |

**Tie-breaking rule**: If in doubt, mark AMBIGUOUS not CLEAR. The user can decide whether the conflict is meaningful.

---

## Output Format

Present results as a table, CLEAR names first:

```
## Name Vetting Results

### ✅ Available
| Name | Notes |
|------|-------|
| Epoch | No significant developer tool. Unix/ML concept but not claimed as a product name. |
| Vigil | No conflicts in dev tooling space. |

### ⚠️ Ambiguous — worth a closer look
| Name | Conflict | Severity |
|------|----------|----------|
| Plexus | Netflix library (archived 2023), unrelated domain | Low — different space, inactive |
| Meridian | Some small repos, no active product | Low |

### ❌ Conflicted — avoid
| Name | Conflict | Why it matters |
|------|----------|----------------|
| Forge | GitLab Forge, several active CLIs | High — directly adjacent space |
| Relay | Meta's Relay (GraphQL), npm package with 10M+ downloads | High |
```

After the table, recommend the top 2-3 CLEAR names that best fit the brand context, with one sentence on why each survives.

---

## Integration with Brand Strategy

If `.claude/product-marketing-context.md` exists, read the `name_candidates` and `positioning` sections before vetting. Use the positioning to make better AMBIGUOUS/CONFLICTED calls — a conflict in a completely different industry matters less than one in the same developer tooling space.

After vetting, offer to update `product-marketing-context.md` with the `name_candidates_vetted` section.

---

## Proactive Behaviors

- **Don't vet names you already know are conflicted.** If the user suggests "Forge", note the conflict immediately rather than running full searches.
- **Surface near-misses.** If "Vigil" is clear but "Vigilo" is also clear and sounds better, mention it.
- **Check stylizations.** If "AgentMux" is conflicted, check "agentmux" (lowercase), "Agenmux", "AgntMux" — slight variations may be available.
- **Domain availability is a bonus signal, not a blocker.** Focus on software namespace conflicts first.

---

## Related Skills

| Skill | When to use |
|-------|-------------|
| `pm-brand-strategy` | Define positioning before vetting names — context improves AMBIGUOUS calls |
| `pm-brand-guidelines` | Apply the chosen name to a full brand system |
| `ui-logo-designer` | Generate logo concepts once a vetted name is chosen |
