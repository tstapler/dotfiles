#!/usr/bin/env bash
# Refactoring: rename
# Language: Rust
# Tool: ast-grep (structural; rust-analyzer has no stable standalone rename CLI)
# Description: Rename function process_request -> handle_request

set -euo pipefail

# IMPORTANT WARNINGS:
# 1. ast-grep is NOT type-aware — it renames every syntactic occurrence.
#    If process_request is a trait method, this rename is INCOMPLETE.
#    ast-grep will rename the declaration but NOT trait impls or other usages.
#
# 2. This fixture uses a non-trait function for a clean demonstration.
#    For trait methods, use rust-analyzer via LSP.
#
# 3. After rename, ALWAYS run `cargo check` to surface missed impl blocks
#    (expected errors: E0407, E0046)

# Step 1: scope check — confirm this is not a trait method
echo "=== Scope check: occurrences of process_request ==="
sg --pattern 'process_request' --lang rust before.rs

echo ""
echo "=== Scope check: any trait definitions using this name ==="
sg --pattern 'fn process_request' --lang rust before.rs

# Step 2: dry-run — show what would be renamed
echo ""
echo "=== Dry-run: what sg would rename ==="
sg --pattern 'process_request' --rewrite 'handle_request' --lang rust before.rs

# Step 3: apply the rename
# Uncomment to apply:
# cp before.rs src/main.rs  # set up Cargo project structure
# sg --pattern 'process_request' --rewrite 'handle_request' --lang rust src/ --update-all
# cargo check  # surfaces any missed trait impls (E0407, E0046)
