#!/usr/bin/env bash
# scan_litellm_vuln.sh
# Scans GitHub repos (org and/or user) for litellm dependency pinned to
# compromised versions 1.82.7 or 1.82.8 (supply chain attack, 2026-03-23).
#
# Reference: https://github.com/BerriAI/litellm/issues/24518
#
# Usage:
#   ./scan_litellm_vuln.sh [--org ORG] [--user USER] [--all]
#
# Flags:
#   --org ORG    Scan all repos in ORG (default: fanatics-gaming)
#   --user USER  Scan personal repos for USER (default: current gh user)
#   --all        Scan both org and personal repos
#   --help       Show this help
#
# Requires: gh CLI (authenticated), python3 (optional, for lockfile parsing)

set -euo pipefail

COMPROMISED_VERSIONS=("1.82.7" "1.82.8")
DEFAULT_ORG="fanatics-gaming"
RESULTS_FILE="/tmp/litellm_scan_results_$(date +%Y%m%d_%H%M%S).txt"
TMPDIR_SCAN=$(mktemp -d)
trap 'rm -rf "$TMPDIR_SCAN"' EXIT

SCAN_ORG=false
SCAN_USER=false
ORG_NAME="$DEFAULT_ORG"
USER_NAME=""

# ── Argument parsing ──────────────────────────────────────────────────────────
usage() {
  grep '^#' "$0" | grep -v '^#!/' | sed 's/^# \?//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --org)   SCAN_ORG=true;  ORG_NAME="${2:-$DEFAULT_ORG}";  shift 2 ;;
    --user)  SCAN_USER=true; USER_NAME="${2:-}";             shift 2 ;;
    --all)   SCAN_ORG=true;  SCAN_USER=true;                 shift   ;;
    --help)  usage ;;
    *)       echo "Unknown flag: $1"; usage ;;
  esac
done

# Default: scan both if nothing specified
if [[ "$SCAN_ORG" == false && "$SCAN_USER" == false ]]; then
  SCAN_ORG=true
  SCAN_USER=true
fi

if [[ -z "$USER_NAME" ]]; then
  USER_NAME=$(gh api user --jq '.login' 2>/dev/null || echo "")
fi

# ── Helpers ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

FINDINGS=0
CHECKED_REPOS=0

log()    { echo -e "${CYAN}[scan]${NC} $*"; }
warn()   { echo -e "${YELLOW}[warn]${NC} $*" | tee -a "$RESULTS_FILE"; }
alert()  { echo -e "${RED}${BOLD}[VULN]${NC} $*" | tee -a "$RESULTS_FILE"; FINDINGS=$((FINDINGS + 1)); }
ok()     { echo -e "${GREEN}[ok]${NC}   $*"; }

# Check if a version string matches compromised versions
is_compromised_version() {
  local content="$1"
  for ver in "${COMPROMISED_VERSIONS[@]}"; do
    if echo "$content" | grep -qiE "litellm[^,\n]*[=~^<>!]*\s*${ver//./\\.}([^0-9]|$)"; then
      echo "$ver"
      return 0
    fi
  done
  return 1
}

# Check if content references litellm at all (any version)
has_litellm() {
  echo "$1" | grep -qi "litellm"
}

# Fetch and scan a single file from a repo via GitHub API
scan_file() {
  local repo="$1"
  local filepath="$2"
  local content

  content=$(gh api "repos/${repo}/contents/${filepath}" --jq '.content' 2>/dev/null | base64 -d 2>/dev/null) || return

  if ! has_litellm "$content"; then
    return
  fi

  local matched_ver
  if matched_ver=$(is_compromised_version "$content"); then
    alert "COMPROMISED: ${repo} → ${filepath}  (litellm==${matched_ver})"
  else
    # Has litellm but not pinned to compromised version — still worth noting
    local ver_line
    ver_line=$(echo "$content" | grep -i "litellm" | head -3 | tr '\n' ' ')
    warn "litellm found (non-compromised): ${repo} → ${filepath}  [${ver_line}]"
  fi
}

# Scan a single repo for all relevant dependency files
scan_repo() {
  local repo="$1"
  CHECKED_REPOS=$((CHECKED_REPOS + 1))

  # Files to check for litellm dependency declarations
  local files=(
    "requirements.txt"
    "requirements-dev.txt"
    "requirements/base.txt"
    "requirements/prod.txt"
    "requirements/dev.txt"
    "pyproject.toml"
    "setup.cfg"
    "setup.py"
    "Pipfile"
    "Pipfile.lock"
    "poetry.lock"
    "uv.lock"
    ".github/workflows"  # Check CI for pip install litellm==X.Y.Z
  )

  for f in "${files[@]}"; do
    scan_file "$repo" "$f"
  done

  # Also use GitHub code search for inline pip install commands in CI workflows
  scan_workflows "$repo"
}

