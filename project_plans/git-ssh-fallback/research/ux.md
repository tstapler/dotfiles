# UX Research: git-ssh-fallback

**Date**: 2026-06-24
**Phase**: Research (Phase 2)
**Feeds into**: plan.md

---

## 1. Comparable UX Patterns: Transparent CLI Wrappers

### The Silence Spectrum

Comparable tools fall into three verbosity tiers on the happy path:

**Tier 1 — Fully silent (pyenv, rbenv, rustup proxy, hub)**
Zero output on success. The wrapper is invisible. Users only learn it exists when something fails.

**Tier 2 — Silent success, verbose failure (asdf, gh passthrough)**
Nothing on success; structured error messages on failure. Wrapper identity appears only in error prefix.

**Tier 3 — Announces state changes (nvm, mise)**
Explicitly notifies the user when a non-default path was taken. Still silent when the default path is used.

### Exact Output Formats by Tool

**pyenv (shim model, PATH manipulation)**
```
# Success: total silence (exec's the real python)

# Error with source attribution:
pyenv: version `3.12.0' is not installed (set by /Users/user/project/.python-version)
```
Key patterns: `pyenv: ` prefix, backtick-apostrophe quoting, `(set by /path)` source attribution. All to stderr.

**nvm (announces state changes by design)**
```
Found '/Users/user/project/.nvmrc' with version <18>
Now using node v18.17.0 (npm v9.6.7)

# Version not installed:
N/A: version "18 -> N/A" is not yet installed.
You need to run `nvm install 18` to install it before using it.
```
nvm always announces version switches — deliberate design choice because version mismatches cause runtime errors that are painful to debug. The fallback-to-a-different-thing UX justifies verbosity.

**mise (log-level format, escape hatch pattern)**
```
# Error with hint:
mise ERROR  ~/project/.mise.toml: node@20 is not installed
hint: Run `mise install` to install tool(s) listed in ~/project/.mise.toml

# Warning:
mise WARN  gpg not found, skipping verification
mise ERROR  Run with --verbose or MISE_VERBOSE=1 for more information
```
Format: `mise <LEVEL>  <message>` (two spaces after level). The `MISE_VERBOSE=1` line on the last error is exemplary — it tells users exactly what to do to get more information.

**rustup (info: prefix, silent proxy)**
```
# Proxy on success: silent (cargo build just works)

# State changes:
info: override toolchain for '/path/to/project' is 'nightly'
info: syncing channel updates for 'stable-x86_64-apple-darwin'

# Error:
error: toolchain 'nightly-x86_64-apple-darwin' is not installed
```
All lowercase `info:`, `warning:`, `error:` — colon-space. Color-coded in terminal. All to stderr.

**hub (transparent git wrapper)**
No interception announcement at all. Hub passes commands through to git unchanged, adding its own subcommands alongside them. Errors mirror git's own format. This is the "pure transparency" model — but hub failed users who couldn't tell what hub was doing vs. git.

**gh (TTY-aware symbols)**
```
✓ Configured git protocol          # TTY success
! Authentication credentials saved  # TTY warning
X Could not create pull request     # TTY error

# Non-TTY / pipe:
Configured git protocol
warning: Authentication credentials saved in plain text
error: Could not create pull request
```
TTY-aware: symbols in terminal mode; plain prefixes otherwise. Status to stderr, data to stdout.

### SSH ProxyCommand — Closest Analogue

SSH's transparent protocol switching is architecturally identical to what git-ssh-fallback does. Its verbosity ladder:

```
# Default (no -v): completely silent about ProxyCommand
ssh internal-host
# Success: nothing. Failure: no mention of ProxyCommand.

