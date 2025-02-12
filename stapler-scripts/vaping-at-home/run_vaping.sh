#!/usr/bin/env sh

# vim: ai ts=2 sw=2 et sts=2 ft=sh

# Start vaping using docker-compose
SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR" && docker-compose up -d
