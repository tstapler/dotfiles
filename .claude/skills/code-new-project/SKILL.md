---
name: code-new-project
description: Bootstrap a new personal/side project using Tyler's researched default stacks — a full hosted web app (Angular, Rust+Axum, Connect-RPC/WebSocket, GCP Cloud Run, Neon+R2, OpenTofu), a library/CLI/MCP tool (Rust, clap, rmcp, cargo-dist, git-cliff, Homebrew tap — modeled on tstapler/kibitzer), or a local single-user app/dashboard (roll-your-own Axum+SQLite+static-SPA bolted onto an existing binary by default; PocketBase/TrailBase/Tauri only for specific standalone-app or native-desktop cases). Starts by asking which kind of project this is, then runs a short decision interview to adapt the defaults, then scaffolds the full repo (or, for the local-app path, states the decision and pattern to follow — that path has no scripted bootstrap since it depends on whether an existing binary/DB already exists). For web apps: build files, RPC/proto layer, multi-environment IaC (staging+prod), CD pipeline (Workload Identity Federation, build/push/deploy), local dev via Neon Local, sqlx migrations tooling, secrets/.env conventions, quality tooling. For lib/CLI/MCP tools: single- or multi-crate layout, clap/rmcp starter, cargo-dist release pipeline with a human-pushed-tag flow, git-cliff changelog, PR test-gate CI, Lefthook. All paths generate or reference CLAUDE.md/AGENTS.md pointing at /sdd:full and other ongoing-development skills. Use when starting a new personal project, adding a local dashboard/UI to an existing tool, asking "what stack should I use for this", or "bootstrap a new project".
---

# code-new-project

Bootstraps a new project repo against Tyler's decided default stack for the kind of project it is, after a short interview to check whether any documented exception cases apply. The web-app stack and its rationale come from a 2026 multi-agent research pass — see `reference.md` for the condensed decision matrix (originally synthesized to `logseq/pages/Personal App Stack (2026).md` in the personal-wiki repo, but this skill is self-contained and does not require that repo to be present). The library/CLI/MCP-tool stack is modeled directly on `tstapler/kibitzer` (which now itself has the CI test gate and README this skill originally added as fixes, not conventions — see `reference.md`).

## When to Use This Skill

- Starting a brand-new personal/side project and want the stack decided already
- Building a CLI tool, an MCP server, or a small Rust library/binary and want kibitzer-style release tooling (cargo-dist, git-cliff, Homebrew tap) without re-deriving it
- Migrating an existing Firebase app and need the composed replacement (auth/storage/realtime)
- Unsure whether a project's specifics (KMP sharing, real users, existing infra, single- vs multi-crate) should change the defaults

## Workflow

### 0. Ask which kind of project this is

Before anything else, ask via `AskUserQuestion`:

