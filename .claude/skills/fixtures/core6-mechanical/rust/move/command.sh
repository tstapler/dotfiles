#!/usr/bin/env bash
# Refactoring: move
# Language: Rust
# Tool: manual + ast-grep for `use` statement updates
# Description: Move UserService from src/services.rs to src/core/user.rs

set -euo pipefail

# No move-symbol assist in rust-analyzer (as of 2025).
# Rust's module system surfaces all broken references as compile errors.

# Step 1: scope check — find all `use` statements referencing the old location
echo "=== Scope check: use statements referencing services::UserService ==="
sg --pattern 'use $$$::services::UserService' --lang rust src/ 2>/dev/null || \
  echo "(no src/ directory in fixture — showing pattern that would be used)"
sg --pattern 'services::UserService' --lang rust before.rs

# Step 2: move the item (dry-run — show what would happen)
echo ""
echo "=== Move procedure (dry-run) ==="
echo "Would: mkdir -p src/core"
echo "Would: move UserService struct + impl from src/services.rs to src/core/user.rs"
echo "Would: add 'pub mod core;' and 'pub mod user;' to module tree"

# Step 3: update `use` statements project-wide
# Uncomment to apply:
# sg --pattern 'use $$$services$$$::UserService' --rewrite 'use ${1}core::user::UserService' --lang rust src/ --update-all

# Step 4: optionally add re-export at old location (preserves API stability)
# In src/services.rs: pub use crate::core::user::UserService;

# Step 5: verify — Rust module system surfaces every broken reference
# cargo check

echo ""
echo "After move, run: cargo check"
echo "Expect compile errors pointing to any missed `use` statements."
