#!/usr/bin/env bash
# Verify that after.ts compiles without errors

set -euo pipefail

npx tsc --noEmit --strict --target ES2020 --moduleResolution node after.ts 2>&1 \
  && echo "PASS: TypeScript compiles cleanly" \
  || (echo "FAIL: Type errors found in after.ts"; exit 1)
