#!/usr/bin/env zsh
# One-time migration: move secrets from local.sh into 1Password + macOS Keychain.
#
# Usage:
#   1. Make sure your OLD local.sh (with hardcoded secrets) is still sourced:
#        source ~/.shell/local.sh   # if not already in your current shell
#   2. Sign into 1Password:
#        eval "$(op signin --account my)"
#   3. Run this script:
#        ~/.shell/setup_1password.sh
#
# What it does:
#   - Creates items in 1Password (vault: "Personal", account: "my")
#   - Stores copies in macOS Keychain as a fallback (account: "dotfiles")
#   - Skips items that already exist in 1Password

set -euo pipefail

VAULT="Personal"
ACCOUNT="my"
KEYCHAIN_ACCOUNT="dotfiles"

_green()  { print -P "%F{green}$*%f" }
_yellow() { print -P "%F{yellow}$*%f" }
_red()    { print -P "%F{red}$*%f" }

# ── Verify signed in ───────────────────────────────────────────────────────────
if ! op whoami --account="$ACCOUNT" &>/dev/null 2>&1; then
  _red "Not signed into 1Password. Run: eval \$(op signin --account $ACCOUNT)"
  exit 1
fi
_green "✓ Signed in to 1Password ($ACCOUNT)"

# ── Helpers ───────────────────────────────────────────────────────────────────

# Create a 1Password item with one field named "credential"
op_create_single() {
  local title="$1" value="$2"
  [[ -z "$value" ]] && { _yellow "  skip $title (empty)"; return; }
  if op item get "$title" --vault="$VAULT" --account="$ACCOUNT" &>/dev/null 2>&1; then
    _yellow "  exists $title"
  else
    op item create \
      --category="API Credential" \
      --title="$title" \
      --vault="$VAULT" \
      --account="$ACCOUNT" \
      "credential[password]=$value" &>/dev/null
    _green "  created $title"
  fi
}

# Create a 1Password item with multiple named fields
op_create_multi() {
  local title="$1"; shift
  # remaining args: "field_name=value" pairs
  if op item get "$title" --vault="$VAULT" --account="$ACCOUNT" &>/dev/null 2>&1; then
    _yellow "  exists $title"
    return
  fi
  local args=()
  local has_value=false
  for pair in "$@"; do
    local val="${pair#*=}"
    [[ -n "$val" ]] && has_value=true
    args+=("${pair%%=*}[password]=$val")
  done
  if [[ "$has_value" == false ]]; then
    _yellow "  skip $title (all fields empty)"
    return
  fi
  op item create \
    --category="API Credential" \
    --title="$title" \
    --vault="$VAULT" \
    --account="$ACCOUNT" \
    "${args[@]}" &>/dev/null
  _green "  created $title"
}

# Store in macOS Keychain (overwrites if exists)
kc_store() {
  local svc="$1" value="$2"
  [[ -z "$value" ]] && return
  security delete-generic-password -a "$KEYCHAIN_ACCOUNT" -s "$svc" &>/dev/null || true
  security add-generic-password -a "$KEYCHAIN_ACCOUNT" -s "$svc" -w "$value"
}

# ── 1Password items ───────────────────────────────────────────────────────────
echo ""
echo "Creating 1Password items in vault '$VAULT' (account: $ACCOUNT)..."

op_create_single  "GitHub PAT"          "${GITHUB_TOKEN:-}"
op_create_single  "Terraform Cloud"     "${TF_CLOUD_TOKEN:-}"
op_create_multi   "Cloudflare"          "api_key=${CLOUDFLARE_API_KEY:-}" "api_token=${CLOUDFLARE_API_TOKEN:-}"
op_create_multi   "Datadog"             "api_key=${DATADOG_API_KEY:-}" "app_key=${DATADOG_APP_KEY:-}"
op_create_single  "Twingate"            "${TWINGATE_API_TOKEN:-}"
op_create_single  "Artifactory"         "${AMELCO_ARTIFACTORY_PASSWORD:-}"
op_create_single  "Jira"               "${JIRA_TOKEN:-}"
op_create_single  "Slack Bot"           "${SLACK_TOKEN:-}"
op_create_multi   "Slack MCP"           "xoxc=${SLACK_MCP_XOXC_TOKEN:-}" "xoxd=${SLACK_MCP_XOXD_TOKEN:-}"
op_create_multi   "Okta"               "api_token=${OKTA_TOKEN:-}" "client_secret=${OKTA_CLIENT_SECRET:-}"
op_create_single  "Geekbot"            "${GEEKBOT_TOKEN:-}"
op_create_multi   "Lacework"           "api_key=${LW_API_KEY:-}" "api_secret=${LW_API_SECRET:-}"
op_create_single  "OpenAI"             "${OPENAI_API_KEY:-}"
op_create_single  "Gemini"             "${GEMINI_API_KEY:-}"
op_create_single  "OpenRouter"         "${OPENROUTER_API_KEY:-}"
op_create_single  "Claude"             "${CLAUDE_CODE_OAUTH_TOKEN:-}"
op_create_single  "PagerDuty"          "${PAGERDUTY_API_KEY:-}"
op_create_single  "Bitbucket"          "${BITBUCKET_TOKEN:-}"
op_create_single  "SonarCloud"         "${SONAR_TOKEN:-}"
op_create_single  "Brave Search"       "${BRAVE_API_KEY:-}"
op_create_single  "Figma"              "${FIGMA_TOKEN:-}"

