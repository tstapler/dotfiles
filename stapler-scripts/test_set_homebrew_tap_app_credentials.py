"""Tests for set-homebrew-tap-app-credentials. Run: uv run --with pytest pytest stapler-scripts/test_set_homebrew_tap_app_credentials.py"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("set-homebrew-tap-app-credentials")
KEY = "-----BEGIN RSA PRIVATE KEY-----\nSENTINEL-KEY-BODY\n-----END RSA PRIVATE KEY-----\n"


def load_module():
    loader = importlib.machinery.SourceFileLoader("tapcreds", str(SCRIPT))
    spec = importlib.util.spec_from_loader("tapcreds", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


tc = load_module()


def scripted(*answers: str):
    queue = list(answers)
    return lambda _prompt: queue.pop(0)


def item(fields=None, files=None):
    return {
        "id": "ITEMID",
        "title": "tstapler Homebrew Tap",
        "vault": {"id": "VAULTID", "name": "Private"},
        "fields": fields
        if fields is not None
        else [{"label": "Client ID", "value": "Iv23liCLIENT"}],
        "files": files if files is not None else [{"id": "f1", "name": "key.pem"}],
    }


# --- choose ----------------------------------------------------------------------------------


def test_choose_returns_zero_based_index():
    assert tc.choose("t", ["a", "b", "c"], interactive=True, read=scripted("2")) == 1


def test_choose_reprompts_on_bad_input_then_accepts():
    assert (
        tc.choose("t", ["a", "b"], interactive=True, read=scripted("x", "0", "9", "1"))
        == 0
    )


def test_choose_quit_is_fatal():
    with pytest.raises(tc.Fatal, match="cancelled"):
        tc.choose("t", ["a", "b"], interactive=True, read=scripted("q"))


def test_choose_eof_is_fatal():
    def eof(_prompt: str) -> str:
        raise EOFError

    with pytest.raises(tc.Fatal, match="cancelled"):
        tc.choose("t", ["a"], interactive=True, read=eof)


def test_choose_without_interaction_fails_instead_of_prompting():
    with pytest.raises(tc.Fatal, match="--no-input"):
        tc.choose("t", ["a", "b"], interactive=False, read=scripted())


# --- client id -------------------------------------------------------------------------------


def test_exact_client_id_field_needs_no_prompt():
    assert tc.pick_client_id(item(), None, interactive=False, read=scripted()) == (
        "Iv23liCLIENT",
        "Client ID",
    )


def test_override_wins():
    assert (
        tc.pick_client_id(item(), "Iv1.manual", interactive=False, read=scripted())[0]
        == "Iv1.manual"
    )


def test_several_client_id_fields_prompt():
    fields = [
        {"label": "Client ID", "value": "one"},
        {"label": "App client id", "value": "two"},
    ]
    assert tc.pick_client_id(
        item(fields=fields), None, interactive=True, read=scripted("2")
    ) == ("two", "App client id")


def test_no_client_id_field_offers_all_labelled_fields_without_showing_values(capsys):
    fields = [
        {"label": "Client secret", "value": "SENTINEL-SECRET", "type": "CONCEALED"},
        {"label": "App", "value": "x"},
    ]
    assert (
        tc.pick_client_id(
            item(fields=fields), None, interactive=True, read=scripted("2")
        )[0]
        == "x"
    )
    shown = capsys.readouterr().err
    assert "Client secret (concealed)" in shown and "SENTINEL-SECRET" not in shown


def test_ambiguous_client_id_without_interaction_fails():
    fields = [
        {"label": "Client ID", "value": "one"},
        {"label": "Client ID", "value": "two"},
    ]
    with pytest.raises(tc.Fatal):
        tc.pick_client_id(item(fields=fields), None, interactive=False, read=scripted())


def test_empty_item_requires_override():
    with pytest.raises(tc.Fatal, match="--client-id"):
        tc.pick_client_id(item(fields=[]), None, interactive=True, read=scripted())


# --- pem -------------------------------------------------------------------------------------


def test_single_pem_is_chosen_silently():
    files = [{"name": "notes.txt"}, {"name": "Key.PEM"}]
    assert (
        tc.pick_pem(item(files=files), interactive=False, read=scripted()) == "Key.PEM"
    )


def test_several_pems_prompt():
    files = [{"name": "old.pem"}, {"name": "new.pem"}]
    assert (
        tc.pick_pem(item(files=files), interactive=True, read=scripted("2"))
        == "new.pem"
    )


def test_no_pem_offers_every_file():
    files = [{"name": "a.bin"}, {"name": "b.bin"}]
    assert (
        tc.pick_pem(item(files=files), interactive=True, read=scripted("1")) == "a.bin"
    )


def test_no_attachments_is_fatal():
    with pytest.raises(tc.Fatal, match="attach"):
        tc.pick_pem(item(files=[]), interactive=True, read=scripted())


# --- missing item falls back to a picker ------------------------------------------------------


def test_missing_item_offers_a_filtered_list(monkeypatch):
    listing = [
        {"id": "A", "title": "Unrelated", "vault": {"name": "Private"}},
        {"id": "B", "title": "tstapler Homebrew Tap", "vault": {"name": "Private"}},
    ]
    calls: list[list[str]] = []

    def fake_run(cmd, *, stdin=None):
        calls.append(list(cmd))
        if cmd[:3] == ["op", "item", "list"]:
            return json.dumps(listing)
        if cmd[3] == "wrong name":
            raise tc.Fatal("`op item` failed: isn't an item")
        return json.dumps(item())

    monkeypatch.setattr(tc, "run", fake_run)
    got = tc.load_item("wrong name", None, interactive=True, read=scripted("", "1"))
    assert got["id"] == "ITEMID"
    assert calls[-1][:4] == ["op", "item", "get", "B"]


def test_missing_item_without_interaction_fails(monkeypatch):
    def fake_run(cmd, *, stdin=None):
        raise tc.Fatal("`op item` failed: isn't an item")

    monkeypatch.setattr(tc, "run", fake_run)
    with pytest.raises(tc.Fatal):
        tc.load_item("x", None, interactive=False, read=scripted())


# --- end to end with stub op/gh ---------------------------------------------------------------


@pytest.fixture
def stubs(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "calls.log"
    (tmp_path / "item.json").write_text(json.dumps(item()))
    (tmp_path / "key.pem").write_text(KEY)
    op = bindir / "op"
    op.write_text(
        f"""#!/usr/bin/env bash
