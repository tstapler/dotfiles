#!/usr/bin/env bash
# Refactoring: introduce-variable
# Language: TypeScript
# Tool: LSP (for multi-site); manual Edit acceptable for this single-site fixture
# Description: Extract complex inline expression into subtotal and totalWithTax

# TIER B OPERATION — No standard CLI path for introduce-variable in TypeScript.

# EXCEPTION: This fixture has a single-expression return statement.
# Manual Edit is acceptable for single-site, single-file introduce-variable.
# Use LSP for cases where the expression appears in multiple locations.

# Manual approach (acceptable for this fixture):
# 1. Add: const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
# 2. Add: const totalWithTax = subtotal * (1 + TAX_RATE);
# 3. Replace the complex inline expression with: totalWithTax.toFixed(2)
# 4. Verify: npx tsc --noEmit after.ts

# LSP Invocation Sequence (for multi-occurrence expressions):
# Step 1: ToolSearch("select:LSP") — confirm LSP available
# Step 2: Select the expression range in before.ts (the inline reduce + multiply)
# Step 3: LSP code action: "Extract to variable" (TypeScript language service)
# Step 4: Verify with npx tsc --noEmit

echo "TIER B: Introduce Variable requires LSP for multi-occurrence expressions."
echo "This fixture has 1 occurrence — manual Edit is acceptable."
echo "See after.ts for the expected result."
