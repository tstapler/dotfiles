#!/usr/bin/env bash
# Refactoring: rename
# Language: TypeScript
# Tool: ast-grep (structural; use ts-morph for type-aware rename in real projects)
# Description: Rename variable `ttlPrc` to `totalPrice` in before.ts

set -euo pipefail

# Step 1: scope check — review all occurrences before applying
echo "=== Scope check: all occurrences of ttlPrc ==="
sg --pattern 'ttlPrc' --lang typescript before.ts

# Step 2: dry-run — show what would change
echo ""
echo "=== Dry-run: what sg would rename ==="
sg --pattern 'ttlPrc' --rewrite 'totalPrice' --lang typescript before.ts

# To apply the rename, uncomment the line below:
# sg --pattern 'ttlPrc' --rewrite 'totalPrice' --lang typescript before.ts --update-all

# For type-aware project-wide rename, use ts-morph (preferred for production use):
# npx tsx -e "
# const { Project } = require('ts-morph');
# const project = new Project({ tsConfigFilePath: './tsconfig.json' });
# const sourceFile = project.getSourceFileOrThrow('before.ts');
# const fn = sourceFile.getFunctionOrThrow('calculateTotalPrice');
# const varDecl = fn.getVariableDeclarationOrThrow('ttlPrc');
# varDecl.rename('totalPrice');
# project.saveSync();
# "
