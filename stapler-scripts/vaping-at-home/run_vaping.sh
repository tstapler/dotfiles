#!/usr/bin/env sh

# vim: ai ts=2 sw=2 et sts=2 ft=sh

# Default config file location
CONFIG_DIR="$HOME/.config/vaping"
CONFIG_FILE="$CONFIG_DIR/config.yaml"

# Get default gateway
if [ "$(uname)" = "Darwin" ]; then
    # macOS
    GATEWAY=$(netstat -nr | grep default | grep -v 'vtnet0' | awk '{print $2}' | head -n 1)
else
    # Linux
    GATEWAY=$(ip route | grep default | awk '{print $3}' | head -n 1)
fi

# Create config directory if it doesn't exist
mkdir -p "$CONFIG_DIR"

# Create default config if it doesn't exist
if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" << 'EOF'
pidfile: /var/run/vaping.pid
logging:
  version: 1
  formatters:
    simple:
      format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  handlers:
    console:
      class: logging.StreamHandler
      level: DEBUG
      formatter: simple
      stream: ext://sys.stdout
  loggers:
    vaping:
      level: DEBUG
      handlers: [console]
      propagate: no
  root:
    level: DEBUG
    handlers: [console]

probes:
  - name: ping_probe
    type: fping
    interval: 5
    count: 5
    hosts:
      - 8.8.8.8  # Google DNS
      - 1.1.1.1  # Cloudflare DNS
      - $GATEWAY # Local network gateway

  - name: http_probe
    type: http
    interval: 30
    hosts:
      - https://google.com
      - https://cloudflare.com

plugins:
  - name: vodka
    type: vodka
    output: stdout
EOF
fi

# Build the Docker image if it doesn't exist
SCRIPT_DIR=$(dirname "$0")
if ! docker image inspect vaping:local >/dev/null 2>&1; then
    if ! docker build -t vaping:local "$SCRIPT_DIR"; then
        echo "Error: Docker build failed"
        exit 1
    fi
fi

# Run vaping in Docker
docker run -d \
    --name vaping \
    --restart unless-stopped \
    --network host \
    -v "$CONFIG_DIR:/etc/vaping" \
    -v /var/run:/var/run \
    --cap-add NET_RAW \
    vaping:local
