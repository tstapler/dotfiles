#!/usr/bin/env python3
"""Receives Grafana webhook POSTs and shows them as local desktop notifications.

Runs on the host, not in Docker: the notification service (D-Bus on Linux,
Notification Center on macOS) is only reachable from the user's session.
Backends mirror gh-signal (crates/gh-signal-core/src/notify.rs): `notify-send`
speaks the same org.freedesktop.Notifications service notify-rust uses, and
macOS uses `osascript display notification`. gh-signal sets no urgency; this
adds one because alerts need a critical tier.

Limit: only reaches you while the graphical session is up and you are at the
machine. It cannot fire if the machine is hung or X is down.
"""
import argparse
import hmac
import json
import os
import platform
import stat
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

APP_NAME = "vaping-at-home"
DEFAULT_BIND = "172.17.0.1"  # docker0 gateway: what host-gateway resolves to inside containers
DEFAULT_PORT = 8791
MAX_BODY_BYTES = 64 * 1024
MAX_NOTIFICATION_CHARS = 400
ROUTE = "/grafana"


def urgency_for(status, severities):
    if status == "resolved":
        return "low"
    return "critical" if "critical" in severities else "normal"


def truncate(text, limit=MAX_NOTIFICATION_CHARS):
    return text if len(text) <= limit else text[: limit - 1] + "…"


def build_notification(payload):
    """Maps a Grafana webhook payload (single or grouped `alerts` array) to (title, body, urgency)."""
    alerts = payload.get("alerts") or []
    status = str(payload.get("status") or (alerts[0].get("status") if alerts else "firing")).lower()
    names = []
    for a in alerts:
        name = (a.get("labels") or {}).get("alertname")
        if name and name not in names:
            names.append(name)
    if not names:
        names = [(payload.get("commonLabels") or {}).get("alertname") or payload.get("title") or "Grafana alert"]
    title = f"[{status.upper()}] {names[0]}"
    if len(alerts) > 1:
        title += f" (+{len(alerts) - 1} more)"

    lines = []
    for a in alerts:
        summary = (a.get("annotations") or {}).get("summary")
        if summary and summary not in lines:
            lines.append(summary)
    body = "\n".join(lines) or str(payload.get("message") or "")
    severities = [(a.get("labels") or {}).get("severity", "") for a in alerts] or \
                 [(payload.get("commonLabels") or {}).get("severity", "")]
    return truncate(title, 120), truncate(body), urgency_for(status, severities)


def osascript_quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def dispatch(title, body, urgency, system=None):
    """Runs the platform notifier; raises on failure."""
    system = system or platform.system()
    if system == "Darwin":
        script = f"display notification {osascript_quote(body)} with title {osascript_quote(title)}"
        cmd = ["osascript", "-e", script]
    elif system == "Linux":
        cmd = ["notify-send", f"--app-name={APP_NAME}", f"--urgency={urgency}", "--", title, body]
    else:
        raise RuntimeError(f"unsupported platform {system}")
    subprocess.run(cmd, check=True, timeout=10, capture_output=True)


def load_token(token_file, env=os.environ):
    token = env.get("DESKTOP_RELAY_TOKEN", "").strip()
    if token_file:
        path = Path(token_file)
        if path.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise SystemExit(f"{path} must not be accessible by group/other (chmod 600)")
        token = path.read_text().strip()
    if not token:
        raise SystemExit("no token: set --token-file or DESKTOP_RELAY_TOKEN")
    return token


def make_handler(token, notifier=dispatch):
    class Handler(BaseHTTPRequestHandler):
        def _reply(self, code, text=""):
            self.send_response(code)
            self.send_header("Content-Length", str(len(text)))
            self.end_headers()
            self.wfile.write(text.encode())

        def do_POST(self):
            supplied = self.headers.get("Authorization", "")
            if not hmac.compare_digest(supplied.encode(), f"Bearer {token}".encode()):
                return self._reply(401, "unauthorized")
            if self.path != ROUTE:
                return self._reply(404, "not found")
            length = self.headers.get("Content-Length")
            if length is None or not length.isdigit():
                return self._reply(411, "length required")
            if int(length) > MAX_BODY_BYTES:
                return self._reply(413, "payload too large")
            try:
                payload = json.loads(self.rfile.read(int(length)))
                if not isinstance(payload, dict):
                    raise ValueError("payload is not an object")
            except ValueError:
                return self._reply(400, "bad json")
            title, body, urgency = build_notification(payload)
            try:
                notifier(title, body, urgency)
            except (OSError, RuntimeError, subprocess.SubprocessError) as err:
                print(f"notify failed: {type(err).__name__}", file=sys.stderr)
                return self._reply(502, "notify failed")
            self._reply(200, "ok")

        def log_message(self, fmt, *args):
            # Request line only; headers (the bearer token) are never logged.
            print(f"{self.address_string()} {fmt % args}", file=sys.stderr)

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bind", default=DEFAULT_BIND)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--token-file", help="file holding the bearer token, mode 0600; else DESKTOP_RELAY_TOKEN")
    args = parser.parse_args(argv)
    server = HTTPServer((args.bind, args.port), make_handler(load_token(args.token_file)))
    print(f"desktop_alert_relay listening on {args.bind}:{args.port}", file=sys.stderr)
    server.serve_forever()


if __name__ == "__main__":
    main()
