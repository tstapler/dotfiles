#!/usr/bin/env bash
# Refactoring: rename
# Language: Java
# Tool: OpenRewrite ChangeMethodName recipe (via Maven plugin)
# Description: Rename method processRequest -> handleRequest in RequestService

set -euo pipefail

# Step 1: dry-run — diff appears in target/rewrite/results/ (no file modification)
echo "=== Dry-run: OpenRewrite dryRun ==="
mvn rewrite:dryRun \
  -Drewrite.activeRecipes=org.openrewrite.java.ChangeMethodName \
  "-Drewrite.ChangeMethodName.methodPattern=com.example.BeforeRequestService processRequest(String)" \
  -Drewrite.ChangeMethodName.newMethodName=handleRequest \
  -q 2>&1 | tail -20 || echo "(dry-run complete; check target/rewrite/results/ for diff)"

echo ""
echo "=== Review the diff above, then apply by uncommenting the command below ==="

# Step 2: apply when satisfied with dry-run output
# mvn -U org.openrewrite.maven:rewrite-maven-plugin:run \
#   -Drewrite.activeRecipes=org.openrewrite.java.ChangeMethodName \
#   "-Drewrite.ChangeMethodName.methodPattern=com.example.BeforeRequestService processRequest(String)" \
#   -Drewrite.ChangeMethodName.newMethodName=handleRequest

# PITFALL: After rename, check for Spring @Qualifier strings and XML bean config:
# grep -r 'processRequest' src/main/resources/ --include="*.xml" --include="*.properties"

echo ""
echo "PITFALL: @Qualifier('processRequest') and XML <property name='processRequest'/> are NOT updated."
echo "Run a text search after applying the rename."
