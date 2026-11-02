# Observability stack: agent notes

Machine-wide OTel + VictoriaMetrics + Grafana stack. See `README.md` for what is wired up. This file only
covers credentials, since agents keep needing them to test alerts.

## Desktop alert relay token

Grafana's `desktop-relay` contact point POSTs alerts to `desktop_alert_relay.py` (user unit
`desktop-alert-relay.service`, listening on `172.17.0.1:8791`), which fires a desktop notification. Requests
need `Authorization: Bearer <token>`; a wrong or missing token gets `401`.

The same token lives in three places, all gitignored or outside the repo:

| Where | Use |
|---|---|
| `~/.local/state/observability/relay.token` (0600) | source of truth on the host |
| `stapler-scripts/observability/.env` as `DESKTOP_RELAY_TOKEN=` (0600) | compose passes it to the `grafana` service |
| `$DESKTOP_RELAY_TOKEN` inside `observability-grafana-1` | what the provisioned contact point reads |

Send a test notification from inside the Grafana container, which exercises the real container-to-host path
and keeps the token out of your shell history and logs:

```bash
docker exec observability-grafana-1 sh -c 'wget -q -O - \
  --header "Authorization: Bearer $DESKTOP_RELAY_TOKEN" --header "Content-Type: application/json" \
  --post-data "{\"status\":\"firing\",\"alerts\":[{\"status\":\"firing\",\"labels\":{\"alertname\":\"TEST ONLY\",\"severity\":\"warning\"},\"annotations\":{\"summary\":\"Safe to ignore.\"}}]}" \
  http://host.docker.internal:8791/grafana'     # prints: ok
```

Do not print the token, paste it into commits, issues or relay logs, or pass it on a command line that is
recorded. Read it with `cat ~/.local/state/observability/relay.token` only when you must hand it to a tool
that cannot read the env var. To rotate: write a new value to the token file and `.env`, run
`docker compose up -d --force-recreate grafana`, then `systemctl --user restart desktop-alert-relay`.

## Grafana API access

`GF_SECURITY_ADMIN_PASSWORD=admin` in `docker-compose.yml` only applies when the Grafana database is first
created. The live `grafana_data` volume has a different admin password, so `admin:admin` returns `401`
(checked 2026-11-01). No Grafana API token is provisioned yet, and none is stored anywhere in this repo.

Without credentials you can still read the unauthenticated `http://localhost:48300/metrics`, for example
`grafana_alerting_rule_group_rules` and `grafana_alerting_alerts{state=...}` for rule counts and states,
and Grafana's container log for provisioning results.

To call `/api/v1/provisioning/*` or `/api/search`, create a service account token in the UI
(Administration, Users and access, Service accounts) and keep it out of the repo. Do not reset the admin
password to get in; ask first.
