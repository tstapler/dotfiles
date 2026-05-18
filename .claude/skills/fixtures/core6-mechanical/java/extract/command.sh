#!/usr/bin/env bash
# Refactoring: extract
# Language: Java
# Tool: IDE/LSP only — no OpenRewrite recipe for arbitrary extraction
# Description: Extract validation block from registerUser into validateInput

# TIER B OPERATION — Extract in Java has no OpenRewrite recipe.
# This is IDE/LSP only.

# Options:
# 1. IntelliJ IDEA: Select the validation block → Refactor → Extract Method → validateInput
# 2. Eclipse: Select block → Refactor → Extract Method
# 3. Claude Code LSP (ENABLE_LSP_TOOL=1):
#    - ToolSearch("select:LSP") to confirm LSP available
#    - Use LSP findReferences to scope the block
#    - Edit to create validateInput method above registerUser
#    - Edit to replace the block with: validateInput(username, email, age);
#    - javac AfterUserProcessor.java to verify

echo "TIER B: Extract in Java has no OpenRewrite recipe."
echo "Use IntelliJ, Eclipse, or Claude Code LSP tool."
echo "See AfterUserProcessor.java for the expected result."
