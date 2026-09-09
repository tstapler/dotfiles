# Research: full-featured Pi profile for a Claude Code user

Snapshot: 2026-09-03

Public package catalogs, npm metadata, repository source, and documentation are
untrusted intake data. This document recommends what to audit and fork; it does
not approve execution. Every selected third-party repository still goes through
the fork, exact-commit pin, source review, and temporary-home test gate.

## Important correction discovered during research

Pi moved npm scopes in May 2026. `@mariozechner/pi-coding-agent` is deprecated
and stopped at `0.73.1`. The maintained package is
`@earendil-works/pi-coding-agent`, observed at `0.84.4`. The bootstrap pin has
been corrected accordingly. This also removes the earlier Plannotator `>=0.74`
compatibility concern.

## What Pi already provides

Do not install extensions merely to imitate a familiar name. Pi already has
core read/write/edit/bash and file discovery tools, instructions and skills,
prompt templates, model/provider switching, session persistence, branching,
compaction, themes, keybindings, package filtering, and an extension API.
Extensions are most valuable for the Claude-specific gaps:

- Claude tool-name compatibility used by existing skills (`AskUserQuestion`,
  `TaskCreate`, `WebSearch`, `Agent`, and related names);
- deterministic permission prompts and protected-path rules;
- hook compatibility;
- plan mode with actual mutation blocking;
- subagents, parallel work, and worktree isolation;
- MCP;
- background/interactive processes;
- checkpoint/rewind;
- browser and web research;
- LSP/test feedback;
- session handoff/search and quality-of-life UI;
- secure, host-side credential resolution.

The existing skills materially use Claude tool names, especially
`AskUserQuestion`, `WebSearch`, `WebFetch`, task tools, and `Agent`. We therefore
need either a selective compatibility extension or a deliberate source
translation layer; relying on prompt wording alone would regress behavior.

## Recommended modular profile

### Tier 0: local and first-party foundations

1. **Ponytail Pi extension** — local Tyler-owned code already implemented.
2. **Existing `llm-sync` skills/prompts export** — remains the source of truth.
3. **Small Tyler-owned Claude tool shims where practical** — preferable to a
   large compatibility bundle for trivial aliases.

### Tier 1: safety and execution policy — universal base

#### `gotgenes/pi-packages`

Review anchor: `e64946b5ce96ca004b753d98932c8b13106dd132`, MIT.

Candidate packages from one fork:

- `@gotgenes/pi-permission-system`
- `@gotgenes/pi-subagents`
- optionally `@gotgenes/pi-subagents-worktrees`

This is the strongest foundation found. The permission system gates normal
Pi tools, bash, MCP tools, skills, sensitive paths, symlink-resolved paths, and
outside-project access with allow/ask/deny behavior. It fails closed on parser
or internal errors, gates project policy behind Pi project trust, and forwards
subagent approval requests to the parent UI. Its subagent implementation is
in-process, supports foreground/background execution, concurrency limits,
steering, resumption, transcripts, custom agents, context inheritance, and an
event bus. The companion package adds worktree isolation.

Why this beats separate generic permission and subagent packages: the two
components have an explicit integration contract, so permission prompts from
child agents are not silently lost. It also reduces the number of independently
trusted repositories.

Required review:

- verify all shell parser fail-closed paths and wrapper handling;
- start from deny/ask defaults for writes, external paths, credentials, git
  publication, package installation, and destructive commands;
- ensure untrusted project configuration cannot weaken global policy;
- verify children do not inherit secrets or extension capabilities by default;
- test worktree cleanup, branch retention, symlinks, nested repositories, and
  cancellation;
- do not enable the optional model-based permission judge initially.

#### Plan mode from `narumiruna/pi-extensions`

Review anchor: `04aae270c51cf4de70479d84317eb15ac8e20e33`, MIT.
Package: `@narumitw/pi-plan-mode`.

This plan mode is substantially stronger than a prompt-only mode: it blocks
editing tools and unapproved extension tools, applies a fail-closed restricted
shell policy, persists plan state across resume/compaction, provides structured
questions, requires structured plan completion, and supports implement-here or
fresh-session handoff. It is compatible with Pi 0.84.4.

