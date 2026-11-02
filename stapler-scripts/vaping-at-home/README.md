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

### Thunderbolt/USB re-enumeration watch

If the host is wired via a Thunderbolt/USB4 dock rather than built-in Ethernet, a dock disconnect or re-enumeration (bad cable seating, firmware hiccup, power event) drops the network exactly like a generic outage, but needs a different signal to diagnose.

- `thunderbolt_watch.py` polls `system_profiler SPThunderboltDataType` and writes `thunderbolt_device_connected` (gauge) and `thunderbolt_device_reenumerations_total` (counter) to `textfile_collector/thunderbolt.prom`, comparing each poll against previous state persisted in `/tmp/vaping-thunderbolt-state.json`. Host-only, not run automatically — schedule it (e.g. `launchd`, ~30s interval; a full poll takes ~2s).
- `log_capture.sh usb_thunderbolt` tails unified-logging kernel messages mentioning `Thunderbolt`/`USB` to `~/Library/Logs/vaping-unified-logs/usb_thunderbolt.log`, scraped by promtail as the `usb_thunderbolt_logs` job and overlaid as a Loki annotation layer (same pattern as the DHCP/power/network-config logs above).
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

### Linux host and btrfs filesystem health

Added after the 2026-11-01 incident on `onyx` (Manjaro, single-NVMe btrfs root): metadata filled (25G used of 26G allocated, 512 MiB global reserve, 1.1 MiB unallocated) while `df` still showed ~250 GiB free, and every read/unlink blocked in `reserve_bytes`. No filesystem metric existed to alert on.

**Scraping a Linux host.** `prometheus.yml` reads its node-exporter target from `prometheus_targets.d/node-exporter.yml`, which `make build` copies from `node-exporter.macos.yml.dist` or `node-exporter.linux.yml.dist` by `uname -s` (the copy is gitignored). The Prometheus container gets `host.docker.internal:host-gateway` (`extra_hosts`) because only Docker Desktop defines that name itself. Verified on `onyx`: a containerized Prometheus 3.2.1 scraped a host node_exporter at `172.17.0.1:9100` and `up{job="node-exporter",instance="onyx"}` was `1`. The macOS path is unchanged in intent but **not tested on a Mac**, including whether Docker Desktop accepts the `host-gateway` entry (INFERRED fine).

**Why both node_exporter and a textfile exporter.** node_exporter 1.12.1 (`brew install node_exporter`, no root) with `--collector.btrfs` exposes `node_btrfs_{size,used,reserved}_bytes{block_group_type,mode}`, `node_btrfs_device_size_bytes`, `node_btrfs_device_unused_bytes`, `node_btrfs_global_rsv_size_bytes`, `node_btrfs_device_errors_total{type}` and `node_btrfs_allocation_ratio`. It does not expose `bytes_may_use`, pinned/readonly bytes, or `global_rsv_reserved`, which are exactly what turned 529 MiB of raw headroom into a negative usable value. `btrfs_health.py` fills that gap by reading `/sys/fs/btrfs/<uuid>/` directly (no root, no btrfs-progs, no metascope). node_exporter still supplies `node_filesystem_*`. Note statfs on btrfs reports 0 inodes (`node_filesystem_files 0`), so the inode panel excludes btrfs.

**`btrfs_health.py`** (textfile collector, same pattern as `process_watch.py`; per-host config in `config.d/btrfs_health.d/*.yaml` with a `hosts` allowlist and optional `uuids`; no matching config means it writes nothing). Metrics: `btrfs_block_group_{total,used,disk_total,reserved,pinned,readonly,may_use}_bytes{uuid,type}`, `btrfs_device_size_bytes`, `btrfs_unallocated_bytes`, `btrfs_metadata_usable_headroom_bytes`, `btrfs_global_reserve_{size,reserved}_bytes`, `btrfs_device_errors_total{devid,type}`, `btrfs_device_missing`, `btrfs_balance_running`, `btrfs_exclusive_operation`, and `btrfs_exporter_last_success_timestamp_seconds`. Run `make btrfs-health` once, `python3 btrfs_health.py --stdout` to print, `make test` for the fixture-based tests (`tests/fixtures/sysfs_btrfs` is a sysfs snapshot; `tests/test_btrfs_health.py` also builds an incident-shaped tree where raw total-used is 1 GiB but usable headroom is negative).

