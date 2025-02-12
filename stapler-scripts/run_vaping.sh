#!/usr/bin/env sh

# vim: ai ts=2 sw=2 et sts=2 ft=sh

# Default config file location
CONFIG_DIR="$HOME/.config/vaping"
CONFIG_FILE="$CONFIG_DIR/config.yaml"

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

# Run vaping in Docker
docker run -d \
    --name vaping \
    --restart unless-stopped \
    --network host \
    -v "$CONFIG_DIR:/etc/vaping" \
    -v /var/run:/var/run \
    --cap-add NET_RAW \
    20c/vaping
