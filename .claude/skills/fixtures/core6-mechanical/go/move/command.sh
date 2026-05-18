#!/usr/bin/env bash
# Refactoring: move
# Language: Go
# Tool: manual copy + gopls rename for import path updates
# Description: Move UserRepository from internal/user/ to internal/repository/

set -euo pipefail

# Cross-package move procedure for Go:
# (No direct CLI subcommand; gopls "Move to new file" is LSP code action only)

# Step 1: create destination package directory
echo "Step 1: would create internal/repository/ directory"
# mkdir -p internal/repository

# Step 2: copy the declaration to the destination file with new package name
echo "Step 2: would copy before.go to internal/repository/user.go with package repository"
# cp internal/user/repo.go internal/repository/user.go
# sed -i '' 's/^package user$/package repository/' internal/repository/user.go

# Step 3: use gopls rename to update all import references
# This renames the import path from example.com/fixture/internal/user
# to example.com/fixture/internal/repository in all files
echo "Step 3: would run: gopls rename -w ./internal/user/repo.go:3:9 repository"
# gopls rename -w ./internal/user/repo.go:3:9 repository

# Step 4: delete the original file
echo "Step 4: would delete internal/user/repo.go"
# rm internal/user/repo.go

# Step 5: verify
# go build ./...

echo ""
echo "Move procedure (dry-run). Uncomment steps above to apply."
echo "See after.go for the expected content of the destination file."
