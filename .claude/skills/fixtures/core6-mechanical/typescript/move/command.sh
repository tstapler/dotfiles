#!/usr/bin/env bash
# Refactoring: move
# Language: TypeScript
# Tool: ts-morph moveToDirectory (moves file with import updates)
# Description: Move UserService from src/services/user.ts to src/core/user.ts

set -euo pipefail

# NOTE: This command requires a real tsconfig.json and directory structure.
# The fixture shows the file content before and after the move.
# In a real project, use the ts-morph script below.

# Step 1: dry-run — show what would be moved (ts-morph has no built-in dry-run;
#         check tsconfig.json include patterns to confirm scope)
echo "=== Scope check: confirm tsconfig.json includes both source and destination ==="
echo "Files in project would be listed here by ts-morph project.getSourceFiles()"

# Step 2: apply the move using ts-morph
# Uncomment to apply in a real project with proper tsconfig.json:
# npx tsx -e "
# const { Project } = require('ts-morph');
# const project = new Project({ tsConfigFilePath: './tsconfig.json' });
# const sourceFile = project.getSourceFileOrThrow('src/services/user.ts');
# sourceFile.moveToDirectory('src/core/');
# project.saveSync();
# console.log('Moved src/services/user.ts to src/core/user.ts; imports updated');
# "

echo "Move command (dry-run mode): would move src/services/user.ts -> src/core/user.ts"
echo "All import statements referencing this file would be updated automatically by ts-morph."
echo "To apply: uncomment the npx tsx block above."
