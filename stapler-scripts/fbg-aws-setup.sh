#!/usr/bin/env bash
# FBG AWS CLI Setup
# Docs: https://betfanatics.atlassian.net/wiki/spaces/Platform/pages/651001880
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${BLUE}▶ $*${NC}"; }
success() { echo -e "${GREEN}✓ $*${NC}"; }
warn()    { echo -e "${YELLOW}⚠ $*${NC}"; }
die()     { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }
header()  { echo -e "\n${BOLD}$*${NC}"; }

# ── 1. HOMEBREW ─────────────────────────────────────────────────────────────
header "Step 1: Homebrew"
if ! command -v brew &>/dev/null; then
  info "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
  success "Homebrew already installed"
fi

# ── 2. GITHUB AUTH ──────────────────────────────────────────────────────────
header "Step 2: GitHub Authentication"
brew install gh &>/dev/null || true

if gh auth status &>/dev/null; then
  success "Already authenticated with GitHub"
else
  info "Choose SSH (recommended) or HTTPS when prompted by gh auth login"
  gh auth login --hostname github.com
fi

# ── 3. FANATICS-GAMING SSO ──────────────────────────────────────────────────
header "Step 3: fanatics-gaming SSO Authorization"
echo ""
warn "You must authorize your SSH/token for the fanatics-gaming GitHub org."
echo -e "  ${BOLD}→ https://github.com/settings/keys${NC}"
echo ""
echo "  1. Find your key in the list"
echo "  2. Click 'Configure SSO' → 'Authorize' next to fanatics-gaming"
echo ""
read -rp "Press Enter once you've authorized SSO..."

# Verify access
info "Verifying fanatics-gaming access..."
if ! git ls-remote git@github.com:fanatics-gaming/homebrew-tap.git HEAD &>/dev/null 2>&1; then
  # Try HTTPS fallback
  if ! git ls-remote https://github.com/fanatics-gaming/homebrew-tap.git HEAD &>/dev/null 2>&1; then
    die "Cannot reach fanatics-gaming/homebrew-tap. Check SSO authorization and try again."
  fi
  PROTOCOL="https"
  warn "SSH not available — using HTTPS for homebrew tap"
else
  PROTOCOL="ssh"
  success "fanatics-gaming SSO access confirmed (SSH)"
fi

# ── 4. INSTALL AWS TOOLS ────────────────────────────────────────────────────
header "Step 4: Install AWS Tools"
info "Installing aws-sso-util, aws-vault, awscli..."
brew install aws-sso-util aws-vault awscli
success "AWS tools installed"

# ── 5. FANATICS-GAMING HOMEBREW TAP ─────────────────────────────────────────
header "Step 5: fanatics-gaming Homebrew Tap"
if [[ "$PROTOCOL" == "ssh" ]]; then
  brew tap fanatics-gaming/homebrew-tap git@github.com:fanatics-gaming/homebrew-tap
else
  brew tap fanatics-gaming/homebrew-tap https://github.com/fanatics-gaming/homebrew-tap
fi
brew install fanatics-gaming/homebrew-tap/fbg-platform-tools
success "fbg CLI installed"

# ── 6. POPULATE AWS PROFILES ────────────────────────────────────────────────
header "Step 6: Populate AWS Profiles (Okta login required)"
fbg aws populate-profiles
success "AWS profiles configured"

# ── 7. OPTIONAL: BIOMETRICS ─────────────────────────────────────────────────
header "Step 7: Optional — Touch ID for aws-vault"
if ! grep -q "AWS_VAULT_BIOMETRICS" "${HOME}/.zshrc" 2>/dev/null; then
  read -rp "Enable Touch ID for aws-vault? (y/N) " -n 1 REPLY; echo
  if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    echo 'export AWS_VAULT_BIOMETRICS=true' >> "${HOME}/.zshrc"
    success "Added to ~/.zshrc — restart your shell to apply"
  fi
fi

echo ""
success "Setup complete! Test with:"
echo "  aws-vault exec <profile> -- aws sts get-caller-identity"
echo ""
info "List your profiles with: aws-vault list"