# With -v (verbose):
debug1: Reading configuration data /Users/user/.ssh/config
debug1: Executing proxy command: exec nc -X connect -x proxy:8080 host 22
debug1: Authentication succeeded (publickey).
```

The `debug1: Executing proxy command: exec <cmd>` line is a direct precedent for how git-ssh-fallback should expose its URL rewriting at verbose level.

SSH's weakness: when ProxyCommand fails, the error doesn't reference the proxy at all. Users must use `-v` to discover why. git-ssh-fallback should do better: always mention SSH in the error even in non-verbose mode.

---

## 2. User Mental Model: When Is Silent Transparency Good?

### What a Developer Expects When They Type `git push`

The user's mental contract with `git push`:
1. Git will attempt to push the current branch to the configured remote
2. If it succeeds: brief confirmation (git's own output: `   abc123..def456  main -> main`)
3. If it fails: an error message explaining why
4. The remote URL is a configuration detail, not something to think about

**Silent transparency is good when:**
- The operation succeeds and produces the expected result
- The mechanism is predictable (users set up SSH keys knowing they'd be used)
- The tool is operating in its designed lane — this is what it's *for*

**Users want to know what happened when:**
- A non-default path was taken (fallback ≠ default)
- The failure mode is different from what they'd expect from vanilla git
- Debugging is needed (latency spike, different remote URL in error message)
- The tool might be *the reason something else breaks* (URL rewriting can confuse other tooling)

### The "Surprising Behavior" Threshold

From clig.dev: "If you change state, tell the user." The key word is *surprising*. If the behavior would surprise a user who didn't read the docs, say it.

For git-ssh-fallback: URL rewriting is surprising. A developer who typed `git push` with an HTTPS remote and sees SSH errors in a subsequent command (e.g., SSH key passphrase prompt) will be confused without a warning. **Therefore: always announce when fallback is triggered, even on success.**

When gh auth IS present and no rewrite happens: silent. That's the expected default path.

---

## 3. Debug/Verbose Output Design: `GIT_SSH_FALLBACK_DEBUG=1`

### GIT_TRACE Format (the established precedent)

Git's own trace format:
```
HH:MM:SS.MICROSECONDS  source_file:line_number  trace: <verb>: <detail>
```

Real example:
```
19:56:51.952359 git.c:458    trace: built-in: git status
19:57:46.125216 git.c:396    trace: alias expansion: st => status
```

Verb vocabulary: `built-in`, `run_command`, `exec`, `alias expansion`.

### Recommended Debug Output Format

Integrate with GIT_TRACE conventions; GIT_TRACE=1 should trigger git-ssh-fallback debug output automatically (since git-ssh-fallback is invoked by git's alias/wrapper chain). Additionally, `GIT_SSH_FALLBACK_DEBUG=1` should work standalone.

```bash
# Normal operation (no debug):
# [nothing]

# GIT_SSH_FALLBACK_DEBUG=1 — phase-by-phase trace:
[git-ssh-fallback] checking gh auth for host: github.com
[git-ssh-fallback] gh auth status: authenticated (user: tstapler)
[git-ssh-fallback] no rewrite needed: gh auth present for github.com
[git-ssh-fallback] exec: git push origin main

# Fallback path:
[git-ssh-fallback] checking gh auth for host: github.com
[git-ssh-fallback] gh auth status: not authenticated (exit 1)
[git-ssh-fallback] rewriting https://github.com/owner/repo.git → git@github.com:owner/repo.git
[git-ssh-fallback] exec: git push git@github.com:owner/repo.git main

# With source attribution (pyenv pattern — why did this decision happen?):
[git-ssh-fallback] SSH key at: /Users/user/.ssh/id_ed25519 (present)
[git-ssh-fallback] SSH agent socket: /run/user/1000/ssh-agent.socket (active)
```

**What's useful:**
- The host being checked (cross-host generalization matters)
- The gh auth verdict and why (exit code, not just "yes/no")
- The exact URL transformation (before → after)
- The exec'd command (so users can reproduce manually)
- SSH key and agent state (headless debugging)

**What's noisy (suppress even in debug):**
- git's own internal operations (let GIT_TRACE handle those)
- Credential values, key fingerprints, tokens
- Timing information (unless TRACE=2 level)
- Repeated checks for the same host in one invocation

### Verbosity Ladder

```
# Env vars (compose-friendly):
GIT_SSH_FALLBACK_DEBUG=1    # full trace (phase-by-phase)
GIT_SSH_FALLBACK_QUIET=1    # suppress even warning: messages on success

