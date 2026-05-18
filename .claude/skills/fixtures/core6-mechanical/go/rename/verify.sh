#!/usr/bin/env bash
# Verify that after.go compiles and passes vet

set -euo pipefail

# Copy after.go as the main file for verification
cp after.go main_verify.go
# Temporarily rename function to avoid conflict with before.go if both present
go build ./... 2>/dev/null || (
  # Standalone verification when only after.go is present
  cp after.go /tmp/verify_go_rename.go
  cd /tmp
  mkdir -p verify_go_rename_fixture
  cp /tmp/verify_go_rename.go verify_go_rename_fixture/main.go
  cat > verify_go_rename_fixture/go.mod << 'GOMOD'
module example.com/fixture
go 1.21
GOMOD
  cd verify_go_rename_fixture && go build ./... && go vet ./...
  cd .. && rm -rf verify_go_rename_fixture
)

# Simpler: copy after.go to a temp dir and build
TMPDIR=$(mktemp -d)
cp after.go "$TMPDIR/main.go"
cp go.mod "$TMPDIR/go.mod"
cd "$TMPDIR" && go build ./... && go vet ./... && echo "PASS: Go builds and vets cleanly" || (echo "FAIL"; exit 1)
rm -rf "$TMPDIR"
