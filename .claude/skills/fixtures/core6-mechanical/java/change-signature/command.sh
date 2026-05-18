#!/usr/bin/env bash
# Refactoring: change-signature
# Language: Java
# Tool: OpenRewrite ReorderMethodArguments recipe
# Description: Reorder createUser(email, name) -> createUser(name, email)

set -euo pipefail

# Step 1: dry-run — show what would change
echo "=== Dry-run: OpenRewrite ReorderMethodArguments ==="
mvn rewrite:dryRun \
  -Drewrite.activeRecipes=org.openrewrite.java.ReorderMethodArguments \
  "-Drewrite.ReorderMethodArguments.methodPattern=com.example.BeforeUserService createUser(String, String)" \
  "-Drewrite.ReorderMethodArguments.newParameterNames=[name, email]" \
  "-Drewrite.ReorderMethodArguments.oldParameterNames=[email, name]" \
  -q 2>&1 | tail -20 || echo "(dry-run complete; check target/rewrite/results/ for diff)"

# Step 2: apply when satisfied
# Uncomment to apply:
# mvn -U org.openrewrite.maven:rewrite-maven-plugin:run \
#   -Drewrite.activeRecipes=org.openrewrite.java.ReorderMethodArguments \
#   "-Drewrite.ReorderMethodArguments.methodPattern=com.example.BeforeUserService createUser(String, String)" \
#   "-Drewrite.ReorderMethodArguments.newParameterNames=[name, email]" \
#   "-Drewrite.ReorderMethodArguments.oldParameterNames=[email, name]"

# Step 3: verify
# mvn compile

echo ""
echo "ReorderMethodArguments updates both the declaration and all call sites."
