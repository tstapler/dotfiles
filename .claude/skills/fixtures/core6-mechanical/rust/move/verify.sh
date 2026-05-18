#!/usr/bin/env bash
set -euo pipefail
TMPDIR=$(mktemp -d)
cp Cargo.toml "$TMPDIR/Cargo.toml"
mkdir -p "$TMPDIR/src"
cp after.rs "$TMPDIR/src/main.rs"
cd "$TMPDIR" && cargo check 2>&1 && echo "PASS: Rust compiles cleanly" || (echo "FAIL"; exit 1)
rm -rf "$TMPDIR"
