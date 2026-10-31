# Observability Stack

A single, shared OpenTelemetry Collector + VictoriaMetrics + Grafana stack for
**any** local project's metrics — not per-project like `../vaping-at-home` or
`../litellm-proxy`. There's exactly one instance running for the whole machine,
so it uses each tool's own standard port rather than a project-specific block.

## Start it

```bash
make up      # docker compose up -d
make logs    # follow all three services
make down    # stop, keep data
make clean   # stop and wipe all volumes
```

## Endpoints

| Service | URL | Notes |
|---|---|---|
| OTLP gRPC | `localhost:4317` | point `OTEL_EXPORTER_OTLP_ENDPOINT` here (or nothing — most OTel SDKs default to this) |
| OTLP HTTP | `localhost:4318` | |
| VictoriaMetrics query API | `http://localhost:8428` | Prometheus-compatible; `/api/v1/query`, `/api/v1/query_range` |
| Tempo query API | `http://localhost:3200` | not usually queried directly — use Grafana's Explore |
| Pyroscope query API | `http://localhost:4040` | continuous profiling storage; not usually queried directly — use Grafana's flamegraph panels/Explore |
| Alloy debug UI | `http://localhost:12345` | component graph + per-target scrape health for the `pyroscope.scrape` jobs below |
| Grafana | `http://localhost:48300` | `admin` / `admin` — change this if you ever expose the port beyond localhost. Non-standard port: `:3000` is one of the most commonly already-bound dev ports (Next.js, CRA, etc.) |

## Pointing a project at this stack

Send OTLP metrics to `localhost:4317`. If the project's OTel setup already
defaults to that address (stapler-squad's `telemetry.DefaultOTLPEndpoint`
does), there's nothing to configure — just make sure its own
`OTEL_ENABLED`-style flag is on. The gRPC exporter retries its own
connection, so start order doesn't matter: bring this stack up before or
after the project.

## What's wired up

- **Metrics**: `otlp` receiver → `prometheusremotewrite` exporter →
  VictoriaMetrics. This is the only pipeline that actually persists data.
- **Traces**: `otlp` receiver → `otlp/tempo` exporter → Tempo (local-disk
  storage, `tempo.yaml`, 48h retention). Query via Grafana Explore using the
  Tempo datasource.
- **Profiles**: Grafana Alloy (`alloy-config.alloy`) pull-scrapes a project's
  standard `net/http/pprof` HTTP endpoint (CPU, heap, goroutine, mutex,
  block) on an interval and forwards to Pyroscope, no SDK/code change
  required in the target project. Query via Grafana's flamegraph panels or
  Explore using the Pyroscope datasource. See "Pointing a project's profiler
  at this stack" below to wire up a new project.