# ── Keychain fallback copies ──────────────────────────────────────────────────
echo ""
echo "Storing Keychain fallback copies (account: $KEYCHAIN_ACCOUNT)..."

kc_store "GITHUB_TOKEN"               "${GITHUB_TOKEN:-}"
kc_store "TF_CLOUD_TOKEN"             "${TF_CLOUD_TOKEN:-}"
kc_store "CLOUDFLARE_API_KEY"         "${CLOUDFLARE_API_KEY:-}"
kc_store "CLOUDFLARE_API_TOKEN"       "${CLOUDFLARE_API_TOKEN:-}"
kc_store "DATADOG_API_KEY"            "${DATADOG_API_KEY:-}"
kc_store "DATADOG_APP_KEY"            "${DATADOG_APP_KEY:-}"
kc_store "TWINGATE_API_TOKEN"         "${TWINGATE_API_TOKEN:-}"
kc_store "AMELCO_ARTIFACTORY_PASSWORD" "${AMELCO_ARTIFACTORY_PASSWORD:-}"
kc_store "JIRA_TOKEN"                 "${JIRA_TOKEN:-}"
kc_store "SLACK_TOKEN"                "${SLACK_TOKEN:-}"
kc_store "SLACK_MCP_XOXC_TOKEN"      "${SLACK_MCP_XOXC_TOKEN:-}"
kc_store "SLACK_MCP_XOXD_TOKEN"      "${SLACK_MCP_XOXD_TOKEN:-}"
kc_store "OKTA_TOKEN"                 "${OKTA_TOKEN:-}"
kc_store "OKTA_CLIENT_SECRET"         "${OKTA_CLIENT_SECRET:-}"
kc_store "GEEKBOT_TOKEN"              "${GEEKBOT_TOKEN:-}"
kc_store "LW_API_KEY"                 "${LW_API_KEY:-}"
kc_store "LW_API_SECRET"              "${LW_API_SECRET:-}"
kc_store "OPENAI_API_KEY"             "${OPENAI_API_KEY:-}"
kc_store "GEMINI_API_KEY"             "${GEMINI_API_KEY:-}"
kc_store "OPENROUTER_API_KEY"         "${OPENROUTER_API_KEY:-}"
kc_store "CLAUDE_CODE_OAUTH_TOKEN"    "${CLAUDE_CODE_OAUTH_TOKEN:-}"
kc_store "PAGERDUTY_API_KEY"          "${PAGERDUTY_API_KEY:-}"
kc_store "BITBUCKET_TOKEN"            "${BITBUCKET_TOKEN:-}"
kc_store "SONAR_TOKEN"                "${SONAR_TOKEN:-}"
kc_store "BRAVE_API_KEY"              "${BRAVE_API_KEY:-}"
kc_store "FIGMA_TOKEN"                "${FIGMA_TOKEN:-}"

_green "Keychain entries written."

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
_green "✓ Migration complete."
echo ""
echo "Next steps:"
echo "  1. Open ~/.shell/secrets.op.sh.tpl and verify the op:// item names match what was created."
echo "     (1Password item names must match exactly — check with: op item list --vault=$VAULT --account=$ACCOUNT)"
echo "  2. Test: open a new shell and confirm secrets load (e.g. echo \$GITHUB_TOKEN)"
echo "  3. Enable 1Password CLI integration in the 1Password app:"
echo "     Settings → Developer → Integrate with 1Password CLI (enables Touch ID auth)"
