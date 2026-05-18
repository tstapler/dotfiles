#!/usr/bin/env bash
# Refactoring: inline
# Language: Rust
# Tool: rust-analyzer inline_local_variable or inline_call assist (LSP)
# Description: Inline normalize_email — single call site, single file

# TIER B OPERATION — Inline in Rust requires rust-analyzer LSP.

# rust-analyzer assists available (via LSP code action):
# - inline_local_variable: inline a `let` binding (inline the variable `normalized_email`)
# - inline_call: replace a function call with the callee's body
#   NOTE: inline_call has edge cases with early returns — test carefully

# EXCEPTION: This fixture has 1 call site in 1 file.
# Manual Edit is acceptable (within 1-5 occurrence limit):
# 1. Replace: let normalized_email = normalize_email(email);
#    With:    let normalized_email = email.trim().to_lowercase();
# 2. Delete the normalize_email function definition
# 3. cargo check to verify

echo "TIER B: Inline requires LSP for multi-site cases."
echo "This fixture has 1 call site — manual Edit is acceptable."
echo "See after.rs for the expected result."
