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
