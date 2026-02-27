#!/usr/bin/env sh
# Configure SSH to use ~/.ssh/personal for github.com:tstapler/* repos.
#
# This script:
#   1. Adds a 'github-personal' Host alias to ~/.ssh/config
#   2. Updates any tstapler git remotes to use that alias
#
# Safe to run multiple times — existing config is not overwritten.

set -e

SSH_CONFIG="$HOME/.ssh/config"
PERSONAL_KEY="$HOME/.ssh/personal"
DOTFILES_DIR="$HOME/dotfiles"

# ---------------------------------------------------------------------------
# 1. Ensure the personal key exists
# ---------------------------------------------------------------------------
if [ ! -f "$PERSONAL_KEY" ]; then
  echo "⚠️  Warning: $PERSONAL_KEY does not exist."
  echo "   Generate it with: ssh-keygen -t ed25519 -f $PERSONAL_KEY -C 'personal'"
  echo "   Then add the public key to your GitHub account before continuing."
  exit 1
fi

# ---------------------------------------------------------------------------
# 2. Add github-personal Host block to ~/.ssh/config (idempotent)
# ---------------------------------------------------------------------------
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if grep -q "Host github-personal" "$SSH_CONFIG" 2>/dev/null; then
  echo "✓ ~/.ssh/config already has github-personal Host entry"
else
  printf '\nHost github-personal\n    HostName github.com\n    IdentityFile %s\n    IdentitiesOnly yes\n' "$PERSONAL_KEY" >> "$SSH_CONFIG"
  chmod 600 "$SSH_CONFIG"
  echo "✓ Added github-personal Host entry to ~/.ssh/config"
fi

# ---------------------------------------------------------------------------
# 3. Update git remotes in tstapler repos to use github-personal
# ---------------------------------------------------------------------------
update_remote() {
  repo_dir="$1"
  if [ ! -d "$repo_dir/.git" ] && [ ! -f "$repo_dir/.git" ]; then
    echo "  Skipping $repo_dir (not a git repo)"
    return
  fi

  changed=0
  found=0
  while IFS= read -r line; do
    remote=$(echo "$line" | awk '{print $1}')
    url=$(echo "$line" | awk '{print $2}')

    # Match any remote pointing to github.com:tstapler/ (but not already using the alias)
    case "$url" in
      git@github.com:tstapler/*)
        new_url=$(echo "$url" | sed 's|git@github.com:tstapler/|git@github-personal:tstapler/|')
        git -C "$repo_dir" remote set-url "$remote" "$new_url"
        echo "  Updated $remote: $url -> $new_url"
        changed=1
        found=1
        ;;
      git@github-personal:tstapler/*)
        echo "  $remote already uses github-personal alias"
        found=1
        ;;
    esac
  done << EOF
$(git -C "$repo_dir" remote -v | grep "(push)" | awk '{print $1, $2}')
EOF

  if [ "$found" = "0" ]; then
    echo "  No tstapler remotes found in $repo_dir"
  fi
}

echo ""
echo "Updating git remotes..."
update_remote "$DOTFILES_DIR"
update_remote "$DOTFILES_DIR/cfgcaddy"

# ---------------------------------------------------------------------------
# 4. Test the connection
# ---------------------------------------------------------------------------
echo ""
echo "Testing github-personal SSH connection..."
if ssh -T git@github-personal 2>&1 | grep -q "successfully authenticated"; then
  echo "✅ SSH connection to github-personal works"
else
  echo "⚠️  SSH test returned unexpected output — check that your key is added to GitHub"
fi
