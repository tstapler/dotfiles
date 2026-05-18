#!/usr/bin/env bash
# Refactoring: extract
# Language: Go
# Tool: gopls codeaction refactor.extract.function (experimental, byte-range form)
# Description: Extract validation block from CreateAccount into validateAccountInput

# TIER B OPERATION — Extract in Go requires LSP code action.
# gopls CLI has codeaction support but byte ranges are fragile.

# gopls experimental CLI approach (byte offsets required):
# The validation block in before.go starts around byte offset 200 and ends around 450.
# Recompute these offsets if the file changes.
#
# Dry-run (show diff without applying):
# gopls codeaction -exec -kind refactor.extract.function -diff ./before.go:#200-#450
#
# Apply (remove -diff to write changes):
# gopls codeaction -exec -kind refactor.extract.function ./before.go:#200-#450

# Standard LSP approach (preferred):
# Step 1: ToolSearch("select:LSP") — confirm LSP available
# Step 2: LSP findReferences to identify the block scope
# Step 3: Edit to create validateAccountInput function above CreateAccount
# Step 4: Edit to replace the validation block with: if err := validateAccountInput(...); err != nil { return "", err }
# Step 5: go build ./... to verify

echo "TIER B: Extract requires LSP."
echo "See after.go for the expected result."
echo ""
echo "gopls codeaction approach (experimental — requires exact byte offsets):"
echo "  gopls codeaction -exec -kind refactor.extract.function -diff ./before.go:#200-#450"
