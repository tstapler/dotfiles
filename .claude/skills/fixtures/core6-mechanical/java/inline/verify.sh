#!/usr/bin/env bash
set -euo pipefail
mkdir -p /tmp/fixture-verify
javac -d /tmp/fixture-verify AfterOrderService.java 2>&1 \
  && echo "PASS: Java compiles cleanly" \
  || (echo "FAIL: Compilation errors in AfterOrderService.java"; exit 1)
rm -rf /tmp/fixture-verify
