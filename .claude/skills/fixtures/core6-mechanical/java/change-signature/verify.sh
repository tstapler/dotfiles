#!/usr/bin/env bash
set -euo pipefail
mkdir -p /tmp/fixture-verify
javac -d /tmp/fixture-verify AfterUserService.java 2>&1 \
  && echo "PASS: Java compiles cleanly" \
  || (echo "FAIL: Compilation errors in AfterUserService.java"; exit 1)
rm -rf /tmp/fixture-verify