echo "op $*" >> {log}
case "$1 $2" in
  "item get") cat "${{ITEM_JSON:-{tmp_path}/item.json}}" ;;
  "read "*) cat "${{KEY_FILE:-{tmp_path}/key.pem}}" ;;
esac
"""
    )
    gh = bindir / "gh"
    gh.write_text(
        f"""#!/usr/bin/env bash
echo "gh $*" >> {log}
case "$1 $2" in
  "variable set") exit 0 ;;
  "secret set") cat > {tmp_path}/stdin.txt ;;
  "variable list") echo "${{LIST_VAR-HOMEBREW_TAP_APP_CLIENT_ID}}" ;;
  "secret list") echo "${{LIST_SECRET-HOMEBREW_TAP_APP_PRIVATE_KEY}}" ;;
esac
"""
    )
    for path in (op, gh):
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return tmp_path, log


def run_script(tmp_path, *args, env_extra=None):
    env = {
        **os.environ,
        "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
        **(env_extra or {}),
    }
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--no-input", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_dry_run_prints_findings_and_never_reads_the_key(stubs):
    tmp_path, log = stubs
    result = run_script(tmp_path, "-n", "a/b")
    assert result.returncode == 0
    assert "Iv23liCLIENT" in result.stdout and "key.pem" in result.stdout
    assert "op read" not in log.read_text()


def test_real_run_sets_both_values_and_never_exposes_the_key(stubs):
    tmp_path, log = stubs
    result = run_script(tmp_path, "a/b", "c/d")
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("ok      ") == 2
    assert "SENTINEL-KEY" in (tmp_path / "stdin.txt").read_text()
    assert "SENTINEL" not in result.stdout + result.stderr + log.read_text()
    assert log.read_text().count("op read") == 1


def test_non_pem_attachment_is_rejected_before_touching_any_repo(stubs):
    tmp_path, log = stubs
    (tmp_path / "notpem.txt").write_text("Iv1.client-secret-value")
    result = run_script(
        tmp_path, "a/b", env_extra={"KEY_FILE": str(tmp_path / "notpem.txt")}
    )
    assert result.returncode == 1 and "not a PEM private key" in result.stderr
    assert "gh variable set" not in log.read_text()


def test_unlisted_secret_is_reported_as_unverified(stubs):
    tmp_path, _ = stubs
    result = run_script(tmp_path, "a/b", env_extra={"LIST_SECRET": ""})
    assert result.returncode == 1 and "UNVERIFIED" in result.stderr


def test_two_pems_without_interaction_fails_with_a_reason(stubs):
    tmp_path, _ = stubs
    (tmp_path / "two.json").write_text(
        json.dumps(item(files=[{"name": "a.pem"}, {"name": "b.pem"}]))
    )
    result = run_script(
        tmp_path, "a/b", env_extra={"ITEM_JSON": str(tmp_path / "two.json")}
    )
    assert result.returncode == 1 and "--no-input" in result.stderr


def test_bad_repo_name_is_rejected(stubs):
    tmp_path, _ = stubs
    result = run_script(tmp_path, "notarepo")
    assert result.returncode == 2 and "OWNER/REPO" in result.stderr