- **Logs**: accepted by the collector (so a project exporting logs doesn't
  error) but only routed to a `debug` exporter (collector's own stdout) — no
  log backend (e.g. Loki) is wired up yet.
- **Dashboards**: file-provisioned per project folder under
  `/var/lib/grafana/dashboards/<project>/` inside the container, each with
  its own explicit provider entry in
  `grafana/provisioning/dashboards/dashboards.yml` (see that file's comment
  for why — a single provider with `foldersFromFilesStructure: true` is
  broken against Grafana's `nestedFolders` toggle, on by default since 11.x:
  https://github.com/grafana/grafana/issues/73271). `general/` is local to
  this repo (`./grafana/dashboards/general`); `stapler-squad/` is bind-mounted
  directly from that project's own repo
  (`~/Programming/stapler-squad/docs/observability/grafana/dashboards`, see
  `docker-compose.yml`'s `grafana` service) — migrated there 2026-09-12 so
  its dashboards version alongside the metrics they visualize, not in this
  unrelated repo; edit them there, not here. To add a new project: either
  drop dashboard JSON directly in `grafana/dashboards/<project>/` here (for
  something with no repo of its own) or bind-mount that project's own
  dashboard directory the same way stapler-squad's is, then add a provider
  block to `dashboards.yml` either way.

## Pointing a project's profiler at this stack

Requires the project to expose a standard Go `net/http/pprof` endpoint
(`import _ "net/http/pprof"` behind its own `http.ListenAndServe`, typically
gated behind a flag/env var so it's not always-on in production). Add a
`pyroscope.scrape` block to `alloy-config.alloy` pointing at
`localhost:<port>` with a unique `service_name` label — see the existing
`stapler_squad` block for the exact shape, including which
`profiling_config` sub-blocks to enable (the plain, non-`godeltaprof_*`
variants — `net/http/pprof` doesn't expose the `delta_*` endpoints those
require). `localhost` works because the `alloy` service runs with
`network_mode: host` (see `docker-compose.yml`): most projects' pprof
servers, like stapler-squad's, bind to `localhost` specifically
(loopback-only), which `host.docker.internal` (the bridge gateway IP) cannot
reach even with the right `extra_hosts` entry — only sharing the host's
network namespace does. `make restart-web-profile`-equivalent: bring the
profiler up, then `docker compose restart alloy` to pick up the new scrape
target.

## Persistence

`restart: unless-stopped` — containers come back with the Docker daemon
(itself a systemd/launchd service), so no separate service wrapper is
needed, unlike `../litellm-proxy` (which runs its main process natively,
not in a container).

## Host contention (macOS Activity Monitor view)

Alloy and the other containers run in the Docker VM, so a node exporter there
reports the VM, not the Mac. `host-collector/host_collector.py` (Python 3
stdlib, no root) runs natively, serves Prometheus text on
`127.0.0.1:64891/metrics` (port = `61000 + CRC32("host-collector") % 4525`, per
the `local-dev-port-management` batch convention), and Alloy scrapes it at
`host.docker.internal:64891` every 15 s with `job="host"`, then remote-writes
to VictoriaMetrics (`alloy-config.alloy`).

Dashboard: Grafana > folder `host` > "Host contention" (uid `host-contention`).
Alerts: Grafana alerting, folder `host`, group `host-contention`
(`grafana/provisioning/alerting/host-alerts.yml`).

### Install (run these yourself; nothing here loads a launchd job for you)

```bash
cd ~/dotfiles/stapler-scripts/observability
# 1. Foreground test
python3 host-collector/host_collector.py &  sleep 15; curl -s localhost:64891/metrics | head; kill %1
# 2. Pick up the new Alloy scrape + Grafana mounts. Restart (not just reload):
#    Docker Desktop's file mount can serve the old alloy-config.alloy otherwise.
docker compose up -d alloy grafana && docker compose restart alloy
# 3. Run it at login (render the template, then bootstrap)
PLIST=~/Library/LaunchAgents/com.tstapler.host-collector.plist
sed -e "s#__PYTHON3__#/usr/bin/python3#" -e "s#__DOTFILES__#$HOME/dotfiles#" \
  host-collector/com.tstapler.host-collector.plist.template > "$PLIST"
launchctl bootstrap gui/$(id -u) "$PLIST"
launchctl print gui/$(id -u)/com.tstapler.host-collector | head -5
```

Uninstall: `launchctl bootout gui/$(id -u)/com.tstapler.host-collector && rm ~/Library/LaunchAgents/com.tstapler.host-collector.plist`.
Logs: `/tmp/host-collector.log`. Env knobs: `HOST_COLLECTOR_PORT`, `_BIND`, `_INTERVAL` (sample seconds, default 10), `_DOCKER_INTERVAL` (default 30).

### Metrics

| Metric | Labels | Meaning |
|---|---|---|
| `host_cpu_percent` / `host_cpu_seconds_total` | `mode` system,user,idle(,nice) | whole-host CPU share (all cores = 100) / cumulative core-seconds since collector start |
| `host_load1/5/15`, `host_cpu_count` | | load average and logical cores |
| `host_memory_bytes`, `host_memory_total_bytes` | `state` free,active,inactive,wired,compressed,speculative | `vm_stat` |
| `host_swap_used_bytes`, `host_swap_total_bytes` | | `vm.swapusage` (total = swap currently allocated, it grows on demand) |
| `host_memory_pressure_level` | | 1 normal, 2 warn, 4 critical |
| `host_vm_{pagein,pageout,swapin,swapout}_bytes_total` | | cumulative since boot, use `rate()` |
| `host_filesystem_free_bytes`, `host_filesystem_size_bytes` | `mount="/System/Volumes/Data"` | excludes APFS purgeable space |
| `host_disk_io_bytes_total` | `direction` | summed over block devices (`ioreg`) |
| `host_process_count`, `host_thread_count` | | totals |
| `host_process_cpu_percent`, `_rss_bytes`, `_threads`, `_instances` | `group` | allowlist groups, `~name` for the current top 10 others, and `other` (bounded: about 30 series) |
| `host_docker_container_cpu_percent` | `name`, `image` | `docker stats`, top 10 containers plus `other` |
| `host_docker_up`, `host_thermal_warning`, `host_thermal_cpu_speed_limit_percent` | | thermal limit only appears when `pmset` reports one |
| `host_collector_errors_total{source}`, `host_collector_sample_duration_seconds`, `host_collector_cpu_seconds_total` | | self-monitoring |

Process CPU is 100 = one core (Activity Monitor units), computed from cumulative
CPU-time deltas between samples.

### Alerts

| Rule | Condition |
|---|---|
| data volume free < 5 GB (warning) | for 2 m |
| data volume free < 1 GB (critical) | for 1 m |
| swap used > 90% | for 10 m |
| memory pressure >= 2 | for 10 m |
| load1 / cores > 4 | for 15 m |
| `up{job="host"}` < 1 (collector blind) | for 5 m |

No contact point is provisioned; alerts are visible in Grafana only until you add one.

### Host vs app contention

The last dashboard row puts stapler-squad's `go_runtime_sched_latency_seconds`
(p50/p99) and `go_runtime_mutex_wait_seconds_total` rate beside host CPU busy %,
with a shared crosshair.

- Host busy near 100%, high load per core, and sched latency rising together while the mutex-wait rate stays flat: the OS is not scheduling the app. Check the contention row for EDR, Docker VM, fseventsd, builds.
- Mutex wait rising while host CPU has idle headroom: the app's own lock contention.
- High system CPU with little user CPU: kernel or filesystem-event work (EDR, fseventsd, Spotlight), not your code.

### Limits (what unprivileged macOS does not give us)

- `kernel_task` CPU reads 0 (not visible to unprivileged `ps`); it appears only as unexplained system CPU. No per-process disk IO or GPU either (`powermetrics` needs root).
- Processes that start and exit between two 10 s samples (short `compile` runs) are not seen individually; sustained build load still shows.
- `host_cpu_seconds_total` and the paging/IO counters restart at zero when the collector restarts (fine for `rate()`).
- `docker stats` shows per-core percentages of the Docker VM, and it is itself slow when the host is starved, so it is sampled every 30 s in a separate thread.
- Verified on macOS 26 (Darwin 25.6, Apple Silicon). `pmset -g therm` text, `ioreg` statistics keys and `kern.memorystatus_vm_pressure_level` can differ on other macOS versions; failures only bump `host_collector_errors_total`.
