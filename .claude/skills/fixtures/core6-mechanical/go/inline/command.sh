#!/usr/bin/env bash
# Refactoring: inline
# Language: Go
# Tool: gopls codeaction refactor.inline.call (LSP, available in gopls v0.14+)
# Description: Inline isValidUsername — it has exactly one call site

# TIER B OPERATION — Inline in Go requires LSP.

# gopls experimental CLI approach:
# gopls codeaction -exec -kind refactor.inline.call -diff ./before.go:#340-#380
# (byte range must cover the isValidUsername call site)
# Remove -diff to apply.
#
# NOTE: gopls inline.call as of v0.17 has imperfect comment handling.
# Review the diff carefully before accepting.

# Standard LSP approach (preferred):
# Step 1: ToolSearch("select:LSP") — confirm LSP available
# Step 2: Position cursor on the isValidUsername call in registerUser
# Step 3: LSP code action: "Inline call"
# Step 4: go build ./... to verify

# EXCEPTION: This fixture has 1 call site. Manual Edit is acceptable:
# Replace: !isValidUsername(username)
# With:    !(len(username) >= 3 && !strings.Contains(username, " "))
# Delete:  isValidUsername function definition
# Verify:  go build ./...

echo "TIER B: Inline requires LSP for multi-site cases."
echo "This fixture has 1 call site — manual Edit is acceptable."
echo "See after.go for the expected result."
