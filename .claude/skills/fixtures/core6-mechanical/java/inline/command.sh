#!/usr/bin/env bash
# Refactoring: inline
# Language: Java
# Tool: OpenRewrite InlineVariable recipe (TIER A EXCEPTION — CLI-feasible!)
# Description: Inline single-use local variables in calculateTotal

set -euo pipefail

# TIER A EXCEPTION: Java Inline (variable) is CLI-feasible via OpenRewrite.
# OpenRewrite InlineVariable inlines local variables used exactly once.

# Step 1: dry-run — show what would be inlined
echo "=== Dry-run: OpenRewrite InlineVariable ==="
mvn rewrite:dryRun \
  --define rewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-static-analysis:RELEASE \
  --define rewrite.activeRecipes=org.openrewrite.staticanalysis.InlineVariable \
  -q 2>&1 | tail -20 || echo "(dry-run complete; check target/rewrite/results/ for diff)"

# Step 2: apply when satisfied with dry-run
# Uncomment to apply:
# mvn -U org.openrewrite.maven:rewrite-maven-plugin:run \
#   --define rewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-static-analysis:RELEASE \
#   --define rewrite.activeRecipes=org.openrewrite.staticanalysis.InlineVariable \
#   --define rewrite.exportDatatables=true

# Step 3: verify
# mvn compile

echo ""
echo "This is a TIER A EXCEPTION: Java InlineVariable is CLI-feasible via OpenRewrite."
echo "Other Tier B operations (Extract, Introduce Variable) still require LSP."
