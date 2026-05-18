#!/usr/bin/env bash
# Refactoring: extract
# Language: TypeScript
# Tool: LSP (requires ENABLE_LSP_TOOL=1 in Claude Code session)
# Description: Extract the validation block in processUserRegistration into validateUser

# TIER B OPERATION — No CLI-only path exists for TypeScript Extract.
# This requires an active LSP session via Claude Code's LSP tool.

# Prerequisites:
# 1. Start Claude Code with ENABLE_LSP_TOOL=1:
#    ENABLE_LSP_TOOL=1 claude
# 2. Verify LSP is available:
#    Run ToolSearch("select:LSP") in the session — must return a schema

# LSP Invocation Sequence:
# Step 1: Use LSP findReferences to confirm the scope of the validation block
#   Tool: LSP
#   Operation: findReferences
#   File: before.ts
#   Position: line 9, col 3 (start of validation block)
#
# Step 2: Use Edit to:
#   a) Create the new validateUser function above processUserRegistration
#   b) Replace the validation block in processUserRegistration with validateUser(user)
#
# Step 3: Verify with TypeScript compiler
#   npx tsc --noEmit before.ts

echo "TIER B: Extract requires LSP. Start Claude Code with ENABLE_LSP_TOOL=1."
echo "See command.sh comments for the LSP invocation sequence."
echo ""
echo "The transformation from before.ts to after.ts shows the expected result."
