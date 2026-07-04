---
name: code-new-project
description: Bootstrap a new personal/side project using Tyler's researched default app stack (Angular, Rust+Axum, Connect-RPC/WebSocket, GCP Cloud Run, Neon+R2, OpenTofu). Runs a short decision interview to adapt the defaults (KMP-sharing frontend, Firebase migration, personal vs production scale) then scaffolds the full repo — build files, RPC/proto layer, multi-environment IaC (staging+prod), CD pipeline (Workload Identity Federation, build/push/deploy), local dev via Neon Local, sqlx migrations tooling, secrets/.env conventions, quality tooling, and CLAUDE.md/AGENTS.md referencing the /sdd:full, journeys-extract, and pm-brand-strategy skills for ongoing development. Use when starting a new personal project, asking "what stack should I use for this", or "bootstrap a new project".
---

# code-new-project

Bootstraps a new project repo against Tyler's decided default app stack, after a short interview to check whether any of the stack's documented exception cases apply. The stack and its rationale come from a 2026 multi-agent research pass — see `reference.md` in this skill for the condensed decision matrix (originally synthesized to `logseq/pages/Personal App Stack (2026).md` in the personal-wiki repo, but this skill is self-contained and does not require that repo to be present).

## When to Use This Skill

- Starting a brand-new personal/side project and want the stack decided already
- Migrating an existing Firebase app and need the composed replacement (auth/storage/realtime)
- Unsure whether a project's specifics (KMP sharing, real users, existing infra) should change the defaults

## Workflow

### 1. Run the decision interview

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
