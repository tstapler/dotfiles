# code-new-project

Bootstraps a new project against Tyler's researched default app stack (Angular, Rust+Axum, Connect-RPC/WebSocket, GCP Cloud Run, Neon+R2, OpenTofu), after a short decision interview to check whether documented exception cases apply (KMP-sharing frontend, Firebase migration, personal vs. production scale, RPC layer).

## Installation

Already installed at `~/.claude/skills/code-new-project/` — available across all project repos.

## Usage

Invoked automatically when starting a new personal/side project, or explicitly via `/code-new-project`. Runs an `AskUserQuestion` interview, then calls `scripts/bootstrap.sh` to scaffold real files — not just advice.

**Example prompts**:
- "Bootstrap a new project for X"
- "What stack should I use for this?"
- "I'm migrating an app off Firebase, set it up"

## Structure

- `SKILL.md` — interview flow + scaffolding workflow (loaded when the skill is relevant)
- `reference.md` — condensed decision matrix and rationale from the July 2026 research pass (loaded when justifying a default)
- `scripts/bootstrap.sh` — the actual scaffolder; smoke-tested end-to-end (Angular app generates and installs, Rust workspace — including the RPC/WebSocket variant — compiles clean via `cargo check`)
- `resources/` — templates copied by the bootstrap script: GitHub Actions CI/CD (path-filtered tests + WIF-based staging deploy + manual prod promotion), Dockerfile, Lefthook config, Cargo workspace (including a standalone `migrator` binary crate), Axum starter, `docker-compose.yml` (Neon Local), `.env.example`/`.envrc`, real OpenTofu **modules + environments** structure (`opentofu-modules/app/` + `opentofu-modules/environments/{staging,prod}/` — Cloud Run service + migration Job, Neon branch/endpoint/role/database, R2 bucket), `proto/` (buf config + starter `.proto`), Rust WebSocket streaming handler (`ws.rs`, smoke-tested), Connect-RPC scaffolding (`CONNECT_RPC_NOTE.md` flags the Rust crate side as unverified/experimental), Angular RPC client starters, and `CLAUDE.md`/`AGENTS.md` templates referencing `/sdd:full`, `journeys-extract`, and `pm-brand-strategy`

## Security

- No hardcoded secrets — OpenTofu provider blocks read `CLOUDFLARE_API_TOKEN`/`NEON_API_KEY` from env, Cloud Run's `DATABASE_URL` (both pooled and direct) goes through Secret Manager, GitHub Actions -> GCP auth uses Workload Identity Federation (no long-lived GCP key ever stored in GitHub)
- IaC has unset `TODO` variables (no defaults) so an unconfigured `tofu apply` fails loudly instead of provisioning into the wrong project
- One GCP project per environment (not shared) — a mistake in staging/dev structurally cannot reach prod IAM/data

## Staleness Warning

`reference.md` is a snapshot from 2026-07-03 (pricing, free tiers, and product lifecycle status change fast — see the App Runner sunset and PlanetScale free-tier removal examples baked into that file as cautionary evidence). Re-verify before a production decision if this skill is used long after that date.

## Version History

- v1.0.0 (2026-07-03): Initial release — interview + full scaffold (app/build/CI/IaC), smoke-tested.
- v1.1.0 (2026-07-03): Added Connect-RPC (unary/server-streaming) + WebSocket (bidi streaming) RPC layer, CLAUDE.md/AGENTS.md generation referencing `/sdd:full`, `journeys-extract`, and `pm-brand-strategy`. The WebSocket transport and proto/buf tooling are smoke-tested; the Rust Connect-RPC crate integration is scaffolded but explicitly flagged as unverified against the real crate API (`CONNECT_RPC_NOTE.md`) — its own maintainers describe it as not yet production-ready.
- v1.2.0 (2026-07-03): Added the "must-decide-before-real-deploy" layer, backed by a second 5-subagent research pass verified against live 2026 sources: multi-environment IaC (Neon branch-per-env + GCP project-per-env + OpenTofu `environments/`+`modules/`, validated with `terraform validate` against real provider schemas — caught and fixed a genuine schema error in the process), a CD pipeline (Workload Identity Federation + build/push/deploy, confirmed current against June 2026 Google docs), local dev via Neon Local (confirmed to exist — was an open question in v1.0), sqlx migrations tooling (a standalone `migrator` binary as the Cloud Run Job entrypoint, confirmed the Neon pooler/prepared-statement gotcha is real), and a direnv+`.env`/1Password secrets pattern.
