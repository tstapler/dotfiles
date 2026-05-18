#!/usr/bin/env bash
# Refactoring: change-signature
# Language: TypeScript
# Tool: ts-morph (add optional parameter); call sites unchanged (optional param)
# Description: Add optional `options?: RequestOptions` parameter to fetchData(url)

set -euo pipefail

# Step 1: scope check — find all call sites before changing signature
echo "=== Scope check: all call sites of fetchData ==="
sg --pattern 'fetchData($$$ARGS)' --lang typescript before.ts

# Step 2: apply the signature change using ts-morph
# Adding an optional parameter does not require updating call sites
echo ""
echo "=== Applying signature change via ts-morph ==="
npx tsx -e "
const { Project } = require('ts-morph');
const project = new Project();
project.addSourceFileAtPath('./before.ts');
const sourceFile = project.getSourceFileOrThrow('./before.ts');
const fn = sourceFile.getFunctionOrThrow('fetchData');
fn.addParameter({ name: 'options', type: 'RequestOptions', hasQuestionToken: true });
project.saveSync();
console.log('Added optional parameter options?: RequestOptions to fetchData');
"

# To revert the change (restore from backup or git):
# git checkout before.ts

# Step 3: verify (after applying — uncomment to run on modified before.ts)
# npx tsc --noEmit --strict --target ES2020 --moduleResolution node before.ts