- **Web app** (default for anything with a browser-facing UI and its own users/data, hosted for real/multiple users) → go to step 1.
- **Library / CLI / MCP tool** (a Rust binary, a CLI, an MCP server, something distributed via Homebrew/crates.io/npm rather than deployed) → skip to step 1b.
- **Local, single-user app** (a browser-served dashboard/UI that only ever runs on the owner's own machine — no hosting, no other users, no auth) → skip to step 1c.

If genuinely ambiguous (e.g. "a tool with a small web dashboard"), ask which surface is primary rather than guessing — the three paths produce very different repos and there's no supported hybrid scaffold. The Web app vs. Local single-user app split is usually the one worth double-checking: "will anyone but me ever load this over a network" is the actual test, not "does it have a browser UI."

### 1c. Local, single-user app: run the decision tree

This path is deliberately **not a scripted bootstrap** — the right shape depends entirely on whether an existing binary/process already owns the data this UI will show. See `reference.md`'s "Local Single-User App Stack" section for the full research (TrailBase vs. PocketBase vs. roll-your-own vs. Tauri) backing this.

1. **Is this a dashboard/UI being bolted onto a project that already has its own process and its own local database (SQLite or otherwise)?**
   - Yes (the common case — e.g. adding a `<tool> ui` subcommand to an existing Rust CLI/daemon) → **roll your own**: add an Axum (or equivalent) router to the existing binary, reading the existing DB connection directly, `bind(127.0.0.1:<port>)`, no auth at all (it's the owner's own machine), serving a built static SPA (Angular, per this skill's default, unless the dashboard is trivial enough that plain server-rendered HTML is less work than standing up a whole Angular build for it — ask which if unclear). This is the only option that doesn't mean running a second process or vendoring a full backend framework with its own auth/admin-UI model you'd then have to work around.
   - No (this is a genuinely new, standalone local app/service with no existing binary or database to hook into) → continue to question 2.
2. **Would you rather not hand-roll the REST/realtime/admin-UI layer yourself for this new standalone local app?**
   - No preference / happy to roll your own → same as above: Axum/equivalent + SQLite + static SPA, just as its own new binary instead of a subcommand.
   - Yes, want a batteries-included local backend → default to **PocketBase** (Go, single binary, MIT, mature, embeddable as a framework if custom routes are needed later) over TrailBase — TrailBase (Rust, single binary, OSL-3.0, Alpha status as of 2026) is the more idiomatic-feeling choice if the project is Rust-only end-to-end, but its own maintainers describe embedding it as a framework as "an afterthought," and neither project has a documented single-user/no-login mode (both require manually opening up API rules to fake "no auth"). Note the language mismatch either way: PocketBase is Go, so it can't be linked into a Rust binary — this only applies to option 2, a standalone process, never to option 1's "bolt onto an existing Rust binary" case.
3. **Does this need to be an installed native desktop app** (dock/taskbar presence, native OS notifications, no "open a browser tab to localhost" step) rather than a page served locally and opened in a browser?
   - No (default — a CLI that prints a URL to open is enough friction reduction for a personal tool) → whichever of the above applies.
   - Yes → **Tauri** (Rust backend + OS-native WebView, `tauri-plugin-sql` for SQLite) instead of/wrapping whichever backend choice above — this is an orthogonal packaging decision, not a competing backend option.

State which branch applies and why in one short summary before writing any code — this determines the actual shape of what gets built, so confirm it rather than silently picking one.

### 1b. Library/CLI/MCP tool: run the decision interview

1. **Crate layout** — "Single binary crate (kibitzer-style — CLI/MCP/daemon all as clap subcommands in one crate, simplest), or a multi-crate workspace (stapler-mcp-style — separate `crates/cli` and `crates/core`, for projects that expect to add native bindings or a WASM target alongside the CLI)?"
   - Single (default — most new CLI/MCP tools don't need the extra layers) → `--layout single`
   - Multi → `--layout multi`; note that `crates/native`/`crates/wasm` are **not** auto-scaffolded (they're genuinely project-specific) — point at `tstapler/stapler-mcp`'s `crates/{cli,core,native,wasm}` as the reference layout to extend by hand
2. **Publish targets** — "Where should releases publish to: Homebrew tap (default), crates.io, npm, or some combination?" → `--publish` (comma-separated)
3. **GitHub username/org** for the Homebrew tap and repo links → `--github-user` (default `tstapler`)

State the resulting stack back to the user in one short summary before scaffolding.

### 2b. Scaffold the repo (library/CLI/MCP tool)

```bash
scripts/bootstrap.sh \
  --dir <target-directory> \
  --kind lib-cli-mcp \
  [--layout single|multi] \
  [--publish crates,npm,homebrew] \
  [--github-user <github-username>]
```

The script:
- Creates the Rust project (`Cargo.toml`, `rust-toolchain.toml` with clippy+rustfmt, `.gitignore`) — either a single binary crate (`src/main.rs`, clap subcommands `run`/`mcp`, `rmcp` dependency) or a `crates/{cli,core}` workspace
- Adds `dist-workspace.toml` (cargo-dist config) and `cliff.toml` (git-cliff config, Conventional Commits, matches kibitzer's grouping) — **does not** write `.github/workflows/release.yml` itself, since that file is meant to be generated by `dist generate` against whatever `cargo-dist` version is actually installed; instead it writes `RELEASE.md` with the one-time `dist init`/`dist generate` steps and the **human-pushes-the-tag** rationale (a bot-authored `GITHUB_TOKEN` push can't trigger other `on: push` workflows, so release-please-style automation doesn't work here)
- Adds `.github/workflows/ci.yml` — a PR/push test gate (fmt, clippy, test); this was originally a deliberate addition rather than something copied from kibitzer, because ungated CI looked like a gap rather than a convention worth repeating — kibitzer has since added the same job itself
- Adds `lefthook.yml` (fmt + clippy pre-commit, test pre-push)
- Generates `README.md` (install/usage/license — originally added as a gap fix; kibitzer has since added its own), `LICENSE` (MIT), `CLAUDE.md`, `AGENTS.md`

After running, tell the user what still needs manual setup: `dist init` + `dist generate`, creating the Homebrew tap repo and/or crates.io/npm tokens per the chosen publish targets, and `cargo check` to confirm the scaffold builds (this skill's own smoke test validated TOML/YAML syntax of the generated files but could not run `cargo build` — no `cargo` binary was available in the environment used to author it; run it yourself before trusting the scaffold compiles).

### 1. Run the decision interview (web app)

Before scaffolding anything, ask via `AskUserQuestion` (do not skip — the answers change which templates get used):

1. **KMP-sharing?** — "Does this project need to share Kotlin business logic/UI with an existing Kotlin Multiplatform mobile or desktop app?"
   - No (default) → frontend = **Angular**
   - Yes → frontend = **Compose Multiplatform / Web (Wasm)** — flag that this is Beta-tier and accept SEO/accessibility trade-offs (see `reference.md`)
2. **Auth needed?** — "Does this project need user accounts/authentication at all?"
   - No (rare — internal tool, single-user) → skip auth scaffolding entirely
   - Yes (default for anything with users) → scaffold **Ory Kratos** regardless of whether this is greenfield or a migration — it's the locked-in default either way, not just a Firebase-migration fallback
3. **Firebase migration?** — "Is this replacing an existing Firebase-backed app, or greenfield?"
   - Greenfield (default) → auth scaffolding (if requested above) is a clean Kratos setup, no Firebase-specific migration notes
   - Migrating → same Ory Kratos scaffold, plus migration-specific notes (Firestore→Postgres schema conversion, Firebase Auth user export/import — see `reference.md`), and ask a follow-up: does the app actually use Firestore realtime listeners (`onSnapshot`) heavily, or mostly plain CRUD? Only add **PowerSync** if realtime/offline sync is a real requirement — don't default it in
3. **Scale** — "Personal/side-project traffic, or does this need to support real paying users?"
   - Personal (default) → use the stack as-is, Neon free tier assumptions hold
   - Production-scale → flag in the scaffold's README that compute/storage tiers (Cloud Run min-instances, Neon plan) need re-sizing before launch — do not silently upgrade tiers, just flag it
4. **Backend language** — confirm **Rust + Axum + sqlx** (the locked-in default) unless the user explicitly wants to deviate for this specific project (e.g. a quick prototype where Kotlin/Quarkus dev speed matters more) — see `reference.md` for the documented fallback.
5. **RPC layer?** — "Does this project need typed RPC between frontend and backend (Connect-RPC + Protobuf), or is plain REST/JSON fine?"
   - RPC (default, matches the locked-in stack) → scaffold `proto/`, Connect-RPC for unary/server-streaming, WebSocket for bidirectional streaming — **flag clearly that the Rust Connect-RPC crate ecosystem is experimental** (its own maintainers say "not yet recommended for production"); the WebSocket transport itself is plain Axum + `prost` and is smoke-tested/solid
   - Skip (`--skip-rpc`) → plain REST/JSON only, no proto layer — reasonable if the user wants to avoid the experimental-crate risk entirely for this project

State the resulting stack back to the user in one short summary before scaffolding, so they can correct anything before files get written.

### 2. Scaffold the repo

Run `scripts/bootstrap.sh` with flags derived from the interview answers:

```bash
scripts/bootstrap.sh \
  --dir <target-directory> \
  --frontend angular|compose-web \
  [--firebase-migration] \
  [--realtime-sync] \
  [--skip-iac] \
  [--skip-rpc]
```

The script (smoke-tested end-to-end, including a `cargo check` pass on every generated variant, `terraform validate` against the real Google/Cloudflare/Neon provider schemas, and a YAML syntax check on the CI/CD workflow):
- Creates the directory structure (`backend/`, `frontend/`, `iac/`, `proto/`, `.github/workflows/`)
- Initializes the Rust backend workspace from `resources/Cargo.toml.template` and a minimal Axum starter
- Adds a standalone `backend/migrator/` binary crate (calls `sqlx::migrate!()` programmatically) plus `backend/migrations/` with a sample migration — this is the Cloud Run Job entrypoint for production migrations, not `sqlx-cli` baked into the runtime image
- Unless `--skip-rpc`: adds `proto/` (buf config + a starter `.proto`), wires Connect-RPC-shaped service definitions for unary/server-streaming and a WebSocket handler (`ws.rs`, plain Axum + `prost`, smoke-tested) for bidirectional streaming, and drops a `CONNECT_RPC_NOTE.md` flagging that the Rust Connect-RPC crate side needs a manual validation pass before real use
- Runs `ng new` for an Angular frontend (or prints the `kotlin-wasm-compose-template` clone command if Compose Web was chosen — this path is less templated since it's the lower-confidence option); when RPC is included, also drops `frontend/src/app/rpc/connect-client.ts` and `ws-client.ts` starter files
- Adds `docker-compose.yml` wired to **Neon Local** (official Neon Docker proxy — spins up a real ephemeral branch on `docker compose up`, deletes it on down; not an offline emulator, still needs network) plus `.env.example` and `.envrc` (direnv) for local secrets
- Copies `resources/github-actions-ci.yml` into `.github/workflows/ci.yml` — path-filtered test jobs, an ephemeral-Neon-branch-per-PR integration test job (via `neondatabase/create-branch-action`, torn down on PR close), and a staging auto-deploy job (Workload Identity Federation + `docker buildx build --push` to Artifact Registry + `tofu apply`, gated to `main`) plus a manual `workflow_dispatch` job to promote a validated image to prod
- Copies `resources/Dockerfile.dev` as the pinned local/CI toolchain image
- Copies `resources/lefthook.yml` as the pre-commit config
- Generates `CLAUDE.md` and `AGENTS.md` from templates — both point at `/sdd:full` for feature planning, `journeys-extract`/`journeys-enrich`/`journeys-verify` for keeping `docs/journeys/*.md` in sync with what the app actually does, and `pm-brand-strategy` for establishing the project's brand/positioning early
- Unless `--skip-iac`, copies a real OpenTofu **module** (`iac/modules/app/` — Cloud Run service + migration Job, Neon branch/endpoint/role/database, R2 bucket) plus two thin **environment** directories (`iac/environments/{staging,prod}/`, each with its own backend/state/GCP-project variables) that call it — validated with `terraform validate` against the actual provider schemas during scaffold authoring, not guessed. One Neon *project* is shared across environments via branching; GCP gets a *separate project per environment* — see `reference.md` for why this mismatch is intentional.
- If `--firebase-migration=true`, adds an `AUTH.md` note pointing at Ory Kratos setup and, if `--realtime-sync=true`, a `SYNC.md` note pointing at PowerSync — deliberately not auto-scaffolding these two since they're lower-confidence/optional pieces (see `reference.md`)

After running, tell the user what was created, what still needs manual setup (creating the actual Neon project and GCP projects, WIF setup, repo variables/secrets, `buf generate` for the RPC layer), and remind them the IaC stubs have `TODO` placeholders that must be filled before `tofu apply` will work — the full checklist is written into the scaffolded `README.md`.

### 3. Point back to the source research

If the user asks *why* a particular default was chosen, answer from `reference.md` first — it has the condensed rationale and the specific 2026 facts that drove each choice (e.g. why App Runner and PlanetScale are excluded). Only suggest re-running deeper research if something in `reference.md` is stale enough to need re-verification (check dates — the research was done July 2026).

## Key Principles

- **Interview before scaffolding, every time** — the defaults have documented exceptions; don't silently assume "no" to all three questions.
- **Scaffold real files, not advice** — this skill's value is `scripts/bootstrap.sh` actually producing a working repo skeleton, not printing a stack recommendation the user has to implement by hand.
- **Don't over-scaffold optional pieces** — Ory Kratos and PowerSync are real but conditional; only add them when the interview confirms they're needed, and even then scaffold minimal notes/stubs rather than a full integration (auth/sync setup is project-specific enough to not template blindly).
- **Flag, don't silently override, scale mismatches** — if the user says "production scale," don't quietly upsize Cloud Run/Neon tiers in the templates; tell them what needs manual re-sizing.

## Common Pitfalls

- ❌ Skipping the interview and always scaffolding the Angular+Rust+Cloud Run default — defeats the purpose; the whole point is catching the KMP/Firebase/scale exceptions.
- ❌ Running `tofu apply` on the scaffolded IaC stubs without filling in the `TODO` placeholders (project ID, region, bucket names) — they're intentionally non-functional until customized.
- ❌ Treating `reference.md` as infallible forever — it's a snapshot from July 2026 (pricing, free tiers, and product lifecycle status for cloud services change fast; re-verify before a production decision if this skill is used more than ~6-12 months after that date).
