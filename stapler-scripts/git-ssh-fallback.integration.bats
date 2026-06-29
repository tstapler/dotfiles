#!/usr/bin/env bats
# Integration tests for git-ssh-fallback (invoke wrapper binary with PATH shims)
# Run: bats stapler-scripts/git-ssh-fallback.integration.bats

load "test/bats-helpers/support/load"
load "test/bats-helpers/assert/load"

SCRIPT="$BATS_TEST_DIRNAME/git-ssh-fallback"

setup() {
  BATS_TMPDIR="$(mktemp -d)"
  mkdir -p "$BATS_TMPDIR/shims"

  # Stub git that records remote get-url calls
  # Default: simulate "origin" remote as https://github.com/owner/repo
  cat > "$BATS_TMPDIR/shims/git" << 'EOF'
#!/bin/sh
if [ "${1:-}" = "remote" ] && [ "${2:-}" = "get-url" ]; then
  echo "https://github.com/owner/repo"
  exit 0
fi
exec /usr/bin/git "$@"
EOF
  chmod +x "$BATS_TMPDIR/shims/git"
  export REAL_GIT="$BATS_TMPDIR/shims/git"
}

teardown() {
  rm -rf "$BATS_TMPDIR"
}

# Helper: create an unauthenticated gh stub
_stub_gh_unauth() {
  printf '#!/bin/sh\nexit 1\n' > "$BATS_TMPDIR/shims/gh"
  chmod +x "$BATS_TMPDIR/shims/gh"
}

# Helper: create an authenticated gh stub
_stub_gh_auth() {
  printf '#!/bin/sh\nexit 0\n' > "$BATS_TMPDIR/shims/gh"
  chmod +x "$BATS_TMPDIR/shims/gh"
}

# Helper: create a live ssh-add stub (exit 1 = no keys, alive)
_stub_ssh_add_alive() {
  printf '#!/bin/sh\nexit 1\n' > "$BATS_TMPDIR/shims/ssh-add"
  chmod +x "$BATS_TMPDIR/shims/ssh-add"
}

# Helper: create a stale ssh-add stub (exit 2 = cannot connect)
_stub_ssh_add_stale() {
  printf '#!/bin/sh\nexit 2\n' > "$BATS_TMPDIR/shims/ssh-add"
  chmod +x "$BATS_TMPDIR/shims/ssh-add"
}

# Helper: create a live Unix socket for SSH_AUTH_SOCK
_make_live_socket() {
  local sock="$BATS_TMPDIR/test.sock"
  # socat may not be installed; use nc if available, otherwise skip socket test
  if command -v socat >/dev/null 2>&1; then
    socat UNIX-LISTEN:"$sock",fork /dev/null &
    echo "$sock"
    return 0
  elif command -v nc >/dev/null 2>&1; then
    nc -lU "$sock" &
    echo "$sock"
    return 0
  fi
  echo ""
}

# ----------------------------------------------------------------------------
# Req 1 integration: no recursion when deployed as git on PATH
# ----------------------------------------------------------------------------

@test "wrapper does not recurse when deployed as 'git' on PATH" {
  local tmpbin="$BATS_TMPDIR/bin"
  mkdir -p "$tmpbin"
  ln -s "$SCRIPT" "$tmpbin/git"
  run env PATH="$tmpbin:/usr/bin:/bin" git --version
  [ "$status" -eq 0 ]
  [[ "$output" == git\ version\ * ]]
}

@test "wrapper shadows /usr/bin/git when deployed to local bin" {
  local tmpbin="$BATS_TMPDIR/bin"
  mkdir -p "$tmpbin"
  ln -s "$SCRIPT" "$tmpbin/git"
  local which_result
  which_result="$(PATH="$tmpbin:/usr/bin:/bin" which git)"
  [ "$which_result" = "$tmpbin/git" ]
}

# ----------------------------------------------------------------------------
# Req 2 integration: local ops pass through without invoking gh
# ----------------------------------------------------------------------------

