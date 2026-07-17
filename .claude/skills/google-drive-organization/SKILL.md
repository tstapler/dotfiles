---
name: google-drive-organization
description: Survey a Google Drive's actual folder structure, apply a PARA-lite organization framework, and produce (then safely execute) a concrete reorganization plan — deduping, sweeping root-level clutter, and fixing misnested folders.
---

# Google Drive Organization

Reorganizing a personal Drive well means surveying what's actually there before
proposing structure — a generic "PARA folder template" imposed on an unsurveyed Drive
just creates new clutter next to the old clutter. This skill is a two-phase process:
survey + plan, then (separately, with explicit go-ahead) execute.

## When to use this

- The user asks to organize, clean up, or restructure their Google Drive
- A Drive has grown organically for years and has root-level file dumping, duplicate
  folders, or inconsistent naming
- Before a big life change that generates a new document category (new job, new
  property, new year) and the user wants to know where things should go

## Phase 1 — Survey (read-only, delegate to an agent)

Use the Drive MCP tools (`search_files`, `list_recent_files`, `get_file_metadata`) —
strictly read-only, no creates/moves/deletes during survey. A single research/general
subagent can do this well since it's read-only and the raw survey output (dozens of
folder listings) doesn't need to stay in the main conversation's context.

What to actually look for — these are the recurring real problems, not hypothetical
ones:

- **Root-level flat dumping**: files sitting directly in "My Drive" root with no
  folder. Query `parentId = 'root'` and separate files from folders.
- **Duplicate files**: same or near-identical `fileSize` under similar titles, often
  created minutes apart (a sign of an accidental double-upload). Compare `fileSize`
  and `createdTime`, don't assume — verify by comparing at least the first page of
  `contentSnippet` too if titles differ slightly.
- **Misnested folders**: a year-folder or category folder living *inside* a sibling
  instead of next to it. Confirm actual nesting before reporting it as a finding — don't
  trust folder names alone, and don't trust a single opaque-ID lookup either (see the
  verification note below). A real example that turned out to be a false positive: an
  agent claimed a `2024 Taxes` folder was nested inside `2025 Taxes` based on a
  `parentId` match; re-checking with `rclone lsf "remote:Taxes" --max-depth 2` showed
  `2024/2025/2026 Taxes` were all correctly siblings — the ID had been misattributed to
  the wrong parent folder during verification.
- **Fragmented topic folders**: many single-purpose top-level folders that are really
  one topic (e.g., 7 different `Health Sync <metric>` folders instead of one `Health/`
  folder with subfolders).
- **Overlapping/duplicate-purpose folders**: a top-level folder and a subfolder
  elsewhere covering the same subject (e.g., a top-level `Remodel/` next to
  `<Property>/Kitchen Remodel/`).
- **Naming drift**: trailing spaces, inconsistent casing, ambiguous dates
  (MM-DD-YYYY vs YYYY-MM-DD) — cheap to fix, good signal of no naming convention.
- **Stale/inactive folders**: old hobby folders, completed projects (e.g., a home
  search folder after the purchase closed) still sitting at the same top level as
  active work — PARA's "Archive" category exists exactly for these.
- **Unmanaged `Shared with me`**: items never triaged into the real folder structure.
  Google Drive has no native way to fold these into folders — the only mechanism is
  "Add shortcut to Drive" for the ones worth keeping.

Verify surprising/specific findings (a claimed duplicate, a claimed misnesting) with a
quick follow-up `search_files` or `get_file_metadata` call yourself before presenting
them as fact — a subagent survey can still get specific file IDs or paths wrong.

## Phase 2 — Framework

**PARA (Projects / Areas / Resources / Archive)** is the right default for a personal
life-admin Drive — it organizes by *actionability* rather than topic:

- **Projects**: time-boxed efforts with a goal and an end (a home renovation, a house
  search, a wedding)
- **Areas**: ongoing responsibilities with no end date (finances, health, a property
  you own)
- **Resources**: reference material that isn't currently actionable (manuals, books,
  research)
- **Archive**: anything from the first three that's gone inactive — moved out, not
  deleted

The critical habit most unorganized Drives are missing isn't folder creation, it's
**archiving on completion** — when a project (house search, a specific renovation
phase) finishes, its folder should move to Archive, not sit forever at the same top
level as active work.

Don't reach for a numeric system like Johnny Decimal unless the Drive has dozens of
top-level categories that PARA's four buckets can't reasonably absorb — for a single
person's life-admin Drive, a hard cap on top-level folder count (aim for well under
10) usually gets you the "nothing is more than a couple clicks away" benefit without
the addressing overhead.

