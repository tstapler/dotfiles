#!/usr/bin/env bash
# Refactoring: move
# Language: Java
# Tool: OpenRewrite ChangePackage recipe
# Description: Move UserRepository from com.example.services to com.example.repository

set -euo pipefail

# Step 1: dry-run — show what import statements would change
echo "=== Dry-run: OpenRewrite ChangePackage ==="
mvn rewrite:dryRun \
  -Drewrite.activeRecipes=org.openrewrite.java.ChangePackage \
  -Drewrite.ChangePackage.oldPackageName=com.example.services \
  -Drewrite.ChangePackage.newPackageName=com.example.repository \
  -q 2>&1 | tail -20 || echo "(dry-run complete; check target/rewrite/results/ for diff)"

# Step 2: apply when satisfied
# Uncomment to apply:
# mvn -U org.openrewrite.maven:rewrite-maven-plugin:run \
#   -Drewrite.activeRecipes=org.openrewrite.java.ChangePackage \
#   -Drewrite.ChangePackage.oldPackageName=com.example.services \
#   -Drewrite.ChangePackage.newPackageName=com.example.repository

# Step 3: verify
# mvn compile

echo ""
echo "PITFALL: XML bean configuration files are NOT updated by OpenRewrite."
echo "After move, run:"
echo "  grep -r 'com.example.services.UserRepository' src/main/resources/ --include='*.xml'"
