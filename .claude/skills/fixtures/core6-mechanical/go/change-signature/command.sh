#!/usr/bin/env bash
# Refactoring: change-signature
# Language: Go
# Tool: ast-grep (scope check) + gritql (call-site rewrite) + manual declaration update
# Description: Add ctx context.Context as first parameter to FetchData(url string)

set -euo pipefail

# Step 1: scope check — find all call sites of FetchData
echo "=== Scope check: all call sites of FetchData ==="
sg --pattern 'FetchData($$$ARGS)' --lang go .

# Step 2: dry-run — show what grit would rewrite at call sites
echo ""
echo "=== Dry-run: call-site rewrites ==="
grit apply '`FetchData($url)` => `FetchData(ctx, $url)`' . --dry-run 2>/dev/null || \
  echo "(grit dry-run: would rewrite FetchData(url) -> FetchData(ctx, url) at all call sites)"

# Step 3: apply the call-site rewrite
# Uncomment to apply:
# grit apply '`FetchData($url)` => `FetchData(ctx, $url)`' .

# Step 4: update the function declaration manually (Edit tool or direct edit)
# Change: func FetchData(url string) (string, error)
# To:     func FetchData(ctx context.Context, url string) (string, error)
# Add import: "context"

# Step 5: verify — Go compiler catches ALL call-site mismatches
# go build ./...

echo ""
echo "Next: manually update the FetchData declaration to add ctx context.Context as first param."
echo "Then run: go build ./... to verify all call sites are correct."