**Naming conventions** (apply going forward, don't retroactively rewrite years of
existing filenames for marginal benefit):
- Date-bound files/folders: `YYYY-MM-DD` prefix — the only format that sorts
  correctly both chronologically and alphabetically across every OS/locale
- Year-based categories (tax folders, annual exports) as **siblings**, never nested
  inside each other
- Status tags in brackets (`[FINAL]`, `[DRAFT]`) when a file's state matters and isn't
  obvious from content
- Prefer hyphens/underscores over spaces for portability; watch for trailing spaces
  from manual folder creation (a real, common source of near-duplicate-looking folders)

## Phase 3 — Produce the plan

Deliver: a proposed top-level taxonomy (aim for ~5-8 categories mapping to the
person's actual areas of life), a migration table (current path → proposed path) that
maps *every* existing top-level folder somewhere, and a short list of dedup/misnesting
fixes to make before any bulk moves. Be honest about scope — if the survey shows a
Drive that's already reasonably organized, say so and propose a light-touch cleanup
rather than inventing a full rebuild to justify the exercise.

Present the plan for review (an Artifact works well for a long migration table) before
executing anything.

## Phase 4 — Execute (only with explicit go-ahead, in stages)

Moving and deleting real files/folders needs the user's explicit permission per
session safety norms — this phase is not something to run unattended even if the plan
itself was approved in principle:

1. **Dedup fixes first** — these are the highest-value, lowest-risk items (confirmed
   duplicate files/folders). Still confirm before deleting anything; there's often no
   "delete" capability exposed via MCP tools at all, only via the Drive web UI, which
   moves to Trash (reversible) rather than permanently deleting.
2. **Misnesting fixes** — move a folder to its correct parent.
3. **Root sweep** — move loose root-level files into their target folders, in batches
   the user can sanity-check (e.g., by category), not all at once.
4. **Rename passes** — trailing spaces, date-prefix conventions going forward.
5. Re-survey afterward to confirm the moves landed where intended — don't assume a
   move succeeded without checking, the same way an upload shouldn't be assumed to
   have succeeded without checking (see the file-integrity lesson below).

## Prefer rclone over the Drive MCP tools when it's available

Check `rclone listremotes` first — if a `gdrive:`-style remote is configured (verify
it's the right account by comparing `rclone lsf gdrive: --max-depth 1` against known
folder names, since `rclone about`'s quota won't match the Drive web UI's combined
Google One figure), it beats the MCP tools for most of this work:

- **Uploads**: `rclone copy <local file> "gdrive:path/to/folder/"` is a real,
  purpose-built multipart upload — no base64 encoding, no size limits to silently hit.
- **Verification**: `rclone lsf "gdrive:Some Folder" --max-depth 2` and `rclone lsl`
  (with sizes) are simple, human-readable path-based listings — far easier to sanity
  check by eye than chasing opaque `parentId` values through the MCP `search_files`
  tool, where it's easy to misattribute which ID belongs to which folder (see the
  misnesting false-positive above — that mistake came directly from this).
- Still verify byte sizes after an `rclone copy` the same way you would for any upload
  — don't skip verification just because the tool is more trustworthy.

## A hard-won lesson: verify uploads/moves, don't trust agent reports

If rclone isn't available and uploading falls back to the `create_file` MCP tool with
base64 content: that tool has been observed to silently produce corrupted/truncated
files when the upload work is delegated to an agent that spawns its own sub-agents to
parallelize it — files arrived at ~1500 bytes regardless of their real size, with no
error thrown. If delegating uploads this way:
- Explicitly forbid the agent from using the Agent/Task tool itself — require it to
  do every upload sequentially, itself
- Require a size-verification step after every single file (`get_file_metadata`'s
  `fileSize` compared against the local file's real byte count via `stat`), not just
  a final "did files appear" check — a corrupted file still shows up in a folder
  listing
- Independently re-verify the agent's final report yourself with your own
  `search_files`/`get_file_metadata` call before telling the user anything is done

This whole section is why the rclone path above is strongly preferred when available.

## References

- [The PARA Method (Tiago Forte)](https://fortelabs.com/blog/para/)
- [Organize your files in Google Drive — Google Help](https://support.google.com/drive/answer/2375091)
- [File Naming Conventions — Harvard Data Management](https://datamanagement.hms.harvard.edu/plan-design/file-naming-conventions)
- [Best Practices for File Naming — National Archives](https://records-express.blogs.archives.gov/2017/08/22/best-practices-for-file-naming/)
- [Johnny Decimal System](https://www.getsortio.com/glossary/johnny-decimal-system) — for when PARA's four buckets aren't enough
