# Run Vaping in Docker

This project provides a containerized setup for running [Vaping](https://github.com/20c/vaping), a network monitoring tool that can perform ping and HTTP checks. This setup only configures the `fping` ping probe (see `config.yaml.template`) — Vaping's HTTP-check capability is available upstream but not wired up here.

## Features

- Runs Vaping in an isolated Docker container
- Automatically detects and monitors your default gateway (`net_discovery.py`)
- Pre-configured to monitor common DNS servers (Google, Cloudflare, OpenDNS) and auto-discovered ISP hops via `fping`
- Persistent configuration through Docker volumes
- Automatic container restart on failure

## Prerequisites

- Docker
- Basic understanding of YAML for configuration (optional)

## Quick Start

1. Clone this repository
2. Build and start the stack:
```bash
make run
```

This will:
- Generate `config.yaml` from `config.yaml.template` via `generate_config.py`, auto-detecting your default gateway and ISP hops (`net_discovery.py`)
- Build the Docker images
- Start the Vaping, Grafana, Prometheus, Loki, promtail, and node-exporter containers via `docker compose`

## Monitoring Logs

To view the Vaping container's logs:
```bash
make logs
# or
./vaping_logs.sh
```

## Configuration

The generated configuration lives in `config.yaml` at the repo root (from `config.yaml.template`). You can modify the template to:
- Add/remove hosts to monitor
- Change monitoring intervals
- Adjust ping count

Re-run `make run` (or `make config.yaml`) to regenerate `config.yaml` after editing the template.

## Container Management

- Stop the stack: `make stop`
- Rebuild and restart: `make run`
- Run in the foreground with logs attached: `make debug`
- Open a shell in the vaping container: `make shell`
- Remove images/volumes: `make clean`

## Security Notes

Grafana, Prometheus, Loki, and promtail all bind to `0.0.0.0` with no auth in front of them, and Grafana ships with the default `admin`/`admin` credentials (`docker-compose.yml`). This is fine on a trusted home network but exposes host metrics and system log contents to anyone else on the LAN. If your machine is on a shared or untrusted network, change `GF_SECURITY_ADMIN_PASSWORD` in `docker-compose.yml` and consider binding the exposed ports to `127.0.0.1` instead of all interfaces.

node-exporter also mounts the entire host filesystem read-only (`/:/host:ro`) and runs with `pid: host` so it can report filesystem and process metrics — standard practice for that image, but worth knowing it gives the container broad visibility into the host.

**On Docker Desktop for Mac/Windows, "host" metrics are really VM metrics.** Docker Desktop runs containers inside a Linux VM (LinuxKit), so `/:/host:ro` and `pid: host` expose that VM's root filesystem and process namespace, not the real macOS/Windows host. Verified: `node_uname_info` reports `sysname="Linux"`, `release="*-linuxkit"`; `node_network_up` only shows the VM's virtual interfaces (`eth0`, `docker0`, `veth*`, `br-*`), never the Mac's real `en0`/Wi-Fi adapter. CPU, memory, and disk numbers in the "System Monitoring" Grafana dashboard reflect the VM, which tracks the host loosely (shared memory/CPU pool) but is not literally "your Mac's metrics." The `instance: 'macos-host'` label in `prometheus.yml` is aspirational, not accurate, on Docker Desktop — on native Linux Docker this setup does report true host metrics.

## Troubleshooting

If you experience issues:

1. Check the logs using `make logs`
2. Ensure the container has proper network access
3. Verify `config.yaml`'s syntax
4. Make sure fping is working within the container

