# Implementation plan: scheduled CSV export

## Architecture

reportsvc is a single Python service (`src/reportsvc/`): `api.py` exposes HTTP handlers, `store.py` wraps the SQLite database. Exports run in a background worker thread started by `api.py`. Emails go through the existing `mailer` helper.

New pieces: `schedules.py` (schedule model + next-run calculation), `exporter.py` (query + CSV writer), `worker.py` (polls due schedules, runs the exporter, records a row in the `export_jobs` table, sends the email), plus two HTTP handlers in `api.py`.

## Epics and stories

### Epic 1 — Schedules

- 1.1 Add `schedules.py` with daily/weekly/monthly next-run calculation. Estimate: 4 hours.
- 1.2 Add create/pause/delete handlers for schedules in `api.py`. Estimate: 6 hours. Depends on 1.1.

### Epic 2 — Export execution

- 2.1 Add `exporter.py` that runs the usage query for a period and writes CSV to a file under `exports/`. Estimate: 6 hours.
- 2.2 Add `worker.py` that finds due schedules, calls the exporter, writes a row to `export_jobs`, and sends the email with a download link. Estimate: 8 hours. Depends on 2.1 and 1.1.

### Epic 3 — History

- 3.1 Add a handler that lists past exports for an admin from `export_jobs`. Estimate: 3 hours. Depends on 2.2.
- 3.2 Add a download handler that serves a stored CSV by job id. Estimate: 4 hours. Depends on 3.1.

## Tasks

| Task | Files | Depends on |
|---|---|---|
| T1 schedules model | schedules.py | none |
| T2 schedule handlers | api.py | T1 |
| T3 exporter | exporter.py | none |
| T4 worker | worker.py | T1, T3 |
| T5 history list | api.py | T4 |
| T6 download | api.py | T5 |

## Testing

Unit tests for next-run calculation and the CSV writer. One integration test that runs a due schedule end to end with a fake mailer.

## Rollout

Ship behind no flag; the worker starts with the service.
