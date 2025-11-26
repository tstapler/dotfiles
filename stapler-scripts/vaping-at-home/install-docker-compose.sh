#!/bin/bash
set -euo pipefail

# Install docker compose plugin
DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
mkdir -p $DOCKER_CONFIG/cli-plugins
VERSION="v2.24.5"  # Latest stable version as of 2024-03-24

echo "Installing Docker Compose $VERSION..."
curl -SL "https://github.com/docker/compose/releases/download/$VERSION/docker-compose-linux-$(uname -m)" -o $DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose

echo "Verifying installation..."
docker compose version
