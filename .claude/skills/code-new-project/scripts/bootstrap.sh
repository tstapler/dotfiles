#!/usr/bin/env bash
# Scaffolds a new project against Tyler's default stacks.
# See ../SKILL.md for the decision interview this should follow, and
# ../reference.md for the rationale behind each default.
#
# Web app usage:
#   bootstrap.sh --dir <target-directory> \
#     [--frontend angular|compose-web] \
#     [--firebase-migration] \
#     [--realtime-sync] \
#     [--skip-iac] \
#     [--skip-rpc]
#
# Library/CLI/MCP tool usage (modeled on tstapler/kibitzer):
#   bootstrap.sh --dir <target-directory> --kind lib-cli-mcp \
#     [--layout single|multi] \
#     [--publish crates,npm,homebrew] \
#     [--github-user <github-username>]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOURCES_DIR="$SCRIPT_DIR/../resources"

TARGET_DIR=""
KIND="web-app"
FRONTEND="angular"
FIREBASE_MIGRATION="false"
REALTIME_SYNC="false"
SKIP_IAC="false"
SKIP_RPC="false"
LAYOUT="single"
PUBLISH="homebrew"
GITHUB_USER="tstapler"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) TARGET_DIR="$2"; shift 2 ;;
    --kind) KIND="$2"; shift 2 ;;
    --frontend) FRONTEND="$2"; shift 2 ;;
    --firebase-migration) FIREBASE_MIGRATION="true"; shift ;;
    --realtime-sync) REALTIME_SYNC="true"; shift ;;
    --skip-iac) SKIP_IAC="true"; shift ;;
    --skip-rpc) SKIP_RPC="true"; shift ;;
    --layout) LAYOUT="$2"; shift 2 ;;
    --publish) PUBLISH="$2"; shift 2 ;;
    --github-user) GITHUB_USER="$2"; shift 2 ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$TARGET_DIR" ]]; then
  echo "Usage: bootstrap.sh --dir <target-directory> [options]" >&2
  exit 1
fi

if [[ -e "$TARGET_DIR" && -n "$(ls -A "$TARGET_DIR" 2>/dev/null)" ]]; then
  echo "Refusing to scaffold into a non-empty existing directory: $TARGET_DIR" >&2
  exit 1
fi