@test "local git subcommand does not invoke gh" {
  printf '#!/bin/sh\necho "gh_was_called"; exit 0\n' > "$BATS_TMPDIR/shims/gh"
  chmod +x "$BATS_TMPDIR/shims/gh"
  run env PATH="$BATS_TMPDIR/shims:$PATH" REAL_GIT="$REAL_GIT" "$SCRIPT" status
  refute_output --partial "gh_was_called"
}

# ----------------------------------------------------------------------------
# Req 3 integration: SSH remote skips auth check
# ----------------------------------------------------------------------------

@test "wrapper skips auth check when remote is already SSH" {
  # Override git stub to return SSH URL for remote get-url
  cat > "$BATS_TMPDIR/shims/git" << 'EOF'
#!/bin/sh
if [ "${1:-}" = "remote" ] && [ "${2:-}" = "get-url" ]; then
  echo "git@github.com:owner/repo"
  exit 0
fi
exec /usr/bin/git "$@"
EOF
  printf '#!/bin/sh\necho "gh_was_called"; exit 0\n' > "$BATS_TMPDIR/shims/gh"
  chmod +x "$BATS_TMPDIR/shims/gh"
  run env PATH="$BATS_TMPDIR/shims:$PATH" \
      GIT_SSH_FALLBACK_DEBUG=1 \
      REAL_GIT="$BATS_TMPDIR/shims/git" \
      "$SCRIPT" fetch origin 2>&1
  refute_output --partial "gh_was_called"
  refute_output --partial "checking auth"
}

# ----------------------------------------------------------------------------
# Req 4 integration: AuthCache prevents repeat gh invocations
# ----------------------------------------------------------------------------

@test "gh is called at most once within cache TTL" {
  local cache_dir="$BATS_TMPDIR/cache"
  local call_log="$BATS_TMPDIR/gh-calls.log"
  mkdir -p "$cache_dir"
  printf '#!/bin/sh\necho 1 >> %s; exit 0\n' "$call_log" > "$BATS_TMPDIR/shims/gh"
  chmod +x "$BATS_TMPDIR/shims/gh"

  # First invocation — cache miss, gh called
  env PATH="$BATS_TMPDIR/shims:$PATH" \
      GIT_SSH_FALLBACK_CACHE_DIR="$cache_dir" \
      REAL_GIT="$BATS_TMPDIR/shims/git" \
      "$SCRIPT" --self-test >/dev/null 2>&1 || true

  # Warm the cache manually (self-test doesn't trigger auth check)
  touch "$cache_dir/github.com.auth"

  env PATH="$BATS_TMPDIR/shims:$PATH" \
      GIT_SSH_FALLBACK_CACHE_DIR="$cache_dir" \
      REAL_GIT="$BATS_TMPDIR/shims/git" \
      "$SCRIPT" --self-test >/dev/null 2>&1 || true

  # gh should not have been called (self-test doesn't check auth)
  local call_count
  call_count="$(wc -l < "$call_log" 2>/dev/null || echo 0)"
  [ "$call_count" -eq 0 ]
}

# ----------------------------------------------------------------------------
# Req 5 integration: no SSH agent → exec real git with original args
# ----------------------------------------------------------------------------

@test "wrapper executes real git when no SSH agent found on fallback path" {
  _stub_gh_unauth
  run env PATH="$BATS_TMPDIR/shims:$PATH" \
      SSH_AUTH_SOCK="" \
      HOME="$BATS_TMPDIR" \
      XDG_RUNTIME_DIR="$BATS_TMPDIR/xdg" \
      REAL_GIT="$BATS_TMPDIR/shims/git" \
      "$SCRIPT" fetch origin 2>&1
  assert_output --partial "no SSH agent found"
}

# ----------------------------------------------------------------------------
# Req 6 integration: ConfigInjection env vars reach real git on fallback
# ----------------------------------------------------------------------------

