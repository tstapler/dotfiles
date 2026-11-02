# Run Vaping in Docker

> **Storage, dashboards and alerts moved to [`../observability`](../observability/README.md).** This directory now runs only the `vaping` probe container plus the host-side exporters. The probe's metrics are scraped by that stack's Alloy from `host.docker.internal:9790` and shown in its single Grafana (`http://localhost:48300`, dashboards `Network Latency Dashboard` and `macOS System & Network Monitoring`; alert rules `Network Monitoring` folder). VictoriaMetrics is `http://localhost:8428`, VictoriaLogs `http://localhost:9428`. The old ports (Grafana 3719, Prometheus 9791, Loki 3792, promtail 9793) are gone. See "Decommission checklist" at the bottom for the leftovers of the old stack.

This project provides a containerized setup for running [Vaping](https://github.com/20c/vaping), a network monitoring tool that can perform ping and HTTP checks. This setup only configures the `fping` ping probe (see `config.yaml.template`) — Vaping's HTTP-check capability is available upstream but not wired up here.

## Features

- Runs Vaping in an isolated Docker container
- Automatically detects and monitors your default gateway (`net_discovery.py`)
- Pre-configured to monitor common DNS servers (Google, Cloudflare, OpenDNS) and auto-discovered ISP hops via `fping`
- Packet loss and latency exposed as Prometheus metrics (graphed and alerted on in the observability stack's Grafana)
- Hop-by-hop latency/loss via `fping_mtr` (traceroute + fping per hop) to distinguish local-network issues from upstream ISP issues
- DNS resolution timing tracked as its own probe, separate from ICMP reachability
- macOS log files (via `log_capture.sh`) feed VictoriaLogs through the observability stack's Alloy, shown as annotations on the latency dashboard
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
- Build the Docker image
- Start the Vaping container via `docker compose` (start `../observability` too, with `make up` there, for storage and dashboards)

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
- Remove the image: `make clean`

## Security Notes

The probe's metrics port is published on `0.0.0.0:9790` with no auth, which is fine on a trusted home network (it carries only latency/loss numbers). Grafana, VictoriaMetrics and VictoriaLogs now belong to the observability stack; see its README for their exposure.

**Host metrics on Docker Desktop for Mac come from a native node_exporter, not a container.** A containerized node-exporter only sees Docker Desktop's LinuxKit VM (verified earlier: `node_uname_info` reported `*-linuxkit` and only virtual interfaces), so the Mac's real interfaces come from `brew services` node_exporter, scraped by the observability stack's `alloy.d/macos.alloy` at `host.docker.internal:9100` with `instance="macos-host"`. Start that stack with `make up` there on macOS (it adds `docker-compose.macos.yml` automatically).

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

### Log annotations

Log lines tailed by the observability stack's Alloy (host syslog and the `log_capture.sh` files) are stored in VictoriaLogs, queried via the `victorialogs` datasource with LogsQL, and overlaid as annotations on the Grafana latency dashboard, so a latency/loss spike can be cross-referenced against what else was happening on the host at that moment.

### Alerting (`../observability/grafana/provisioning/alerting/network-rules.yml`)

Two unified-alerting rules are provisioned into a `Network Monitoring` folder: `Sustained Packet Loss` (`packet_loss > 5` for 5m) and `Sustained High Latency` (5m rate of `average_latency_milliseconds` > 150ms for 5m). Verified firing against real data — `Sustained Packet Loss` triggered correctly during testing when a discovered ISP hop showed 40-80% loss.

- **No notification channel is configured.** The rules use Grafana's built-in default receiver, which has no SMTP/Slack/etc. wired up, so firing alerts are visible in the Alerting UI but nothing gets delivered — you'll see `SMTP not configured` errors in the Grafana logs, which is expected. Routing is in `../observability/grafana/provisioning/alerting/policies.yml`; only the Filesystem Health folder is routed to the desktop relay so far.

### Wi-Fi RSSI correlation

`wifi_signal_exporter.py` reads the host's Wi-Fi signal (RSSI, noise, tx rate) and writes Prometheus textfile-collector output to `textfile_collector/wifi_signal.prom`, which the native node_exporter picks up via `--collector.textfile.directory`. This lets you overlay `wifi_rssi_dbm` against latency panels to see if degraded signal correlates with ping spikes.

- The exporter is host-only (reads the Mac's/Linux box's own Wi-Fi interface) and is not run automatically — schedule it yourself (e.g. `cron`/`launchd`) at whatever interval you want fresh samples; node-exporter will serve whatever the last-written `.prom` file contains between runs.

### Thunderbolt/USB re-enumeration watch

If the host is wired via a Thunderbolt/USB4 dock rather than built-in Ethernet, a dock disconnect or re-enumeration (bad cable seating, firmware hiccup, power event) drops the network exactly like a generic outage, but needs a different signal to diagnose.

- `thunderbolt_watch.py` polls `system_profiler SPThunderboltDataType` and writes `thunderbolt_device_connected` (gauge) and `thunderbolt_device_reenumerations_total` (counter) to `textfile_collector/thunderbolt.prom`, comparing each poll against previous state persisted in `/tmp/vaping-thunderbolt-state.json`. Host-only, not run automatically — schedule it (e.g. `launchd`, ~30s interval; a full poll takes ~2s).
- `log_capture.sh usb_thunderbolt` tails unified-logging kernel messages mentioning `Thunderbolt`/`USB` to `~/Library/Logs/vaping-unified-logs/usb_thunderbolt.log`, tailed by Alloy as the `usb_thunderbolt_logs` job and overlaid as a VictoriaLogs annotation layer (same pattern as the DHCP/power/network-config logs above).
- Dashboard: "Thunderbolt Device State" (state-timeline) and "Thunderbolt Re-enumerations" (stat) panels on `macOS System & Network Monitoring`.

### Per-process resource watch

`process_watch.py` polls `ps` for one or more configured processes and writes `process_watch_rss_bytes`, `process_watch_cpu_percent`, and `process_watch_count` (all gauges, labeled by `label`) to `textfile_collector/process_watch.prom`. Built to catch a CrowdStrike Falcon Agent memory leak that spiked RSS from 1.4GB to 25GB within seconds — a coarser poll interval would miss bursts like that.

- Host-only, not run automatically — schedule it (e.g. `launchd`, ~15s interval to catch fast bursts).
- **Which processes to watch is host-specific config**, not hardcoded in the script: drop a YAML file per watch into `config.d/process_watch.d/*.yaml` with a `label`, a `match` substring checked against each process's full command line, and an optional `hosts` allowlist (exact hostname match) so the entry only applies on machines where it's relevant — e.g. only hosts running `falcond`. Omit `hosts` to apply everywhere. Example (`config.d/process_watch.d/crowdstrike-falcon.yaml`):
  ```yaml
  label: crowdstrike_falcon
  match: com.crowdstrike.falcon.Agent
  hosts:
    - MacBook-4M6L1
  ```
- Dashboard: "Watched Process Memory (RSS)" and "Watched Process CPU" (timeseries) panels on `macOS System & Network Monitoring`.

## Troubleshooting

If you experience issues:

1. Check the logs using `make logs`
2. Ensure the container has proper network access
3. Verify `config.yaml`'s syntax
4. Make sure fping is working within the container

## Decommission checklist (not executed)

The old Prometheus, Loki, promtail and Grafana containers are gone from `docker-compose.yml`, but their Docker leftovers remain. Historical Prometheus and Loki data was **not** migrated. If you want the old series in VictoriaMetrics, `vmctl` can backfill from a Prometheus snapshot (not done; see https://docs.victoriametrics.com/vmctl/). Loki data has no such path and would be lost.

Found with `docker volume ls` / `docker images` on `onyx`:

- Volumes: `vaping-at-home_prometheus_data`, `vaping-at-home_grafana_data` (no `loki_data` / `promtail_positions` volume exists on `onyx`; on the Mac, `docker volume ls | grep vaping-at-home` will list those too).
- Image: `mirror.gcr.io/prom/prometheus:v3.2.1`. Keep `vaping:local` (still used) and `mirror.gcr.io/grafana/grafana:11.5.2` (the observability Grafana uses it). On the Mac also the `grafana/loki:3.3.2` and `grafana/promtail:3.3.2` images.

**DESTRUCTIVE, irreversible.** Run only after confirming the observability stack has what you need, and after confirming the old containers are stopped (`docker ps -a | grep vaping-at-home`):

```bash
docker volume rm vaping-at-home_prometheus_data vaping-at-home_grafana_data   # plus vaping-at-home_loki_data vaping-at-home_promtail_positions on the Mac
docker rmi mirror.gcr.io/prom/prometheus:v3.2.1                               # plus the loki/promtail images on the Mac
```
