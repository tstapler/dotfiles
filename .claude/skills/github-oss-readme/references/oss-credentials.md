# OSS credentials checklist

The files GitHub's own repo "Community Standards" checklist (Insights → Community) looks for, beyond the README. A repo missing most of these reads as abandoned or not-really-open-source, even with a great README.

## The checklist

| File | Purpose | Required? |
|---|---|---|
| `LICENSE` (or `LICENSE.md`) | Defines legal terms of use, modification, and distribution | Yes — without one, the default is "all rights reserved," even if the code is public |
| `README.md` | Entry point (see the other reference files in this skill) | Yes |
| `CONTRIBUTING.md` | How to file issues, set up a dev environment, run tests, submit a PR | Recommended once external contributions are wanted |
| `CODE_OF_CONDUCT.md` | Behavioral expectations for the community | Recommended for any project accepting outside contributions |
| `.github/ISSUE_TEMPLATE/` | Structured issue intake (bug report, feature request) | Optional, high-value once issue volume grows |
| `.github/PULL_REQUEST_TEMPLATE.md` | Checklist for PR authors (tests run, docs updated) | Optional |
| `SECURITY.md` | How to report vulnerabilities privately | Recommended for anything handling user data or credentials |
| `.github/FUNDING.yml` | Sponsorship links | Optional, only if the maintainer wants it |

GitHub aggregates a subset of these into a visible "Community Standards" progress checklist on `github.com/<org>/<repo>/community` — worth checking directly against the live repo when auditing.

## LICENSE: never choose or invent one unasked

A license is a legal decision belonging to the repo owner, not a default to silently apply. When a LICENSE is missing:

1. Ask which license they want. If they have no preference, the common defaults are:
   - **MIT** — permissive, minimal restrictions, the most common choice for small tools/libraries.
   - **Apache-2.0** — permissive plus an explicit patent grant; common for larger projects or anything patent-sensitive.
   - **GPL-3.0** — copyleft; forces derivative works to also be open source. Only if the owner wants that.
2. Once confirmed, use the license's canonical text verbatim (e.g. from [choosealicense.com](https://choosealicense.com) or `gh api licenses/<key>`) — never paraphrase or abbreviate legal text.
3. Fill in the copyright line with the current year and the owner's name/org as given — don't guess a legal entity name.
4. Cross-reference it from the README's own License section (a one-line link, not a duplicate of the text).

## CONTRIBUTING.md: minimum viable content

A useful `CONTRIBUTING.md` answers, in order:

1. How do I set up a local dev environment? (exact commands, not "see docs")
2. How do I run the tests?
3. What's the code style / lint requirement, and how do I run it?
4. How do I submit a change (branch naming, commit format, PR process)?
5. Is there a CLA or DCO sign-off requirement?

Pull these commands from the actual project (Makefile, package.json scripts, CI config) rather than inventing generic ones — the same source-grounding discipline as the README modes in this skill.

## CODE_OF_CONDUCT.md: default to Contributor Covenant

Unless the user has an existing standard they prefer, the [Contributor Covenant](https://www.contributor-covenant.org/) is the de facto default across the OSS ecosystem and is what GitHub's own "Add file" UI offers. Fill in the contact method (email or issue tracker) with what the user actually provides — don't invent a contact address.

## Issue/PR templates: keep them short

A short structured template beats a free-text box, but a long mandatory template gets skipped or filled with junk. For a bug-report issue template, three fields are usually enough: what happened, what you expected, how to reproduce. For a PR template, a short checklist matching the project's actual CI gates (tests pass, docs updated, changelog entry) is more useful than a generic checklist copied from elsewhere.

## Audit output shape

When auditing an existing repo's OSS credentials, report a simple present/missing table before touching anything:

```
## OSS Credentials Audit

| File | Status | Notes |
|---|---|---|
| LICENSE | ✅ Present | MIT, copyright 2024 |
| CONTRIBUTING.md | ❌ Missing | |
| CODE_OF_CONDUCT.md | ❌ Missing | |
| .github/ISSUE_TEMPLATE/ | ⚠️ Partial | bug_report.md only, no feature_request.md |
| SECURITY.md | ❌ Missing | project handles API credentials — recommended |
```

Then ask the user which gaps they want filled before creating any file.