if [[ "$KIND" == "lib-cli-mcp" ]]; then
  PROJECT_NAME="$(basename "$TARGET_DIR")"
  LIB_RESOURCES="$RESOURCES_DIR/lib-cli-mcp"
  mkdir -p "$TARGET_DIR"/.github/workflows
  cd "$TARGET_DIR"

  echo "==> Rust project ($LAYOUT layout)"
  cp "$LIB_RESOURCES/rust-toolchain.toml" rust-toolchain.toml
  cp "$LIB_RESOURCES/gitignore.template" .gitignore

  if [[ "$LAYOUT" == "multi" ]]; then
    mkdir -p crates/cli/src crates/core/src
    sed "s/{{PROJECT_NAME}}/${PROJECT_NAME}/g" "$LIB_RESOURCES/workspace-Cargo.toml.template" > Cargo.toml
    sed "s/{{PROJECT_NAME}}/${PROJECT_NAME}/g" "$LIB_RESOURCES/core-Cargo.toml.template" > crates/core/Cargo.toml
    sed "s/{{PROJECT_NAME}}/${PROJECT_NAME}/g" "$LIB_RESOURCES/core-lib.rs.template" > crates/core/src/lib.rs
    sed "s/{{PROJECT_NAME}}/${PROJECT_NAME}/g" "$LIB_RESOURCES/cli-Cargo.toml.template" > crates/cli/Cargo.toml
    sed "s/{{PROJECT_NAME}}/${PROJECT_NAME}/g" "$LIB_RESOURCES/cli-main.rs.template" > crates/cli/src/main.rs
    echo "    Multi-crate workspace: crates/{cli,core}. Add crates/native or"
    echo "    crates/wasm later only if this project actually needs native"
    echo "    bindings or a WASM target — see tstapler/stapler-mcp's"
    echo "    crates/{cli,core,native,wasm} as the reference layout; this"
    echo "    script doesn't template those two since they're genuinely"
    echo "    project-specific (which native runtime, which WASM target)."
    CORE_CRATE_NOTE=" (see \`crates/core/\`)"
  else
    sed "s/{{PROJECT_NAME}}/${PROJECT_NAME}/g" "$LIB_RESOURCES/Cargo-single.toml.template" > Cargo.toml
    mkdir -p src
    sed "s/{{PROJECT_NAME}}/${PROJECT_NAME}/g" "$LIB_RESOURCES/main.rs.template" > src/main.rs
    CORE_CRATE_NOTE=""
  fi

  echo "==> Release: cargo-dist + git-cliff, human-pushed tags (see RELEASE.md)"
  sed "s/{{GITHUB_USER}}/${GITHUB_USER}/g" "$LIB_RESOURCES/dist-workspace.toml.template" > dist-workspace.toml
  cp "$LIB_RESOURCES/cliff.toml" cliff.toml
  sed "s/{{PROJECT_NAME}}/${PROJECT_NAME}/g; s/{{GITHUB_USER}}/${GITHUB_USER}/g" "$LIB_RESOURCES/RELEASE.md.template" > RELEASE.md
  echo "    NOTE: .github/workflows/release.yml is NOT written by this script —"
  echo "    run 'dist init' then 'dist generate' after scaffolding (see RELEASE.md)."
  IFS=',' read -ra PUBLISH_TARGETS <<< "$PUBLISH"
  for target in "${PUBLISH_TARGETS[@]}"; do
    case "$target" in
      crates) echo "    Publish target: crates.io — set a CARGO_REGISTRY_TOKEN repo secret." ;;
      npm) echo "    Publish target: npm — set an NPM_TOKEN repo secret." ;;
      homebrew) echo "    Publish target: Homebrew tap ${GITHUB_USER}/homebrew-tap — set a HOMEBREW_TAP_TOKEN repo secret." ;;
      *) echo "    Unknown publish target: $target" >&2 ;;
    esac
  done

  echo "==> CI: PR test gate (fmt/clippy/test) — separate from the tag-triggered release workflow"
  cp "$LIB_RESOURCES/ci.yml" .github/workflows/ci.yml

  echo "==> Pre-commit: Lefthook"
  cp "$LIB_RESOURCES/lefthook.yml" lefthook.yml

  echo "==> README.md, CLAUDE.md, AGENTS.md"
  sed "s/{{PROJECT_NAME}}/${PROJECT_NAME}/g; s/{{GITHUB_USER}}/${GITHUB_USER}/g; s/{{DESCRIPTION}}/CLI \/ MCP tool./g" "$LIB_RESOURCES/README.md.template" > README.md
  sed "s/{{LAYOUT}}/${LAYOUT}-crate/g; s|{{CORE_CRATE_NOTE}}|${CORE_CRATE_NOTE}|g" "$LIB_RESOURCES/CLAUDE.md.template" > CLAUDE.md
  sed "s/{{LAYOUT}}/${LAYOUT}-crate/g; s|{{CORE_CRATE_NOTE}}|${CORE_CRATE_NOTE}|g" "$LIB_RESOURCES/AGENTS.md.template" > AGENTS.md

  cat > LICENSE <<EOF
MIT License

Copyright (c) $(date +%Y 2>/dev/null || echo "2026") Tyler Stapler

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to
deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
EOF

  echo ""
  echo "Done. Scaffolded into: $TARGET_DIR"
  echo "Next: cd $TARGET_DIR && cargo check, then read RELEASE.md before your first tag."
  exit 0
fi

mkdir -p "$TARGET_DIR"/{backend/api/src/{routes,db,domain},backend/migrator/src,backend/migrations,.github/workflows}
cd "$TARGET_DIR"

echo "==> Backend: Rust + Axum workspace"
cp "$RESOURCES_DIR/Cargo.toml.template" backend/Cargo.toml
cat > backend/rust-toolchain.toml <<'EOF'
[toolchain]
channel = "stable"
components = ["clippy", "rustfmt"]
EOF
cat > backend/deny.toml <<'EOF'
# Fill in as license/dependency policy decisions come up.
# https://embarkstudios.github.io/cargo-deny/
[licenses]
allow = ["MIT", "Apache-2.0", "BSD-3-Clause", "ISC", "Unicode-3.0"]

[bans]
multiple-versions = "warn"
EOF

echo "==> Migrations: sqlx-cli + a standalone migrator binary (Cloud Run Job entrypoint)"
cp "$RESOURCES_DIR/migrator-Cargo.toml.template" backend/migrator/Cargo.toml
cp "$RESOURCES_DIR/migrator-main.rs.template" backend/migrator/src/main.rs
cp "$RESOURCES_DIR/migrations/0001_init.sql.template" backend/migrations/0001_init.sql