Keep the generic permission system authoritative outside plan mode. During
fork review, add integration tests proving that the two independent gates
compose most-restrictively and cannot reactivate a tool denied by the other.

### Tier 2: Claude workflow compatibility — universal base

#### Hooks: `hsingjui/pi-hooks`

Review anchor: `8250a856d4f892f0a8a640ac2f1241d1a000701b`.
Npm package reports MIT, but the repository snapshot had no standalone license
file; resolve that before forking/provisioning.

It reads Claude-style hook configuration and maps SessionStart/End,
Pre/PostCompact, Pre/PostToolUse, tool failure, UserPromptSubmit, and Stop to Pi.
Only command hooks are currently supported; Claude `http`, `prompt`, and
`agent` hook types are not. `PermissionRequest` is also not supported and
should be replaced by the selected permission system, not emulated.

This is a useful compatibility bridge for the tracked post-compaction audit and
future command hooks, but it must not become the primary security boundary.
Hook commands execute local code and need the same review as extensions.

Alternative: `pi-yaml-hooks` at
`003ebd2df62aebfc5ccccdd7e380b35208c3f1d9` is active and has a clear MIT
license, but introduces its own YAML configuration rather than reusing Claude
configuration. Prefer it only if the Claude-compatible bridge fails review.

#### Selective Claude tool compatibility: `fractary/pi-claude-code`

Review anchor: `17e743da59e117b4b155f5bc926702a281811d80`.
Npm and README say MIT, but the repository snapshot had no license file; this
must be resolved before adoption.

Useful selectively loaded shims:

- `Grep`, `Glob`, and `LS` for skills that insist on Claude casing/schemas;
- `AskUserQuestion` for existing interviews;
- `Agent` as a compatibility facade over the selected subagent package;
- possibly Claude task names if they can be adapted to the chosen todo store.

Do **not** load its PlanMode, task store, or web tools by default if specialist
packages are selected; duplicated tools and state stores create ambiguous
behavior. Its `Agent` shim currently targets `pi-subagents`, so the fork will
need adaptation or replacement for `@gotgenes/pi-subagents`.

Because the required subset is small and the legal metadata is incomplete, a
clean Tyler-owned compatibility extension may be safer than carrying the full
package.

### Tier 3: tools expected in a full coding environment

#### MCP: `nicobailon/pi-mcp-adapter`

Review anchor: `6ba7d360fcc67a77ccbbb4921586614798020a7a`, MIT.

Still the primary MCP candidate. It has a large attack surface: subprocesses,
stdio/network transports, OAuth callbacks, browser opening, configuration
parsing, and native keyring integration. Enable only behind the permission
system. The fork should default to no servers and obtain server declarations
through the tiered configuration generator. Secure-store support must never
copy resolved values into generated settings, logs, sessions, or model-visible
results.

#### Ask-user and todo UI: `juicesharp/rpiv-mono`

Review anchor: `338b264c1ca4fd8828cc849b632f4f7ad88d2e78`, MIT.
Candidate packages:

- `rpiv-ask-user-question`
- `rpiv-todo`
- the minimum required local config package

Do not provision the whole monorepo suite: it also contains telemetry, voice,
web, advisor, and workflow packages. Decide whether the todo store or a custom
adapter should back Claude `TaskCreate`/`TaskUpdate` compatibility; there must
be one canonical task state, not two.

#### Checkpoint and rewind: `arpagon/pi-rewind`

Review anchor: `91611ad87992fb7b635a41ba68f67916ff6e6ae3`, MIT.

Preferred over `@ayulab/pi-rewind`, whose source repository is archived. Review
file snapshot boundaries, binary/large-file handling, symlink behavior, git
interaction, restore previews, atomic rollback, and whether untracked user
files can be overwritten or deleted. Start opt-in until destructive-path tests
pass.

#### LSP and diagnostics: `apmantza/pi-lens`

