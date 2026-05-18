# Auth Workflow

Two separate auth systems — both needed for full functionality.

| Tool | Auth command | Saves to | Used for |
|---|---|---|---|
| `nlm` CLI | `nlm login` | nlm config store | Querying notebooks |
| `notebooklm-py` | `$NLM_PY login` | `~/.notebooklm/storage_state.json` | Creating notebooks, loading YouTube content |

```bash
NLM_PY=~/.claude/skills/notebooklm/.venv/bin/notebooklm
```

## Setup / Re-authenticate

**User must run these — they open a browser window:**

```bash
# nlm CLI auth
nlm login

# notebooklm-py auth
~/.claude/skills/notebooklm/.venv/bin/notebooklm login
```

Flow for both:
1. Chromium opens to Google login
2. Complete login + 2FA
3. Wait until NotebookLM homepage loads
4. Press Enter in terminal
5. Cookies/tokens saved

## Check Status

```bash
nlm login --check        # nlm CLI auth check
~/.claude/skills/notebooklm/.venv/bin/notebooklm list   # notebooklm-py check
```

## Troubleshooting

**`nlm` not found:**
```bash
uv tool install notebooklm-mcp-cli
```

**`notebooklm` venv missing:**
```bash
python3 -m venv ~/.claude/skills/notebooklm/.venv
~/.claude/skills/notebooklm/.venv/bin/pip install "notebooklm-py[browser]" -q
~/.claude/skills/notebooklm/.venv/bin/playwright install chromium
```

**Browser doesn't open:**
```bash
~/.claude/skills/notebooklm/.venv/bin/playwright install chromium
```

**Wrong Google account:**
Delete `~/.notebooklm/browser_profile` and re-run `notebooklm login`.

**Auth expires** (usually after a few weeks): Re-run both login commands.

**`nlm notebook query` returns empty or auth error:**
```bash
nlm login   # re-authenticate
```