# Integration with existing:
GIT_TRACE=1 git push        # git-ssh-fallback should emit to trace when GIT_TRACE is set
```

All debug output to stderr. Bracket prefix `[git-ssh-fallback]` disambiguates from git's own trace lines.

---

## 4. Error UX: When Fallback Also Fails

### The Cascading Failure Pattern (Cargo precedent)

```
error: failed to push to https://github.com/owner/repo.git
  Caused by:
    could not read Username for 'https://github.com': terminal prompts disabled
error: SSH fallback also failed: git@github.com: Permission denied (publickey).
hint: Run `gh auth login` to authenticate via HTTPS
hint: Or ensure your SSH key is configured: ssh -T git@github.com
```

Two `error:` lines (one per attempted method). Two `hint:` lines (one per recovery path). This is the Cargo pattern for cascading failures, adapted to dual-method fallback.

### What to Include in the Error Message

**Always include:**
- Which method failed (HTTPS or SSH) and the direct error text from that method
- What the user should try next (concrete command, not vague advice)

**Include when available:**
- The original HTTPS URL (so users can identify which remote failed)
- The SSH URL that was tried (so users can test it manually: `ssh -T git@github.com`)
- Whether SSH agent is available (critical in headless contexts)

**Never include:**
- Token values, key contents, or credential material
- Internal state that only makes sense with source access

### Headless-Specific Error Guidance

In headless contexts (no SSH_AUTH_SOCK, no interactive terminal):
```
error: SSH fallback failed: no SSH agent found (SSH_AUTH_SOCK not set)
hint: Ensure ssh-agent is running in this environment
hint: For systemd user sessions: systemctl --user enable --now ssh-agent.service
```

The second hint is environment-specific — detect whether this is likely a systemd session (DBUS_SESSION_BUS_ADDRESS set) and tailor the advice accordingly.

### Recovery Hint Hierarchy

Order hints from "most likely to work" to "nuclear option":
1. `gh auth login` — restores HTTPS auth (resolves the root cause)
2. `ssh -T git@HOST` — verifies SSH works (diagnoses SSH-side failures)
3. `git remote set-url origin git@HOST:ORG/REPO` — permanent URL fix (escapes the tool entirely)
4. URL to documentation (curl pattern: last resort when hints are insufficient)

---

## 5. Observability UX: How Interception Tools Communicate

### The "Set By" Pattern (pyenv/rbenv)

pyenv and rbenv always tell users *why* a decision was made:
```
pyenv: version `3.12.0' is not installed (set by /Users/user/project/.python-version)
rbenv: version `3.2.0' is not installed (set by /path/to/.ruby-version)
$ rbenv version
3.2.2 (set by /Users/user/.rbenv/version)
```

For git-ssh-fallback, apply this to the fallback warning:
```
warning: falling back to SSH (gh not authenticated for github.com)
```

The `(gh not authenticated for github.com)` parenthetical is the "set by" equivalent — it explains the *reason* for the non-default behavior.

### The Escape Hatch Pattern (mise, rustc)

Both mise and rustc end error messages with the escape hatch to more information:
```
mise ERROR  Run with --verbose or MISE_VERBOSE=1 for more information
rustc: For more information about this error, try `rustc --explain E0308`
```

git-ssh-fallback should follow this pattern on non-trivial failures:
```
error: SSH fallback failed: Permission denied (publickey).
hint: Run with GIT_SSH_FALLBACK_DEBUG=1 for detailed diagnostic output
```

### TTY vs Non-TTY Discipline

Like `gh`, adapt output based on whether stderr is a TTY:

```bash
# TTY (interactive terminal):
⚠ gh auth not found for github.com, falling back to SSH
  hint: Run `gh auth login` to restore HTTPS authentication

