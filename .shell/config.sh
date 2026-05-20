# Non-secret environment config — committed to dotfiles
# Secrets live in secrets.op.sh.tpl (injected via 1Password)

# ── Identity ──────────────────────────────────────────────────────────────────
export GITHUB_USERNAME=TylerStaplerAtFanatics
export GITHUB_USER=${GITHUB_USERNAME}
export GITHUB_ACTOR=${GITHUB_USERNAME}
export GITHUB_EMAIL="tyler.stapler@betfanatics.com"

export BITBUCKET_USER=tstapler

export JIRA_EMAIL="tyler.stapler@betfanatics.com"
export JIRA_USERNAME="${JIRA_EMAIL}"
export JIRA_URL="https://betfanatics.atlassian.net"

export CONFLUENCE_URL="${JIRA_URL}/wiki"
export CONFLUENCE_USERNAME="${JIRA_EMAIL}"

export AMELCO_ARTIFACTORY_USERNAME="tstapler"

export SONAR_ORG="fanatics-gaming"

export OKTA_CLIENT_ID="0oawfyipm6wiY69Pm697"

# ── Services ──────────────────────────────────────────────────────────────────
export OLLAMA_API_BASE="http://127.0.0.1:11434"
export LW_ACCOUNT="betfanatics.lacework.net"

# ── PATH additions ────────────────────────────────────────────────────────────
pathadd "$HOME/.rd/bin"
export PATH="$PATH"
