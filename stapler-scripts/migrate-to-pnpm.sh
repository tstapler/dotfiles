#!/usr/bin/env bash
# migrate-to-pnpm.sh
# Finds JS projects with node_modules and converts them to pnpm's hard-linked store.
# Usage:
#   ./migrate-to-pnpm.sh                  # dry run — show what would be done
#   ./migrate-to-pnpm.sh --execute        # actually convert
#   ./migrate-to-pnpm.sh --execute --dir ~/Programming  # limit search to a directory

set -euo pipefail

EXECUTE=false
SEARCH_DIR="${HOME}"
SKIP_DIRS=("node_modules" ".git" ".cache" ".local/share/pnpm" "third_party" "vendor")

for arg in "$@"; do
  case "$arg" in
    --execute) EXECUTE=true ;;
    --dir) shift; SEARCH_DIR="$1" ;;
    --dir=*) SEARCH_DIR="${arg#--dir=}" ;;
    --help|-h)
      echo "Usage: $0 [--execute] [--dir <path>]"
      echo ""
      echo "Finds JS projects with node_modules and converts them to pnpm's"
      echo "content-addressable store (hard links = shared disk across projects)."
      echo ""
      echo "Options:"
      echo "  --execute    Actually convert projects (default: dry run)"
      echo "  --dir PATH   Search only under PATH (default: \$HOME)"
      exit 0
      ;;
  esac
done

if ! command -v pnpm &>/dev/null; then
  echo "ERROR: pnpm is not installed. Install via: npm install -g pnpm"
  exit 1
fi

PNPM_VERSION=$(pnpm --version)
PNPM_STORE=$(pnpm store path 2>/dev/null || echo "~/.local/share/pnpm/store")

echo "pnpm $PNPM_VERSION | store: $PNPM_STORE"
echo "Search root: $SEARCH_DIR"
if [ "$EXECUTE" = false ]; then
  echo "Mode: DRY RUN (pass --execute to actually convert)"
fi
echo ""

# Build find exclusion args
PRUNE_ARGS=()
for d in "${SKIP_DIRS[@]}"; do
  PRUNE_ARGS+=(-path "*/${d}" -prune -o)
done

converted=0
skipped_already_pnpm=0
skipped_no_lockfile=0
failed=0

# Find all package.json files outside of node_modules / excluded dirs
while IFS= read -r pkg_file; do
  dir="$(dirname "$pkg_file")"

  # Skip if already using pnpm
  if [ -f "${dir}/pnpm-lock.yaml" ]; then
    ((skipped_already_pnpm++)) || true
    continue
  fi

  has_node_modules=false
  [ -d "${dir}/node_modules" ] && has_node_modules=true

  # Determine lockfile type
  lockfile_type=""
  if [ -f "${dir}/package-lock.json" ]; then
    lockfile_type="npm"
  elif [ -f "${dir}/yarn.lock" ]; then
    lockfile_type="yarn"
  fi

  if [ -z "$lockfile_type" ] && [ "$has_node_modules" = false ]; then
    continue  # No lockfile and no node_modules — skip quietly
  fi

  if [ -z "$lockfile_type" ]; then
    ((skipped_no_lockfile++)) || true
    echo "  SKIP (no lockfile): $dir"
    continue
  fi

  size=""
  if [ "$has_node_modules" = true ]; then
    size=" ($(du -sh "${dir}/node_modules" 2>/dev/null | cut -f1))"
  fi

  echo "  FOUND [$lockfile_type]$size: $dir"

  if [ "$EXECUTE" = false ]; then
    continue
  fi

  echo "    Converting..."
  if (cd "$dir" && pnpm import 2>&1 | grep -v "^Progress:" | grep -v "^$"); then
    :
  else
    echo "    WARNING: pnpm import may have had issues, trying pnpm install directly"
  fi

  # Run pnpm install to populate the store and set up hard links
  if (cd "$dir" && pnpm install 2>&1 | grep -v "^Progress:" | grep -v "^$"); then
    # Remove old node_modules and reinstall to ensure hard links from store
    rm -rf "${dir}/node_modules"
    if (cd "$dir" && pnpm install 2>&1 | grep -v "^Progress:" | grep -v "^$"); then
      echo "    ✓ Converted to pnpm"
      ((converted++)) || true
    else
      echo "    ✗ pnpm install failed"
      ((failed++)) || true
    fi
  else
    echo "    ✗ Failed"
    ((failed++)) || true
  fi

done < <(find "$SEARCH_DIR" \
  "${PRUNE_ARGS[@]}" \
  -name "package.json" -print \
  2>/dev/null | sort)

echo ""
echo "Summary:"
echo "  Already pnpm: $skipped_already_pnpm"
echo "  No lockfile:  $skipped_no_lockfile"
if [ "$EXECUTE" = true ]; then
  echo "  Converted:    $converted"
  echo "  Failed:       $failed"
  echo ""
  echo "pnpm store status:"
  pnpm store status 2>/dev/null || true
else
  echo ""
  echo "Run with --execute to convert these projects."
fi
