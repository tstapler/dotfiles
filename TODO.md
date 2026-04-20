# TODO

## System
- [ ] Add cron job to automatically run stapler-scripts/update_node_version.py weekly

---

## Skills Backlog

Skills evaluated for adoption into `~/.claude/skills/`. Ordered by priority within each tier.

Legend: `[verdict] name — source — effort — notes`

### Adopt Now

- [ ] **skill-stocktake** — [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) — Low (~20 min: copy SKILL.md + scripts/scan.sh) ⭐ **highest priority**
  - Batch maintenance auditor for the entire skills library: Keep/Improve/Update/Retire/Merge verdicts
  - Two modes: Quick Scan (delta, ~5 min) and Full Stocktake (complete review)
  - Chunked subagent evaluation (~20 skills/chunk) + resume detection + JSON results cache
  - Directly fills known gap: skills library grows unchecked, no audit tooling exists
  - Install: `npx skillfish add affaan-m/everything-claude-code skill-stocktake` (needs SKILL.md + `scripts/scan.sh`)
  - Run after any batch skill installs; run `/skill-stocktake` (Quick Scan) first

- [ ] **react-ui-design-patterns** — [claudiodearaujo/sistema-de-narra-o-de-livro-front](https://github.com/claudiodearaujo/sistema-de-narra-o-de-livro-front) — Low (copy SKILL.md only, ~15 min)
  - Lightweight React state pattern guide: loading/error/button/empty-state/form
  - Fills gap between `frontend-design` (visual) and React UX engineering
  - ⚠️ 0 stars, repo name mismatch — verify SKILL.md integrity before install
  - Install: copy `SKILL.md` → `~/.claude/skills/react-ui-patterns/SKILL.md`; add to skills-index.md triggering React component/loading/error tasks

### Plan Adoption (Fork & Adapt)

- [ ] **ui-ux-pro-max** — [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) — Medium (1.5–2h: fork + trim SKILL.md + install data/scripts)
  - Searchable design database: 161 palettes, 67 styles, 57 font pairings, 161 product reasoning rules
  - Fills genuine data gap — existing design skills (frontend-design, android-ux-design, ux-expert.md) carry no queryable reference data
  - ⚠️ 43KB SKILL.md violates context-budget discipline — must trim to ~5KB dispatch layer before activating
  - Steps: fork → `uipro init` or manual copy data+scripts → rewrite SKILL.md with progressive disclosure → add to skills-index.md after frontend-design

### Skip

- ~~**python-best-practices-patterns-2**~~ — [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) — Full overlap + language barrier
  - Covers PEP 8, type hints, EAFP, dataclasses, generators, concurrency — all valid patterns
  - ❌ Existing `python-development` skill already covers this domain, stack-specific (uv/Pydantic/Typer/pytest)
  - ❌ SKILL.md is entirely in Chinese — would inject Chinese into Claude's context for Python tasks
  - Only additive pieces: concurrency patterns + `__slots__` — extract those into existing skill if needed

### Monitor

_(skills to re-evaluate when they mature or workflow needs shift)_

### Pending Evaluation

_(URLs queued for `/claude-technique-evaluator`)_

---

## Skills Evaluation Log

| Date | Skill | Verdict | Source |
|------|-------|---------|--------|
| 2026-04-16 | ui-ux-pro-max | Plan Adoption (Fork & Adapt) | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill |
| 2026-04-16 | react-ui-design-patterns | Adopt Now (Minor Tweaks) | https://mcpmarket.com/tools/skills/react-ui-design-patterns |
