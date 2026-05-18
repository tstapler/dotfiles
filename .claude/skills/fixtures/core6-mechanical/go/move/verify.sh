#!/usr/bin/env bash
set -euo pipefail
TMPDIR=$(mktemp -d)
mkdir -p "$TMPDIR/internal/repository"
cp after.go "$TMPDIR/internal/repository/user.go"
cat > "$TMPDIR/go.mod" << 'GOMOD'
module example.com/fixture
go 1.21
GOMOD
cd "$TMPDIR" && go build ./... && go vet ./... && echo "PASS: Go builds and vets cleanly" || (echo "FAIL"; exit 1)
rm -rf "$TMPDIR"