# Scan GitHub Actions workflow files for compromised pip install commands
scan_workflows() {
  local repo="$1"
  local workflow_list

  workflow_list=$(gh api "repos/${repo}/contents/.github/workflows" --jq '.[].name' 2>/dev/null) || return

  while IFS= read -r wf; do
    [[ -z "$wf" ]] && continue
    scan_file "$repo" ".github/workflows/${wf}"
  done <<< "$workflow_list"
}

# Fetch all repos for an org (handles pagination)
get_org_repos() {
  local org="$1"
  gh api --paginate "orgs/${org}/repos" \
    --jq '.[].full_name' 2>/dev/null
}

# Fetch all personal repos for a user
get_user_repos() {
  local user="$1"
  gh api --paginate "users/${user}/repos" \
    --jq '.[].full_name' 2>/dev/null
}

# ── GitHub Code Search (faster broad scan) ────────────────────────────────────
code_search_org() {
  local org="$1"
  log "Running GitHub code search in org: ${org}..."

  for ver in "${COMPROMISED_VERSIONS[@]}"; do
    local results
    results=$(gh api \
      "search/code?q=litellm==${ver}+org:${org}&per_page=100" \
      --jq '.items[] | "\(.repository.full_name) → \(.path)"' 2>/dev/null) || true

    if [[ -n "$results" ]]; then
      while IFS= read -r line; do
        alert "CODE SEARCH HIT (${ver}): ${line}"
      done <<< "$results"
    fi
  done
}

code_search_user() {
  local user="$1"
  log "Running GitHub code search for user: ${user}..."

  for ver in "${COMPROMISED_VERSIONS[@]}"; do
    local results
    results=$(gh api \
      "search/code?q=litellm==${ver}+user:${user}&per_page=100" \
      --jq '.items[] | "\(.repository.full_name) → \(.path)"' 2>/dev/null) || true

    if [[ -n "$results" ]]; then
      while IFS= read -r line; do
        alert "CODE SEARCH HIT (${ver}): ${line}"
      done <<< "$results"
    fi
  done
}

# ── Main ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  LiteLLM Supply Chain Vulnerability Scanner              ║${NC}"
echo -e "${BOLD}║  Checking for compromised versions: 1.82.7, 1.82.8       ║${NC}"
echo -e "${BOLD}║  Reference: github.com/BerriAI/litellm/issues/24518      ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Results will be saved to: $RESULTS_FILE"
echo "$(date)" > "$RESULTS_FILE"
echo "LiteLLM vulnerability scan (compromised: 1.82.7, 1.82.8)" >> "$RESULTS_FILE"
echo "=========================================================" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Phase 1: Fast GitHub code search (catches most cases immediately)
if [[ "$SCAN_ORG" == true ]]; then
  code_search_org "$ORG_NAME"
fi
if [[ "$SCAN_USER" == true && -n "$USER_NAME" ]]; then
  code_search_user "$USER_NAME"
fi

# Phase 2: Per-repo file scan (catches lockfiles, indirect pinning)
if [[ "$SCAN_ORG" == true ]]; then
  log "Fetching repo list for org: ${ORG_NAME}..."
  mapfile -t ORG_REPOS < <(get_org_repos "$ORG_NAME")
  log "Found ${#ORG_REPOS[@]} repos in ${ORG_NAME}, scanning dependency files..."
  for repo in "${ORG_REPOS[@]}"; do
    log "  Scanning: ${repo}"
    scan_repo "$repo"
  done
fi

if [[ "$SCAN_USER" == true && -n "$USER_NAME" ]]; then
  log "Fetching personal repos for: ${USER_NAME}..."
  mapfile -t USER_REPOS < <(get_user_repos "$USER_NAME")
  log "Found ${#USER_REPOS[@]} personal repos, scanning dependency files..."
  for repo in "${USER_REPOS[@]}"; do
    log "  Scanning: ${repo}"
    scan_repo "$repo"
  done
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}Scan complete${NC}"
echo "  Repos checked:    $CHECKED_REPOS"
if [[ "$FINDINGS" -gt 0 ]]; then
  echo -e "  ${RED}${BOLD}FINDINGS: $FINDINGS${NC}  ← IMMEDIATE ACTION REQUIRED"
  echo ""
  echo -e "${BOLD}Recommended actions:${NC}"
  echo "  1. Pin litellm to a safe version: >=1.82.9 or <=1.82.6"
  echo "  2. Rotate ALL secrets in affected repos (API keys, AWS creds, SSH keys)"
  echo "  3. Check for unauthorized access in cloud provider audit logs"
  echo "  4. Search for litellm_init.pth in your deployed environments"
  echo "  5. Review git history for any unexpected changes"
  echo ""
  echo "Full findings saved to: $RESULTS_FILE"
else
  echo -e "  ${GREEN}${BOLD}No compromised versions found.${NC}"
  echo ""
  echo "Note: If any repos use litellm WITHOUT a pinned version, they may have"
  echo "pulled a compromised version at install time. Check deployment logs."
fi
echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"
