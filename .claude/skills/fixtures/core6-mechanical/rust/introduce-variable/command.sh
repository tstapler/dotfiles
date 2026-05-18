#!/usr/bin/env bash
# Refactoring: introduce-variable
# Language: Rust
# Tool: rust-analyzer extract_variable assist (LSP)
# Description: Extract config.timeout_secs * retry_count into variable max_wait

# TIER B OPERATION — Introduce Variable in Rust requires rust-analyzer LSP.

# rust-analyzer assist: extract_variable
# Select the expression: config.timeout_secs * retry_count
# Code action: "Extract into variable"
# rust-analyzer will prompt for the variable name (added in PR #17587)
# Name it: max_wait

# EXCEPTION: This fixture has 2 occurrences in 1 function.
# Manual Edit is acceptable (within 1-5 occurrence limit):
# Add before the if statement:
#   let max_wait = config.timeout_secs * retry_count;
# Replace both occurrences with: max_wait
# cargo check to verify

echo "TIER B: Introduce Variable requires rust-analyzer LSP."
echo "This fixture has 2 occurrences in 1 function — manual Edit is acceptable."
echo "See after.rs for the expected result."
