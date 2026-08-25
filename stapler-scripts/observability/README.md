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
| Grafana | `http://localhost:3000` | `admin` / `admin` — change this if you ever expose the port beyond localhost |

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
- **Traces / logs**: accepted by the collector (so a project that exports
  both, like stapler-squad, doesn't error), but only routed to a `debug`
  exporter (collector's own stdout) — no trace/log backend (e.g. Tempo/Loki)
  is wired up yet. Add one to `otel-collector-config.yaml` if that's ever
  needed; out of scope for now.
- **Dashboards**: `grafana/dashboards/stapler-squad-cgroup-memory.json` is a
  starter dashboard for stapler-squad's `cgroup_memory_*` metrics
  (`telemetry/cgroup_linux.go`) — memory.current vs the MemoryHigh/MemoryMax
  ceilings, PSI stall percentages, and OOM/OOM-kill event counts. Add more
  dashboards under `grafana/dashboards/` as new projects wire in metrics;
  they're auto-provisioned (see `grafana/provisioning/dashboards/`).

## Persistence

`restart: unless-stopped` — containers come back with the Docker daemon
(itself a systemd/launchd service), so no separate service wrapper is
needed, unlike `../litellm-proxy` (which runs its main process natively,
not in a container).