Review anchor: `528bb96eab3f0394b69d369909f104cdca1722a4`, MIT.

Preferred over the much smaller `pi-lsp-adapter` because it combines LSP,
linters, formatters, structural analysis, test feedback, and edit guards.
Provision as an opt-in development fragment at first. Audit executable
auto-discovery, repository-supplied formatter/linter config, automatic fixes,
process timeouts, output limits, and macOS/Linux parity.

#### Web retrieval: `nicobailon/pi-web-access`

Review anchor: `7ca5cdce4fdf33ddec3da4b1858215dcd0c0e382`, MIT.

Candidate for non-browser search and content extraction. Default to providers
that require no secret or obtain credentials through a reviewed host-side
resolver. Add URL policy, redirect limits, response size/time limits, private
network/localhost blocking, content-type validation, and explicit treatment of
all fetched content as untrusted. Keep work-specific web tooling in overlays.

#### Browser debugging: `narumiruna/pi-extensions`

Same monorepo review anchor as plan mode. Candidate package:
`@narumitw/pi-chrome-devtools`.

This candidate has useful security properties: isolated temporary browser by
default, machine-owned connection settings, project settings only after trust,
explicit confirmation for experimental page-provided tools, bounded output,
and cleanup of only the browser it started. Keep WebMCP disabled initially.
Never attach an everyday authenticated browser profile by default.

`pi-agent-browser-native@5460058d7544c6c8b67e039780801539d20440fd`
is a broader alternative with strong cross-platform testing, but brings a much
larger package and overlapping web-search/config behavior. `pi-chrome` can use
the user's authenticated profile and should be an explicit high-risk local
profile, not universal configuration.

#### Background and interactive commands

Two credible but overlapping candidates:

- `99percentpeople/pi-extensions@663964048fc8d5767dfe64d9bf89b68cb3322933`
  package `@99percentpeople/pi-background-tasks`, MIT: background PTYs,
  attach/log/input/signal support; native `node-pty` dependency.
- `nicobailon/pi-interactive-shell@d363e9a162c60be463871ac2132c582e654621c3`:
  rich interactive/hands-free/dispatch/background/reattach workflows, but the
  repository snapshot had no license file.

Start with the 99percentpeople package because licensing is clear and its
scope is narrower. Audit PTY child cleanup, inherited environment, terminal
escape sanitization, output limits, SSH execution, cancellation, and platform
native builds. Do not install both until a concrete missing workflow justifies
the overlap.

### Tier 4: session and user experience — opt-in base

#### Session search and handoff: `thurstonsand/pi-sessions`

Review anchor: `8f2f3d444cc65255bfc61dbb6173e69c21eb5e2c`, MIT.

Provides session indexing/search, old-session question answering, active
session messaging, child-session handoff, title generation, and handoff review.
Valuable for Claude-style long-running work, but session transcripts can contain
sensitive code and prompts. Audit index location and permissions, redaction,
project boundaries, retention/deletion, prompt injection from old transcripts,
and whether work/personal histories can mix. Keep disabled on work machines
unless the work overlay approves it.

#### Async compaction: `almogdepaz/pi-async-compaction`

Review anchor: `5b9a70b678f23b7250f66b97789cb2777061cf3c`, MIT.

Precomputes compaction summaries while work continues. Useful for long sessions,
but summary generation affects correctness and cost. Validate cancellation,
stale-summary detection, model/provider choice, secret handling, and exact
behavior when the active branch changes. Adopt only after baseline Pi
compaction and Ponytail compaction instructions are tested together.

#### Small UX packages

- Notifications: `diegopetrucci/pi-extensions@bf849e251c10d28a3fc601d489fa0ae4768419b1`,
  package `@diegopetrucci/pi-notify`, MIT.
- Clipboard/screenshot images: `MasuRii/pi-image-tools@b8977bbb4f416fd63db7c7c602db6dfe7b17f62c`,
  MIT. It has a postinstall script that patches dependencies, so source-install
  behavior needs special review or removal in the fork.