if [[ "$SKIP_RPC" != "true" ]]; then
  echo "==> RPC: Connect-RPC (unary/server-streaming) + WebSocket (bidi streaming)"
  echo "    NOTE: the Connect-RPC Rust crate side is experimental — see"
  echo "    backend/CONNECT_RPC_NOTE.md before extending it. The WebSocket"
  echo "    transport (ws.rs) is plain Axum + prost, smoke-tested, safe to build on."
  mkdir -p proto/greet/v1
  cp "$RESOURCES_DIR"/proto/buf.yaml proto/buf.yaml
  cp "$RESOURCES_DIR"/proto/buf.gen.yaml proto/buf.gen.yaml
  cp "$RESOURCES_DIR"/proto/greet/v1/greet.proto proto/greet/v1/greet.proto
  cp "$RESOURCES_DIR/api-Cargo-rpc.toml.template" backend/api/Cargo.toml
  cp "$RESOURCES_DIR/main-rpc.rs.template" backend/api/src/main.rs
  cp "$RESOURCES_DIR/ws.rs.template" backend/api/src/ws.rs
  cp "$RESOURCES_DIR/build.rs.template" backend/api/build.rs
  cp "$RESOURCES_DIR/CONNECT_RPC_NOTE.md.template" backend/CONNECT_RPC_NOTE.md
else
  cp "$RESOURCES_DIR/api-Cargo.toml.template" backend/api/Cargo.toml
  cp "$RESOURCES_DIR/main.rs.template" backend/api/src/main.rs
fi

echo "==> Frontend"
if [[ "$FRONTEND" == "angular" ]]; then
  if command -v ng >/dev/null 2>&1; then
    ng new frontend --directory=frontend --style=css --routing=true --skip-git
  else
    echo "    Angular CLI not found — run manually:"
    echo "      npx -p @angular/cli ng new frontend --directory=frontend --routing=true"
  fi
  echo "22" > frontend/.nvmrc 2>/dev/null || mkdir -p frontend && echo "22" > frontend/.nvmrc
  if [[ "$SKIP_RPC" != "true" ]]; then
    mkdir -p frontend/src/app/rpc
    cp "$RESOURCES_DIR/frontend-rpc/connect-client.ts.template" frontend/src/app/rpc/connect-client.ts
    cp "$RESOURCES_DIR/frontend-rpc/ws-client.ts.template" frontend/src/app/rpc/ws-client.ts
  fi
else
  echo "    Compose Multiplatform / Web chosen — this path is lower-confidence"
  echo "    (Beta as of 2026), no first-party template bundled with this skill."
  echo "    Clone JetBrains' starter instead:"
  echo "      git clone https://github.com/Kotlin/kotlin-wasm-compose-template frontend"
  echo "    Then remove its .git directory and adapt to this repo."
  echo "    RPC client scaffolding (frontend-rpc/*.ts) targets Angular/TS and"
  echo "    was not copied — adapt the Kotlin/KMP equivalent yourself if needed."
fi

echo "==> Local dev: Neon Local (docker-compose.yml) — real ephemeral Neon branch, not an offline emulator"
cp "$RESOURCES_DIR/docker-compose.yml.template" docker-compose.yml
cp "$RESOURCES_DIR/env.example.template" .env.example
cp "$RESOURCES_DIR/envrc.template" .envrc

echo "==> CI/CD, dev container, pre-commit"
cp "$RESOURCES_DIR/github-actions-ci.yml" .github/workflows/ci.yml
cp "$RESOURCES_DIR/Dockerfile.dev" Dockerfile.dev
cp "$RESOURCES_DIR/lefthook.yml" lefthook.yml

echo "==> CLAUDE.md / AGENTS.md"
sed "s/{{FRONTEND}}/${FRONTEND}/g" "$RESOURCES_DIR/CLAUDE.md.template" > CLAUDE.md
sed "s/{{FRONTEND}}/${FRONTEND}/g" "$RESOURCES_DIR/AGENTS.md.template" > AGENTS.md

if [[ "$SKIP_IAC" != "true" ]]; then
  echo "==> IaC (OpenTofu — modules/app + environments/{staging,prod}, TODO placeholders must be filled before apply)"
  mkdir -p iac/modules iac/environments
  cp -r "$RESOURCES_DIR"/opentofu-modules/app iac/modules/app
  cp -r "$RESOURCES_DIR"/opentofu-modules/environments/staging iac/environments/staging
  cp -r "$RESOURCES_DIR"/opentofu-modules/environments/prod iac/environments/prod
fi

if [[ "$FIREBASE_MIGRATION" == "true" ]]; then
  cat > AUTH.md <<'EOF'
# Auth: Ory Kratos (Firebase Auth replacement)

See reference.md in the code-new-project skill for the Ory Kratos vs.
Zitadel decision. Kratos is headless — you build the login/registration/
MFA screens yourself in the Angular app against its API.

Setup: https://www.ory.sh/docs/kratos/quickstart
EOF
  if [[ "$REALTIME_SYNC" == "true" ]]; then
    cat > SYNC.md <<'EOF'
# Realtime/offline sync: PowerSync (Firestore listener replacement)