- `unallocated = sum(devices/*/size) - sum(disk_total)`; `disk_total` already includes DUP copies.
- `usable headroom = total - used - reserved - pinned - readonly - may_use - global_rsv_size`. Deliberately conservative: the kernel may already count the global reserve inside `bytes_may_use` (INFERRED, not checked against kernel source), so it can read low but not high.
- **Headroom is noisy during a balance.** Sampling every 4 s on `onyx` during a running balance gave 7.5 to 10.2 GiB, and a direct sysfs read at another moment showed metadata `bytes_may_use` at 14.9 GiB, which would make it negative on a healthy filesystem with tens of GiB unallocated. The headroom alerts are therefore gated on `unallocated < 20 GiB` and use `for:` 10m/2m. The 20 GiB gate is my choice, not a verified kernel threshold; see open decisions below.
- Scrub state is not exported: it is not an `exclusive_operation` and its status needs root. Only balance is observable.
- Not built: per-directory metadata attribution from `metascope scan` (optional; expensive and infrequent, would need its own slower timer).

**Scheduling (not installed).** Units live in `systemd/`: `btrfs-health.{service,timer}` (user-level, every 60 s, no root) and `node-exporter.service` (user-level; binds `172.17.0.1:9100`, the docker0 gateway, so the container reaches it without exposing :9100 on the LAN; `Restart=on-failure` covers boot before docker0 exists; a host firewall may still need to allow docker0 to 9100). Existing precedent: `llm-sync.timer` is not stored in the repo but rendered by `bootstrap-pyinfra/deploys/llm_sync.py` into `~/.config/systemd/user/` and enabled with `systemd.service`; `litellm-proxy.service` is stored in its project directory. Until a pyinfra deploy exists for these, install by hand:

```bash
mkdir -p ~/.config/systemd/user
ln -s ~/dotfiles/stapler-scripts/vaping-at-home/systemd/{btrfs-health.service,btrfs-health.timer,node-exporter.service} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now node-exporter.service btrfs-health.timer
```

Hand-run `make run` (or `docker compose up -d`) afterwards. Units pass `systemd-analyze verify --user`; they have not been started.

**Alerts** (`grafana/provisioning/alerting/rules.yml`, folder `Filesystem Health`): unallocated < 10 GiB warn / < 3 GiB critical; usable metadata headroom < 2 GiB warn / < 256 MiB critical (gated, above); any `increase(btrfs_device_errors_total[15m])`; `btrfs exporter stale or missing` (`time() - last_success > 300`, NoData = Alerting, so a dead exporter alerts); `node_exporter target down`; and an always-firing `Dead mans switch heartbeat`. Verified in a throwaway Grafana 11.5.2 container against live data: all 8 rules provisioned and evaluated with health `ok`, heartbeat `firing`, the rest `inactive`. Not tested: the stale/NoData and error-increase rules actually firing.

- Existing finding: `onyx` already reports `corruption_errs 14586` on devid 1. The alert fires on increase, so it stays quiet; the lifetime count is shown in the dashboard. Worth a `btrfs scrub` / `btrfs device stats` look.

**Notification channel: not chosen.** `contactpoints.yml` provisions two webhook placeholders (`ntfy-placeholder`, `heartbeat-placeholder`) reading `NTFY_WEBHOOK_URL` and `HEARTBEAT_URL` from the environment; unset, they default to unresolvable `*.invalid` URLs so delivery fails visibly in the Grafana log. `policies.yml` routes only the `Filesystem Health` folder (and `severity=heartbeat`) to them; existing network alerts keep the default receiver. Needed to finish: the ntfy server URL, topic, and whether auth is a bearer token (a commented hint is in `contactpoints.yml`; no credentials are invented).

**Dead man's switch, and what a self-hosted monitor cannot cover.** If `onyx` freezes (the incident), Prometheus, Grafana and the exporter freeze with it, so no in-stack rule can fire. The `deadmans-switch-heartbeat` rule re-sends every 5 minutes to `heartbeat-placeholder`; that only helps if the receiver is **outside the machine** and alerts on absence. Needs: an external service that expects a ping every ~5 min and pages (for example a Healthchecks.io-style check or ntfy on a different host) with a grace period of ~10-15 min, the ping URL in `HEARTBEAT_URL`, and for ntfy a separate always-on host that runs the absence check. Grafana will also keep sending "firing" while the heartbeat rule fires, so the external side must treat silence, not content, as the signal.

**Dashboard:** `Filesystem Health (btrfs)` (`grafana/dashboards/filesystem/filesystem_health.json`, folder `Filesystem Health`): allocation stacked by type plus unallocated, unallocated and usable headroom with threshold lines, metadata consumers, device error counters, balance state, statfs usage, non-btrfs inode usage. All 18 panel queries returned data against a live Prometheus; the dashboard was loaded by Grafana's file provisioner but not visually inspected.

## Troubleshooting

If you experience issues:

1. Check the logs using `make logs`
2. Ensure the container has proper network access
3. Verify `config.yaml`'s syntax
4. Make sure fping is working within the container

