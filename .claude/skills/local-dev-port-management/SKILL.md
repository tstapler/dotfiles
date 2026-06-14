---
name: local-dev-port-management
description: Design and document a port assignment strategy for local development environments. Use when setting up new projects, resolving port conflicts, or establishing team conventions for port usage across services.
---

# Local Dev Port Management

Apply this skill when choosing, documenting, or fixing port assignments for local development services.

## IANA Port Ranges (the foundation)

| Range | Numbers | Rules |
|---|---|---|
| System / Well-Known | 0–1023 | Requires root on Unix. Reserved for OS/standard protocols. Avoid entirely in dev. |
| Registered / User | 1024–49151 | Where all dev tools live. IANA-assigned defaults cluster here. |
| Dynamic / Ephemeral | 49152–65535 | OS assigns these temporarily for client connections. Linux default: 32768–60999 (readable from `/proc/sys/net/ipv4/ip_local_port_range`). **Never hardcode services here** — the OS will steal them on restart. |

## Common Tool Defaults (memorise to avoid collisions)

| Port | Service |
|---|---|
| 3000 | Express, React (CRA), many Node tools |
| 4000 | Firebase Emulator UI |
| 5000 | Firebase Hosting emulator, Overmind/Hivemind base port, Flask (Linux) |
| 5001 | Firebase Functions emulator, Flask (macOS since 2.3+) |
| 5002 | Firebase App Hosting emulator |
| 5173 | Vite dev server |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 8080 | Firebase Firestore emulator, generic HTTP alternative |
| 8085 | Firebase Pub/Sub emulator |
| 9000 | Firebase Realtime Database emulator |
| 9099 | Firebase Auth emulator |
| 9199 | Firebase Cloud Storage emulator |
| 9229 | Node.js inspector (debugger) |
| 27017 | MongoDB |

## Conflict Avoidance Strategies

### 1. Explicit declaration in gradle.properties / .env (recommended default)
Define all ports centrally. Every service reads from that file. Zero runtime magic.

```properties
# gradle.properties (Gradle projects)
webApp.devPort=3001
firebase.emulator.firestore=9090
firebase.emulator.auth=9099

# .env (Node/general)
WEB_PORT=3001
API_PORT=3002
DB_PORT=5432
```

**Rule**: Firestore emulator should NOT be on 8080 — webpack, most HTTP servers, and Java app servers all default there. Move it to 9090.

### 2. Per-project port ranges (namespace by project)
Assign each project a 100-port block in the registered range. Document in a team wiki.

```
Project A: 3100–3199  (web: 3100, api: 3101, db proxy: 3102)
Project B: 3200–3299
Project C: 3300–3399
```

Tools like Overmind/Hivemind automate this: they assign `BASE + (process_index × STEP)` and inject `PORT` env var into each process.

### 3. Procfile process managers (Overmind / Hivemind)
Both tools read a `Procfile`, start each process, and assign ports sequentially:

```
# Procfile
web: ./gradlew :webApp:wasmJsBrowserDevelopmentRun
api: ./gradlew :cliApp:run
```

```bash
# Overmind — start all with base port 3000, step 100
PORT=3000 overmind start
# web gets 3000, api gets 3100
# Each process also sees OVERMIND_PROCESS_<name>_PORT for siblings
```

Overmind is preferred over Hivemind for projects that need process restart control (`overmind restart web`).

