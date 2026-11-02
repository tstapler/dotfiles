"""Tests for desktop_alert_relay.py using a fake notify-send that records its argv.

Run: uv run --no-project --with pytest --with pyyaml pytest tests/
"""
import json
import platform
import sys
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import desktop_alert_relay as relay  # noqa: E402

TOKEN = "s3cret-test-token"

pytestmark = pytest.mark.skipif(platform.system() != "Linux", reason="exercises the notify-send backend")


@pytest.fixture
def server(tmp_path, monkeypatch):
    record = tmp_path / "calls.jsonl"
    fake = tmp_path / "bin" / "notify-send"
    fake.parent.mkdir()
    fake.write_text(f"#!/usr/bin/env python3\nimport json,sys\nopen({str(record)!r},'a').write(json.dumps(sys.argv[1:])+'\\n')\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake.parent}:/usr/bin:/bin")
    httpd = HTTPServer(("127.0.0.1", 0), relay.make_handler(TOKEN))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}{relay.ROUTE}", record
    httpd.shutdown()


def post(url, payload, token=TOKEN, raw=None):
    data = raw if raw is not None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as err:
        return err.code


def calls(record):
    return [json.loads(line) for line in record.read_text().splitlines()] if record.exists() else []


def alert(name="btrfs unallocated space critical", severity="critical", summary="Unallocated below 3 GiB", status="firing"):
    return {"status": status, "labels": {"alertname": name, "severity": severity}, "annotations": {"summary": summary}}


def test_critical_firing_maps_title_body_and_urgency(server):
    url, record = server

    assert post(url, {"status": "firing", "alerts": [alert()]}) == 200

    assert calls(record) == [[
        "--app-name=vaping-at-home", "--urgency=critical", "--",
        "[FIRING] btrfs unallocated space critical", "Unallocated below 3 GiB",
    ]]


def test_warning_is_normal_and_resolved_is_low(server):
    url, record = server

    post(url, {"status": "firing", "alerts": [alert(severity="warning")]})
    post(url, {"status": "resolved", "alerts": [alert(status="resolved")]})

    urgencies = [c[1] for c in calls(record)]
    assert urgencies == ["--urgency=normal", "--urgency=low"]


def test_grouped_alerts_become_one_notification_with_worst_urgency(server):
    url, record = server
    payload = {"status": "firing", "alerts": [
        alert("A low", "warning", "first"), alert("B crit", "critical", "second"), alert("C", "warning", "third")]}

    post(url, payload)

    (call,) = calls(record)
    assert call[1] == "--urgency=critical"
    assert call[3] == "[FIRING] A low (+2 more)"
    assert call[4] == "first\nsecond\nthird"


def test_long_body_is_truncated(server):
    url, record = server

    post(url, {"status": "firing", "alerts": [alert(summary="x" * 5000)]})

    body = calls(record)[0][4]
    assert len(body) == relay.MAX_NOTIFICATION_CHARS and body.endswith("\u2026")


def test_bad_or_missing_token_is_rejected_without_notifying(server):
    url, record = server

    assert post(url, {"alerts": [alert()]}, token="wrong") == 401
    assert post(url, {"alerts": [alert()]}, token=None) == 401
    assert calls(record) == []


def test_oversized_body_is_rejected(server):
    url, record = server

    assert post(url, None, raw=b"{" + b" " * (relay.MAX_BODY_BYTES + 1) + b"}") == 413
    assert calls(record) == []


def test_malformed_json_is_400(server):
    url, _ = server

    assert post(url, None, raw=b"not json") == 400


def test_unknown_path_is_404(server):
    url, _ = server

    assert post(url.replace(relay.ROUTE, "/other"), {}) == 404


def test_token_file_must_be_private(tmp_path):
    f = tmp_path / "t"
    f.write_text("abc\n")
    f.chmod(0o644)
    with pytest.raises(SystemExit):
        relay.load_token(str(f), env={})
    f.chmod(0o600)
    assert relay.load_token(str(f), env={}) == "abc"


def test_osascript_quoting_escapes_quotes():
    assert relay.osascript_quote('a"b\\c') == '"a\\"b\\\\c"'
