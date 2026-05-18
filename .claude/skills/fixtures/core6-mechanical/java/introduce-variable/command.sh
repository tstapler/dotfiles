#!/usr/bin/env bash
# Refactoring: introduce-variable
# Language: Java
# Tool: IDE/LSP only — no OpenRewrite extract-variable recipe
# Description: Extract price * 1.08 into priceWithTax and stock ternary into availability

# TIER B OPERATION — Introduce Variable in Java has no OpenRewrite recipe.
# Note: OpenRewrite has InlineVariable (the INVERSE) but not extract-variable.

# Options:
# 1. IntelliJ IDEA: Select expression → Refactor → Introduce Variable
# 2. Eclipse: Select expression → Refactor → Extract Local Variable
# 3. Manual Edit (acceptable for this fixture — 2 expressions, 1 file):
#    Add: double priceWithTax = price * 1.08;
#    Add: String availability = stock > 0 ? "Yes (qty: " + stock + ")" : "No";
#    Replace inline expressions in String.format with variable names
#    Verify: javac AfterProductService.java

echo "TIER B: Introduce Variable in Java has no OpenRewrite recipe."
echo "OpenRewrite has InlineVariable (the inverse) but not extract-variable."
echo "Use IntelliJ, Eclipse, or manual Edit for small cases."
echo "See AfterProductService.java for the expected result."
