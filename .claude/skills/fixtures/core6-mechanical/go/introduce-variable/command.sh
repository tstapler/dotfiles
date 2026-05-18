#!/usr/bin/env bash
# Refactoring: introduce-variable
# Language: Go
# Tool: gopls codeaction refactor.extract.variable (LSP)
# Description: Extract strings.TrimSpace(r.URL.Query().Get("q")) into variable `query`

# TIER B OPERATION — Introduce Variable in Go requires LSP.

# gopls experimental CLI approach:
# gopls codeaction -exec -kind refactor.extract.variable -diff ./before.go:#250-#310
# (byte range must cover the complex expression)
# Remove -diff to apply.

# Standard LSP approach (preferred):
# Step 1: ToolSearch("select:LSP") — confirm LSP available
# Step 2: Select the expression: strings.TrimSpace(r.URL.Query().Get("q"))
# Step 3: LSP code action: "Extract variable"
# Step 4: Name the variable `query`
# Step 5: go build ./... to verify

# EXCEPTION: This fixture has 2 occurrences in 1 function.
# Manual Edit is acceptable (within 1-5 occurrence limit):
# Add: query := strings.TrimSpace(r.URL.Query().Get("q"))
# Replace both occurrences with: query
# Verify: go build ./...

echo "TIER B: Introduce Variable requires LSP."
echo "This fixture has 2 occurrences — manual Edit is acceptable."
echo "See after.go for the expected result."