Only added because the interview confirmed this app needs Firestore-style
realtime listeners, not just plain CRUD. Full bidirectional Postgres<->
client-SQLite sync, official Kotlin Multiplatform SDK.

Setup: https://docs.powersync.com/
EOF
  fi
fi

cat > README.md <<EOF
# $(basename "$TARGET_DIR")

Scaffolded by the \`code-new-project\` skill against Tyler's default app
stack. See that skill's \`reference.md\` for the full rationale, and
\`CLAUDE.md\`/\`AGENTS.md\` for the development workflow (feature planning
via /sdd:full, journey docs via journeys-extract, brand via
pm-brand-strategy).

## Stack

- Frontend: ${FRONTEND}
- Backend: Rust + Axum + sqlx (backend/api/), migrations via a standalone binary (backend/migrator/)
$(if [[ "$SKIP_RPC" != "true" ]]; then echo "- RPC: Connect-RPC (unary/server-streaming, EXPERIMENTAL — see backend/CONNECT_RPC_NOTE.md) + WebSocket (bidi streaming, backend/api/src/ws.rs)"; fi)
- Compute: GCP Cloud Run, one GCP project per environment (iac/environments/{staging,prod})
- Data: Neon Postgres — one project, branch per environment (iac/modules/app/neon.tf) + Cloudflare R2 (iac/modules/app/r2.tf)
- Local dev: Neon Local (docker-compose.yml) — a real ephemeral Neon branch, not an offline emulator; needs network access
- CI/CD: GitHub Actions, path-filtered (.github/workflows/ci.yml) — staging auto-deploys on merge to main via Workload Identity Federation + \`tofu apply\`; prod is a manual \`workflow_dispatch\` promotion
- Pre-commit: Lefthook (lefthook.yml) — run \`lefthook install\` after cloning
- Secrets: direnv + .env locally (\`cp .env.example .env\`, fill in, \`direnv allow\`) — see reference.md to upgrade to 1Password CLI

## Before this actually runs

- [ ] Create the Neon project itself (this scaffold's IaC manages BRANCHES within an existing project, not the project) and note its ID + default branch ID for \`iac/environments/*/main.tf\`
- [ ] Create one GCP project per environment (staging, prod) — do not share one GCP project across environments, see reference.md
- [ ] Fill in \`iac/environments/{staging,prod}/main.tf\` and \`terraform.tfvars\` TODOs
- [ ] Configure a remote OpenTofu state backend per environment (each \`versions.tf\` has a commented GCS backend block — use separate buckets/prefixes per environment, not shared state)
- [ ] Set up Workload Identity Federation for GitHub Actions -> GCP (google-github-actions/auth@v3, ~15 min one-time setup) and set the \`GCP_WORKLOAD_IDENTITY_PROVIDER\`/\`GCP_DEPLOY_SERVICE_ACCOUNT\` repo variables
- [ ] Set repo variables: \`GCP_REGION\`, \`GCP_PROJECT_ID_STAGING\`, \`PROJECT_NAME\`, \`NEON_PROJECT_ID\`, \`NEON_PROD_BRANCH_ID\`
- [ ] Set repo secrets: \`NEON_API_KEY\`, \`CLOUDFLARE_API_TOKEN\` (the official Neon GitHub integration can auto-create the Neon ones — see reference.md)
- [ ] \`cp .env.example .env\`, fill in, \`direnv allow\`
- [ ] \`docker compose up\` to start Neon Local for day-to-day dev
- [ ] \`cargo install sqlx-cli\`, then \`cargo sqlx prepare --workspace\` after any query change (commit the \`.sqlx/\` cache)
- [ ] \`cd frontend && npm install\`
$(if [[ "$SKIP_RPC" != "true" ]]; then cat <<'RPC'
- [ ] Read backend/CONNECT_RPC_NOTE.md before extending the Connect-RPC side — it's unverified against the real crate API
- [ ] Install buf (https://buf.build/docs/installation) and run `buf generate` from proto/ to produce TS + Rust message types
- [ ] `cd frontend && npm install @connectrpc/connect @connectrpc/connect-web @bufbuild/protobuf`
RPC
fi)
$(if [[ "$FIREBASE_MIGRATION" == "true" ]]; then echo "- [ ] Set up Ory Kratos — see AUTH.md"; fi)
$(if [[ "$REALTIME_SYNC" == "true" ]]; then echo "- [ ] Set up PowerSync — see SYNC.md"; fi)
- [ ] Run \`pm-brand-strategy\` to set the project's brand/marketing direction (see CLAUDE.md)
- [ ] Run \`journeys-extract\` once real features exist, to start docs/journeys/
EOF

echo ""
echo "Done. Scaffolded into: $TARGET_DIR"
echo "See README.md there for the manual setup steps still required."
