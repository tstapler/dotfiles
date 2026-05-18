#!/usr/bin/env bash
set -euo pipefail
TMPDIR=$(mktemp -d)
cp after.go "$TMPDIR/main.go"
cp go.mod "$TMPDIR/go.mod"
cd "$TMPDIR" && go build ./... && go vet ./... && echo "PASS: Go builds and vets cleanly" || (echo "FAIL"; exit 1)
rm -rf "$TMPDIR"
