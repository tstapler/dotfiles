# Run Vaping in Docker

This project provides a containerized setup for running [Vaping](https://github.com/20c/vaping), a network monitoring tool that can perform ping and HTTP checks. This setup only configures the `fping` ping probe (see `config.yaml.template`) — Vaping's HTTP-check capability is available upstream but not wired up here.

## Features

- Runs Vaping in an isolated Docker container
- Automatically detects and monitors your default gateway (`net_discovery.py`)
- Pre-configured to monitor common DNS servers (Google, Cloudflare, OpenDNS) and auto-discovered ISP hops via `fping`
- Packet loss and latency graphed in Grafana, with sustained-loss/sustained-latency alert rules
- Hop-by-hop latency/loss via `fping_mtr` (traceroute + fping per hop) to distinguish local-network issues from upstream ISP issues
- DNS resolution timing tracked as its own probe, separate from ICMP reachability
- Loki-backed log annotations overlaid on the latency dashboard
- Optional Wi-Fi RSSI/noise/tx-rate export via a host-side textfile-collector script, correlatable against latency panels
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

## Network Debugging Additions

### Packet loss and latency

`fping`'s `loss`/`avg` output feeds the `packet_loss` and `average_latency_milliseconds` Prometheus metrics (via `prometheus_plugin.py`) for every host in the `dns_servers` group. Graphed on the main Grafana dashboard alongside latency.

### ISP-vs-local hop diagnosis (`fping_mtr`)

The `path_to_google_dns` probe (`type: fping_mtr` in `config.yaml.template`) runs `traceroute` to rediscover the hop path to `8.8.8.8` each cycle, then `fping`s every hop, exposing `mtr_hop_average_latency_milliseconds` / `mtr_hop_packet_loss` per `hop`/`hop_index`. Comparing loss/latency at the first hop (your router) against later hops tells you whether a problem is on your LAN or upstream.

- `fping_mtr_plugin.py` overrides the fork's `fping_mtr.py` to add `-I` (ICMP echo) to the `traceroute` invocation. The upstream code uses plain UDP probes, which don't work from inside a Docker container: the bridge network's NAT rewrites UDP source ports, so the returned ICMP TTL-exceeded packets from hops beyond the gateway never route back to the probing socket, and traceroute gets stuck reporting only hop 1. Verified via `docker exec` before/after: UDP mode reported all hops beyond the gateway as `*`; ICMP mode correctly resolved the destination.
- `traceroute` needs `cap_net_raw` for both the UDP and ICMP cases; the Dockerfile already grants this (see the `setcap` step).
- **Docker Desktop for Mac/Windows caveat**: because Docker Desktop containers run inside a NAT'd LinuxKit VM, only the gateway and destination hops are visible from inside the container — real intermediate ISP hops aren't reachable regardless of UDP vs ICMP mode. On native Linux Docker (bridge or host networking closer to the real interface), you should see the actual ISP hop chain. This is a platform limitation of the fix, not a bug in it.
- **`mtr_hop_packet_loss` and `mtr_hop_average_latency_milliseconds` can look inconsistent at a single scrape** (e.g. `loss=100` next to a non-zero `avg`) — this is expected Gauge staleness, not a bug. Each is set independently in `emit_mtr`, and `hop_avg_latency` is only updated `if "avg" in stats`; fping omits the `avg` field entirely on a 100%-loss cycle, so the Gauge just keeps serving its last successful reading until the next cycle (30s later, per `interval` in `config.yaml.template`) refreshes it. Verified by polling `/metrics` across several cycles: the same hop's loss moved 100% → 60% → 20% while latency stayed populated throughout.

### DNS resolution timing (`command` probe)

The `dns_resolution_timing` probe (`type: command`) shells out to `dns_probe.py {host}` for each host in the `dns_lookup_targets` group and reports resolution latency the same way `fping` reports ICMP latency — as a separate signal from reachability, so you can tell "DNS is slow" apart from "the network is dropping packets."

- `command_plugin.py` overrides the fork's vendored `command.py`, which has two bugs: `CommandProbe.init()` never initializes `self.hosts` before `.extend()`-ing onto it (`AttributeError` on startup), and it never unwraps dict-shaped `hosts: [{host: ..., name: ...}]` entries the way `fping.py` does (would have broken `self.command.format(host=host)` on the next call). Both fixed in the override.
- Each `dns_probe.py` invocation does a fresh resolution; OS/resolver caching may still mask real upstream DNS latency depending on your system's resolver config.

### Loki log annotations

Log lines from `promtail` (host syslog) are queried via the `loki` datasource and overlaid as annotations on the Grafana latency dashboard, so a latency/loss spike can be cross-referenced against what else was happening on the host at that moment.

### Alerting (`grafana/provisioning/alerting/rules.yml`)

Two unified-alerting rules are provisioned into a `Network Monitoring` folder: `Sustained Packet Loss` (`packet_loss > 5` for 5m) and `Sustained High Latency` (5m rate of `average_latency_milliseconds` > 150ms for 5m). Verified firing against real data — `Sustained Packet Loss` triggered correctly during testing when a discovered ISP hop showed 40-80% loss.

- **No notification channel is configured.** The rules use Grafana's built-in default receiver, which has no SMTP/Slack/etc. wired up, so firing alerts are visible in the Alerting UI but nothing gets delivered — you'll see `SMTP not configured` errors in the Grafana logs, which is expected. Add a contact point (`grafana/provisioning/alerting/contactpoints.yml` or via the UI) if you want actual notifications.

### Wi-Fi RSSI correlation

`wifi_signal_exporter.py` reads the host's Wi-Fi signal (RSSI, noise, tx rate) and writes Prometheus textfile-collector output to `textfile_collector/wifi_signal.prom`, which node-exporter picks up via `--collector.textfile.directory`. This lets you overlay `wifi_rssi_dbm` against latency panels to see if degraded signal correlates with ping spikes.

- The exporter is host-only (reads the Mac's/Linux box's own Wi-Fi interface) and is not run automatically — schedule it yourself (e.g. `cron`/`launchd`) at whatever interval you want fresh samples; node-exporter will serve whatever the last-written `.prom` file contains between runs.

## Troubleshooting

If you experience issues:

1. Check the logs using `make logs`
2. Ensure the container has proper network access
3. Verify `config.yaml`'s syntax
4. Make sure fping is working within the container