- Statusline: prefer a tiny Tyler-owned extension or a narrowly filtered package
  over a large QoL bundle. Pi already exposes the necessary model/context/git
  state, and bundles often collide with Ponytail's footer/status.

These should never delay the safety and compatibility foundation.

### Tier 5: credential providers — explicit local profiles only

#### `jmcombs/pi-extensions` / `@jmcombs/pi-1password`

Review anchor: `733bb02439ed1f633909a7142bbbefb412245f81`, MIT.

This is the best match found for the requested desktop secure-store model. It
stores `!op read ...` references—not resolved secrets—in mutable
`~/.pi/agent/auth.json`, resolves them in the host process through 1Password,
and injects values into child command environments while reporting only names.
The dotfiles must not generate or copy `auth.json`; setup remains an explicit
local user action.

Major risk: values are injected into every agent bash child, so any allowed
command, build script, compiler plugin, repository hook, or malicious process
can read them. Require the permission system, least-privilege dedicated vault
items, per-tool/per-project scoping in our fork, output redaction tests, and no
inheritance into subagents/background tasks unless explicitly approved.

#### `liamvinberg/pi-secrets`

Review anchor: `95fb3508ee6a44d644fa131ddd3d3131814d747b`, MIT.

Useful as an ephemeral masked-input fallback. It clearly documents that its
model is cooperative rather than adversarial and that transformations can
bypass redaction. It should not be presented as secure containment and should
not be part of the universal default.

Pi's provider credential command resolution may be preferable for model API
keys because it can retrieve one credential for one provider without exposing a
general secret environment to every shell command.

## Packages not recommended as defaults

- **`pi-code` and other all-in-one suites:** attractive feature lists but broad,
  overlapping trust and state surfaces. A modular reviewed stack gives clearer
  ownership, disablement, and update cadence.
- **Composio:** hosted auth and very broad external-account capability; explicit
  opt-in only after a separate threat model.
- **Context Mode:** Elastic-2.0 rather than an OSI license, install script,
  native database, and invasive tool-output rewriting.
- **Piolium:** useful on demand for security audits, but PoC generation and
  agent fan-out do not belong in an always-on universal base.
- **Archived Oh My Pi rewind source:** prefer the maintained MIT rewind option.
- **Authenticated everyday-browser control:** too much ambient authority for a
  universal default; use isolated browser profiles.
- **Model-based permission judges:** a model must not be the initial authority
  for high-impact operations.

## Proposed final profile shape

### Universal enabled base

- Ponytail
- permission system with conservative global policy
- in-process subagents with low concurrency and no secret inheritance
- plan mode
- minimal Claude tool compatibility
- Claude command-hook bridge
- Ask User UI
- todo/task adapter
- MCP adapter with no servers enabled by default
- notification extension

### Universal installed but disabled/opt-in

- subagent worktrees
- rewind
- web access
- isolated Chrome DevTools
- LSP/lens
- background PTY tasks
- session search/handoff
- async compaction
- image tools
- Plannotator

### Machine-local or work-overlay only

- actual MCP server declarations
- model/provider defaults
- browser executable/profile settings
- credential-provider activation and mutable references
- work-owned Pi package and internal tools
- session indexing approval
- platform-specific LSP/formatter commands

## Next research and implementation gates

1. Resolve missing license files for `pi-hooks`, `pi-claude-code`, and
   `pi-interactive-shell`; do not fork them until the grant is unambiguous.
2. Fork `gotgenes/pi-packages` and `narumiruna/pi-extensions` first; together
   they cover permissions, subagents, worktrees, plan mode, and isolated browser
   control with two review/update streams.
3. Build a compatibility test corpus from the existing synced skills. Every
   referenced Claude tool name must map to one tested Pi tool or be rewritten.
4. Define one canonical task store and one plan mode before enabling any package.
5. Add tiered extension-specific config rendering; package install alone is not
   enough for permission, browser, MCP, or worktree policies.
6. Test each fork in a temporary Pi home with network and credential access
   absent, then with narrowly mocked providers.
7. Only after review, add exact fork commits to disabled config fragments and
   promote them tier by tier.
