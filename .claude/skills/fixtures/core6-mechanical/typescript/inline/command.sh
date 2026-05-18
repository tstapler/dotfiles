#!/usr/bin/env bash
# Refactoring: inline
# Language: TypeScript
# Tool: LSP (requires ENABLE_LSP_TOOL=1) or manual Edit (single-site acceptable here)
# Description: Inline formatUserEmail — it has exactly one call site

# TIER B OPERATION — No standard CLI path for TypeScript Inline.

# EXCEPTION: This specific fixture has only 1 call site in 1 file.
# Manual Edit is acceptable for 1-5 occurrences in a single file.
# For multi-file inlining, LSP is required.

# Manual approach (acceptable for this fixture):
# 1. Replace: const normalizedEmail = formatUserEmail(email);
#    With:     const normalizedEmail = email.trim().toLowerCase();
# 2. Delete the formatUserEmail function definition
# 3. Verify with: npx tsc --noEmit after.ts

# LSP Invocation Sequence (for multi-site cases):
# Step 1: ToolSearch("select:LSP") — confirm LSP is available
# Step 2: LSP findReferences on formatUserEmail — confirm single call site
# Step 3: Edit to replace call site with inlined body
# Step 4: Edit to remove the function definition
# Step 5: npx tsc --noEmit to verify

echo "TIER B: Inline requires LSP for multi-site cases."
echo "This fixture has 1 call site — manual Edit is acceptable."
echo "See after.ts for the expected result."
