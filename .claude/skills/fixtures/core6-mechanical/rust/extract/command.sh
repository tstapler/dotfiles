#!/usr/bin/env bash
# Refactoring: extract
# Language: Rust
# Tool: rust-analyzer extract_function assist (LSP only)
# Description: Extract validation block from create_account into validate_account_input

# TIER B OPERATION — Extract in Rust requires rust-analyzer LSP.

# LSP assist: extract_function
# Available via any LSP-capable editor (neovim, helix, VS Code + rust-analyzer extension)
#
# Steps:
# 1. Open before.rs in an LSP-enabled editor
# 2. Select lines 3-11 (the validation block)
# 3. Trigger code action: "Extract into function"
# 4. NOTE: rust-analyzer names the extracted function `fun_name` by default
#    Rename it immediately to `validate_account_input`
#
# Or via Claude Code LSP tool (ENABLE_LSP_TOOL=1):
# Step 1: ToolSearch("select:LSP") — confirm LSP available
# Step 2: LSP findReferences to scope the block
# Step 3: Edit to create validate_account_input above create_account
# Step 4: Edit to replace the block with: validate_account_input(username, email, age)?;
# Step 5: cargo check to verify

echo "TIER B: Extract requires LSP (rust-analyzer extract_function assist)."
echo "Default extracted function name is 'fun_name' — rename immediately."
echo "See after.rs for the expected result."