### 4. Named subdomains instead of ports (Portless)
[vercel-labs/portless](https://github.com/vercel-labs/portless) replaces port numbers with `.localhost` names:
- `https://web.localhost` instead of `http://localhost:3001`
- Assigns random ports internally (4000–4999 range), exposes them via `PORT` env var
- Best for teams where port numbers keep drifting

### 5. Persistent named port registry (port-for)
[port-for](https://github.com/fizyk/port-for) stores stable name→port bindings in `/etc/port-for.conf`:

```bash
sudo port-for add myapp    # assigns and persists a stable port for "myapp"
port-for show myapp        # always returns same port
```

Survives machine restarts. Avoids ephemeral range collisions by reading the OS range at runtime.

### 6. Service mesh intercept (Telepresence — Kubernetes only)
For services running in Kubernetes, Telepresence routes cluster traffic to your local machine. Local port and cluster port can differ:

```bash
telepresence intercept my-service --port 3001:8080
# local :3001 intercepts cluster :8080 traffic
```

Eliminates port management entirely for remote-dependent services.

## Decision Guide

| Situation | Strategy |
|---|---|
| Solo developer, 1–3 services | `.env` / `gradle.properties` with explicit ports |
| Team project, multiple services per dev | Per-project port ranges documented in wiki |
| Frequently starting/stopping many services | Procfile + Overmind |
| Sick of remembering port numbers | Portless (named subdomains) |
| Stable named ports needed system-wide | port-for |
| Kubernetes microservices dev | Telepresence |

## Sequential Batch Strategy (recommended for projects with multiple services)

**The pattern**: claim a sequential block of N ports from the IANA dynamic range (49152–65535), above the OS ephemeral ceiling.

**Why above the ephemeral ceiling?** On Linux the ephemeral range tops at 60999 by default. Ports 61000–65535 are in the IANA dynamic range but the kernel never assigns them to outbound connections — no `ip_local_reserved_ports` needed. On macOS (ephemeral extends to 65535) you need explicit reservation.

**Algorithm for grabbing a batch:**
1. Read OS ephemeral ceiling: `cat /proc/sys/net/ipv4/ip_local_port_range` (Linux) or `sysctl net.inet.ip.portrange.last` (macOS)
2. Start batch at `ceiling + 1` (Linux: 61000) or reserve via `ip_local_reserved_ports`/sysctl
3. Assign services sequentially from base
4. Check availability: `ss -tlnp | grep -E ':(61000|61001|...)'`
5. Persist reservation if needed (Linux: `/etc/sysctl.d/99-project-ports.conf`, macOS: LaunchDaemon plist)

**Reservation script** (create as `scripts/reserve-ports.sh`):
- Reads OS type + ephemeral range
- Checks batch for conflicts
- Reserves via `ip_local_reserved_ports` (Linux) or narrows ephemeral start (macOS)
- Persists across reboots
- Run with `--check` for dry-run, `--show` for port table

**Picking your base**: anything above your OS ephemeral ceiling works. Simple choices:
- Linux: 61000 (one past default ceiling 60999)
- macOS: 49152 (IANA dynamic start) — but requires reservation
- Cross-platform safe: 61000 + reserve on macOS

## Sortie-Specific Conventions

Sequential batch **64386–64395** — derived from project name, not a round number:

```properties
# gradle.properties — base 64386 = 61000 + CRC32("sortie") % 4525
webApp.devPort=64386
firebase.emulator.ui=64387
firebase.emulator.auth=64388
firebase.emulator.firestore=64389
firebase.emulator.functions=64390
firebase.emulator.hosting=64391
# 64392-64395 spare
```

```json
// firebase.json emulators section
{ "auth": {"port": 61002}, "firestore": {"port": 61003},
  "functions": {"port": 61004}, "hosting": {"port": 61005},
  "ui": {"enabled": true, "port": 61001} }
```

`make reserve-ports` — checks batch availability, reserves on macOS if needed, shows port table.
`make ports` — shows the assignment table without any changes.

## Sources

- [RFC 6335 — IANA Port Assignment](https://www.rfc-editor.org/rfc/rfc6335.html)
- [Firebase Emulator Suite — Install & Configure](https://firebase.google.com/docs/emulator-suite/install_and_configure)
- [Overmind GitHub](https://github.com/DarthSim/overmind)
- [Hivemind GitHub](https://github.com/DarthSim/hivemind)
- [Portless GitHub](https://github.com/vercel-labs/portless)
- [port-for GitHub](https://github.com/fizyk/port-for)
- [Kubernetes local debugging with Telepresence](https://kubernetes.io/docs/tasks/debug/debug-cluster/local-debugging/)
