#!/usr/bin/env bash
# Verify that AfterRequestService.java compiles

set -euo pipefail

# Compile using javac directly (no Maven required for basic verification)
javac -d /tmp/fixture-verify AfterRequestService.java 2>&1 \
  && echo "PASS: Java compiles cleanly" \
  || (echo "FAIL: Compilation errors in AfterRequestService.java"; exit 1)

rm -rf /tmp/fixture-verify