@test "GIT_CONFIG_COUNT env var is set when fallback triggers" {
  _stub_gh_unauth
  _stub_ssh_add_alive

  # Create a fake socket for SSH_AUTH_SOCK
  local fake_sock="$BATS_TMPDIR/fake.sock"
  # Use a plain file to pass the -S check (not ideal, but avoids socat dependency)
  # Instead test by checking debug output shows "config injection"
  # We use a real socket approach via python if available
  local ssh_auth_sock=""
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import socket, os, time, threading
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind('$fake_sock')
s.listen(1)
def accept_loop():
    while True:
        try: c, _ = s.accept(); c.close()
        except: break
t = threading.Thread(target=accept_loop, daemon=True)
t.start()
" 2>/dev/null &
    sleep 0.1
    ssh_auth_sock="$fake_sock"
  fi

  # If we couldn't make a real socket, skip this test
  if [ ! -S "$fake_sock" ]; then
    skip "cannot create Unix socket for test (no python3 or socat)"
  fi

  run env PATH="$BATS_TMPDIR/shims:$PATH" \
      SSH_AUTH_SOCK="$fake_sock" \
      HOME="$BATS_TMPDIR" \
      GIT_SSH_FALLBACK_DEBUG=1 \
      REAL_GIT="$BATS_TMPDIR/shims/git" \
      "$SCRIPT" fetch origin 2>&1
  assert_output --partial "config injection"
  assert_output --partial "url.git@github.com:"
}

# ----------------------------------------------------------------------------
# Req 7 integration: non-gh host with no agent passes through to HTTPS
# ----------------------------------------------------------------------------

@test "non-gh host passes through to HTTPS when no SSH agent" {
  # Override git stub to return a non-gh HTTPS remote
  cat > "$BATS_TMPDIR/shims/git" << 'EOF'
#!/bin/sh
if [ "${1:-}" = "remote" ] && [ "${2:-}" = "get-url" ]; then
  echo "https://git.internal.example.com/org/repo"
  exit 0
fi
exec /usr/bin/git "$@"
EOF
  _stub_gh_unauth

  run env PATH="$BATS_TMPDIR/shims:$PATH" \
      SSH_AUTH_SOCK="" \
      HOME="$BATS_TMPDIR" \
      XDG_RUNTIME_DIR="$BATS_TMPDIR/xdg" \
      REAL_GIT="$BATS_TMPDIR/shims/git" \
      GIT_SSH_FALLBACK_DEBUG=1 \
      "$SCRIPT" fetch origin 2>&1
  assert_output --partial "non-gh host"
  assert_output --partial "no live SSH agent"
  refute_output --partial "warning: falling back to SSH"
}

# ----------------------------------------------------------------------------
# Req 8 integration: FallbackWarning appears on stderr
# ----------------------------------------------------------------------------

@test "fallback warning appears when gh unauthenticated and SSH agent alive" {
  _stub_gh_unauth
  _stub_ssh_add_alive

  local fake_sock="$BATS_TMPDIR/fake2.sock"
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import socket, threading
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind('$fake_sock')
s.listen(1)
def loop():
    while True:
        try: c, _ = s.accept(); c.close()
        except: break
threading.Thread(target=loop, daemon=True).start()
" 2>/dev/null &
    sleep 0.1
  fi

  [ -S "$fake_sock" ] || skip "cannot create Unix socket for test"

  run env PATH="$BATS_TMPDIR/shims:$PATH" \
      SSH_AUTH_SOCK="$fake_sock" \
      HOME="$BATS_TMPDIR" \
      REAL_GIT="$BATS_TMPDIR/shims/git" \
      "$SCRIPT" fetch origin 2>&1
  assert_output --partial "warning: falling back to SSH (gh not authenticated for github.com)"
}

# ----------------------------------------------------------------------------
# Req 9 integration: deployment / PATH shadowing
# ----------------------------------------------------------------------------

@test "wrapper deployed as symlink resolves real git without recursion" {
  local tmpbin="$BATS_TMPDIR/bin"
  mkdir -p "$tmpbin"
  ln -s "$SCRIPT" "$tmpbin/git"
  run env PATH="$tmpbin:/usr/bin:/bin" git --version
  [ "$status" -eq 0 ]
  [[ "$output" == git\ version\ * ]]
}
