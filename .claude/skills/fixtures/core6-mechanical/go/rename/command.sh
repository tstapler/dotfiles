#!/usr/bin/env bash
# Refactoring: rename
# Language: Go
# Tool: gopls rename (semantic, module-graph-aware)
# Description: Rename function ProcessRequest -> HandleRequest

set -euo pipefail

# Step 1: dry-run — show diff without modifying files
# Line 6, col 6 is the position of ProcessRequest in before.go
echo "=== Dry-run: gopls rename diff ==="
gopls rename -d ./before.go:6:6 HandleRequest

# Step 2: apply the rename
# Uncomment to apply:
# gopls rename -w ./before.go:6:6 HandleRequest

# NOTE: Always use gopls rename, NOT gorename.
# gorename is deprecated and does not support Go modules.

# After applying, verify:
# go build ./...
# go vet ./...