# Non-TTY (pipe, script, Claude Code subagent):
warning: gh auth not found for github.com, falling back to SSH
hint: Run `gh auth login` to restore HTTPS authentication
```

Respect `NO_COLOR`. This distinction matters because Claude Code subagents and CI systems consume stderr as text — symbols don't add value there, and some tools misinterpret them.

### The Bracket Prefix Convention

`[git-ssh-fallback]` prefix on all wrapper-originated messages (borrowed from mise's log format and common in proxy tools). This lets users grep specifically for wrapper messages:
```
git push 2>&1 | grep '\[git-ssh-fallback\]'
```

In non-debug mode, use the git-native `warning:`/`hint:` prefixes without brackets (blends with git's own output style). In debug mode, bracket prefix for grep-ability.

---

## 6. Jobs-to-be-Done: Serving All Three Levels

### Functional Job: "git push works"

Design implications:
- Fallback must be fast (< 500ms overhead) — users notice latency on every push
- Must not require any extra keystrokes or prompts on the success path
- Exit code must be the git operation's exit code, not the wrapper's — `git push && deploy.sh` must work

### Emotional Job: "I don't have to think about auth"

Design implications:
- On success: **total silence**. Any output on the happy path breaks this job.
- On failure: **clear, calm error message** with a concrete fix. Not a wall of trace. The user's emotional state is already "something broke" — don't add cognitive load.
- The `warning:` on fallback should feel informational, not alarming. A fallback is a feature, not a failure.

The distinction: `warning: falling back to SSH (gh not authenticated)` feels informational. `ERROR: HTTPS authentication failed, attempting SSH recovery` feels alarming even though it describes the same thing.

### Social Job: "my dotfiles setup just works on any machine"

Design implications:
- The tool must announce its own presence in diagnostic output — a developer cloning this config on a new machine needs to know the wrapper is active
- Debug output should include config source: `[git-ssh-fallback] config: loaded from ~/.gitconfig (git wrapper alias)`
- Bootstrap messages (first-run on new machine) could print a one-time notice: `[git-ssh-fallback] installed and active — use GIT_SSH_FALLBACK_DEBUG=1 to trace decisions`
- The social story is "this is a dotfile; it just works" — so the README and the first-run experience matter as much as the runtime UX

---

## Design Recommendations Summary

### Default Mode (no env vars set)

| Scenario | Output |
|----------|--------|
| gh auth present, HTTPS proceeds | Silent |
| gh auth missing, SSH fallback succeeds | `warning: falling back to SSH (gh not authenticated for HOST)` to stderr |
| gh auth missing, SSH fallback fails | Two `error:` lines + two `hint:` lines to stderr |
| Both methods fail in headless context | Error includes SSH agent diagnostic hint |

### Verbose Mode (`GIT_SSH_FALLBACK_DEBUG=1`)

Phase-by-phase trace with `[git-ssh-fallback]` bracket prefix, including: host checked, auth verdict, URL transformation, exec'd command, SSH key/agent state.

### Stream Discipline

- stdout: git's own output, unmodified. Never put wrapper messages here.
- stderr: all wrapper messages (warning, error, hint, debug)
- Exit code: passthrough from the git operation

### Prefix Convention

Normal output: git-native prefixes (`warning:`, `hint:`, `error:`) — blends with git's own output.
Debug output: `[git-ssh-fallback]` bracket prefix — grep-able, distinct from git's trace format.
TTY mode: optionally add `⚠`/`✗` symbols before `warning:`/`error:`.
Non-TTY/NO_COLOR: plain text only.

---

## Sources

- [clig.dev — Command Line Interface Guidelines](https://clig.dev/)
- [git-scm.com — GIT_TRACE documentation](https://git-scm.com/docs/api-trace)
- [git-scm.com — Environment Variables](https://git-scm.com/book/en/v2/Git-Internals-Environment-Variables)
- pyenv error format (confirmed from GitHub issues)
- rbenv source + documentation
- nvm documentation — `nvm use` output format
- mise GitHub discussions — stderr format evidence
- rustup documentation — `info:` prefix pattern
- GitHub CLI (gh) source — TTY-aware output pattern
- Cargo error format — cascading `Caused by:` pattern
- SSH config ProxyCommand `debug1:` format
- Eric Raymond, *The Art of Unix Programming* — Rule of Silence
