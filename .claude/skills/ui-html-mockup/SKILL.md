---
name: ui-html-mockup
description: Build a shareable single-file HTML mockup of a UI redesign from real data, with Figma-style annotations (was/now/data/ask pins), a guided tour, a full state matrix and measured accessibility probes. Use when asked to prototype, mock up or critique a view and hand it to a partner team, or when a design needs evidence rather than opinion.
---

# UI HTML mockup

A mockup is a single `.html` file, no build step, that runs from `file://`, shows real (trimmed) data, and explains how it differs from the current design. Anyone can open it, click the pins or take the tour, and answer the questions in it.

## When to use

- Redesigning or proposing a view and you need partner feedback.
- Critiquing an existing view: the mockup is the argument.
- Not for production code. Port to the real design system afterwards; this file uses raw colours on purpose.

## Workflow

1. **Name the question and the baseline.** Write the one question the page must answer ("which pools need attention?"). Capture the current design from screenshots or source and record what it does, so every "Was" is verified, not remembered.
2. **Get real data, read-only.** Prefer a snapshot of the real API over invented rows. Probe the API first: list the kinds or fields it serves, fetch one object, check size limits (responses over a gateway buffer fail outright; select fields to trim). Save raw responses outside the repo. Note what the API cannot provide; those become "Not available" notes and annotation questions, not fake numbers.
3. **Trim and anonymise.** Build a compact JSON (counts, states, timestamps). Drop names, IDs, UIDs and hostnames; use `Item #3 (omitted)`. Label the page as sample data. Keep snapshots from one point in time, because a busy system drifts between fetches and pages then disagree.
4. **Start from `assets/shell.html`.** Inline `annotations.css`, `tabs.js` and `annotations.js` at the placeholders (`/* ANNOTATIONS_CSS */`, `/* TABS_JS */`, `/* ANNOTATIONS_JS */`). Add pages as functions that return HTML from the data. Compute every on-screen number from the data so pages agree.
5. **Design the whole state matrix, not just the happy path.** Loading (skeleton), empty (reason plus next action), error (the real cause plus retry), stale (banner with timestamp; do not dim, dimming breaks contrast), no access (who can grant it). A State selector in the header switches them.
6. **Annotate.** For each part that differs from the current design add an entry: `type` (New, Changed, Question), `was` (current behaviour, verified), `now`, `data` (source field), `ask` (one question for the partner team). Order a `tour` of the most important entries across pages.
7. **Make it operable.** Real `<button>` elements for anything clickable, a visible focus ring, roving tabindex with arrow keys for large grids and for every `role=tablist` (`assets/tabs.js`), top-level page switching in a `<nav>` with `aria-current` (not tabs), targets at least 24px, details never hover-only, text at least 4.5:1, status never by colour alone (text, shape or pattern too: hatch secondary bar segments, outline empty cells). Put every colour behind a CSS variable so a dark theme is one block, and provide the toggle.
8. **Verify with measurements, not by looking.** `scripts/probe.sh file.html#page 1440` returns text-contrast failures, small targets, non-keyboard click handlers, duplicate control names, heading outline and overflow. Run it at 1440 and 720, in light and dark (`probe.sh file.html#page 1440 dark`), on every page and state; loop it over a generated matrix of page by state files rather than by hand. `scripts/shoot.sh file.html#page out.png` screenshots any page; read the PNG. Stress with a 90-character unbroken name and a large number before calling it resilient.
9. **Review against a rubric.** Score the result (task-first, hierarchy, scent, disclosure, colour-alone, contrast, encoding, density, states, feedback, keyboard, targets, tokens, consistency, resilience) and keep a backlog of open findings. If a project rubric exists, use it; otherwise score these 15 as 0/1/2 with the probe output as evidence, and mark anything unmeasured CANNOT_VERIFY. Pass at 80% of the maximum over the criteria you could score (e.g. 22.4 of 28), BLOCKED if any blocker criterion scores 0, and always list the unscored ones.
10. **Share.** Send the file. Links: `file.html#tour` starts the tour, `#annotations` shows pins, `#<page>` opens a page. Tell reviewers to answer the "Ask" lines.

## Annotation contract

`window.MOCKUP = { pages, getPage, go, annos, tour, before }`; call `MOCKUP.afterRender()` after each render. Pins are numbered buttons (shape differs for Question, not just colour). `go(page)` must switch pages without stealing focus. Tour and pin cards are placed beside the highlighted element (right, left, below, above, whichever overlaps least), with a spotlight; anchor annotations to a small element (a heading or control row), not a whole table, so a free side exists. See the header comment in `assets/annotations.js`.

## Pitfalls seen in practice

- A pop-over notes panel that stays open covers the design. Make it a collapsed `<details>`.
- Page switching marked as `role=tab` without arrow-key support fails the ARIA pattern; use `<nav>` + `aria-current` for pages and reserve `role=tablist` for in-page sections.
- A cluster or scope picker drawn as a chip but not wired reads as broken. Wire it (even to an empty state) or draw it as plain text.
- Dimming a "stale" page breaks contrast; use a banner.
- Dark theme exposes contrast failures the light theme hides; probe both.
- Wording drift against the product ("NotReady" vs the product's "Unhealthy"): read the sibling screen's source for its labels before inventing yours.

- A generated number that disagrees across pages (different snapshots, or two sources for "pending"). Compute from one dataset and footnote any cluster-wide versus app-scoped count.
- Invented labels that contradict the product (a state called "disrupted" where the product says "Draining"). Check wording against the source.
- Interactive-looking chips that do nothing. Either wire them or label them as placeholders.
- Tabs or panels with no data behind them. Show only what the data can fill, and list the rest as follow-ups.
- Generic link text ("View", "Open pool" repeated). Use a visible cue plus an `aria-label` naming the target.
- Headless Chrome will not go below about 500px wide, so a true narrow-viewport check is CANNOT_VERIFY there.
- Probes catch contrast and structure, not judgement. Hierarchy, consistency and whether the design is right still need a human.

## Files

- `assets/shell.html` starter with pages, state selector, annotations and tour wired.
- `assets/annotations.css`, `assets/annotations.js` pins, collapsible notes panel, guided tour.
- `assets/tabs.js` arrow-key navigation for tablists.
- `scripts/probe.sh`, `scripts/probe.js` measured checks injected into a copy of the mockup.
- `scripts/shoot.sh` headless screenshot of a page or mode.

## Third-party chrome

When a mockup embeds a faithful copy of an existing product shell (header, rail), put `data-probe-ignore` on its root elements so `probe.js` skips contrast checks there; the shell's own flaws are findings about the real product for the backlog, not mockup failures.
