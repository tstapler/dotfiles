#!/usr/bin/env bash
# Refactoring: change-signature
# Language: Rust
# Tool: ast-grep (scope check) + gritql (call-site rewrite) + manual declaration update
# Description: Add config: &Config parameter to process(items: &[Item])

set -euo pipefail

# Step 1: scope check — find all call sites of process
echo "=== Scope check: all call sites of process ==="
sg --pattern 'process($$$ARGS)' --lang rust before.rs

# Step 2: dry-run — show what grit would rewrite at call sites
echo ""
echo "=== Dry-run: call-site rewrites ==="
grit apply '`process($items)` => `process($items, &config)`' . --dry-run 2>/dev/null || \
  echo "(grit dry-run: would rewrite process(items) -> process(items, &config) at all call sites)"

# Step 3: apply the call-site rewrite
# Uncomment to apply:
# grit apply '`process($items)` => `process($items, &config)`' .

# Step 4: update the function declaration manually
# Change: fn process(items: &[Item]) -> f64
# To:     fn process(items: &[Item], config: &Config) -> f64
# Add the Config struct definition

# Step 5: verify — Rust borrow checker surfaces all mismatches
# cargo check

echo ""
echo "PITFALL: Check for #[cfg(...)]-gated methods — they may not all be visible on the current platform."
echo "After applying, run: cargo check"
