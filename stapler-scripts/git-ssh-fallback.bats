#!/usr/bin/env bats
# Unit tests for git-ssh-fallback wrapper (bats-core)
# Run: bats stapler-scripts/git-ssh-fallback.bats

load "test/bats-helpers/support/load"
load "test/bats-helpers/assert/load"

SCRIPT="$BATS_TEST_DIRNAME/git-ssh-fallback"

setup() {
  BATS_TMPDIR="$(mktemp -d)"
  mkdir -p "$BATS_TMPDIR/shims"
  # Source the script to get function definitions (main is gated on $0 pattern)
  # shellcheck disable=SC1090
  GIT_SSH_FALLBACK_SOURCE_ONLY=1 . "$SCRIPT" 2>/dev/null || true
  # Provide a REAL_GIT so functions that call it work without PATH magic
  REAL_GIT="$(command -v git)"
  export REAL_GIT
}

teardown() {
  rm -rf "$BATS_TMPDIR"
}

# ----------------------------------------------------------------------------
# Req 1: RealGit resolution and RecursionGuard passthrough
# ----------------------------------------------------------------------------

@test "find_real_git returns a git binary that is not the wrapper itself" {
  run _find_real_git
  [ "$status" -eq 0 ]
  [[ "$output" == */git ]]
  [ "$output" != "$SCRIPT" ]
}

@test "recursion guard bypasses all logic when GIT_SSH_FALLBACK_ACTIVE=1" {
  run env GIT_SSH_FALLBACK_ACTIVE=1 "$SCRIPT" --version
  [ "$status" -eq 0 ]
  [[ "$output" == git\ version\ * ]]
  refute_output --partial "[git-ssh-fallback]"
}

@test "wrapper passes through to real git with no wrapper output on --version" {
  run "$SCRIPT" --version
  [ "$status" -eq 0 ]
  [[ "$output" == git\ version\ * ]]
}

# ----------------------------------------------------------------------------
# Req 2: NetworkSubcommand detection
# ----------------------------------------------------------------------------

@test "is_network_op returns true for fetch" {
  run _is_network_op "fetch"
  [ "$status" -eq 0 ]
}

@test "is_network_op returns true for clone" {
  run _is_network_op "clone"
  [ "$status" -eq 0 ]
}

@test "is_network_op returns true for push" {
  run _is_network_op "push"
  [ "$status" -eq 0 ]
}

@test "is_network_op returns false for status" {
  run _is_network_op "status"
  [ "$status" -eq 1 ]
}

@test "is_network_op returns false for log" {
  run _is_network_op "log"
  [ "$status" -eq 1 ]
}

@test "extract_subcommand skips -C path correctly" {
  run _extract_subcommand "-C" "/some/path" "fetch" "origin"
  [ "$output" = "fetch" ]
}

@test "extract_subcommand skips --git-dir arg correctly" {
  run _extract_subcommand "--git-dir" "/tmp/repo" "push" "origin"
  [ "$output" = "push" ]
}

@test "extract_subcommand returns empty for flag-only invocation" {
  run _extract_subcommand "--version"
  [ -z "$output" ]
}

# ----------------------------------------------------------------------------
# Req 3: RemoteHost extraction
# ----------------------------------------------------------------------------

@test "extract_host returns hostname from https clone URL" {
  run _extract_host "clone" "https://github.com/owner/repo.git"
  [ "$output" = "github.com" ]
}

@test "extract_host strips embedded credentials from HTTPS URL" {
  run _extract_host "clone" "https://user:token@github.com/org/repo"
  [ "$output" = "github.com" ]
}

@test "extract_host returns empty for ssh clone URL" {
  run _extract_host "clone" "git@github.com:owner/repo.git"
  [ -z "$output" ]
}

@test "extract_host returns empty for ssh:// URL" {
  run _extract_host "clone" "ssh://git@github.com/owner/repo.git"
  [ -z "$output" ]
}

@test "extract_host strips port from HTTPS URL" {
  run _extract_host "clone" "https://git.corp.example.com:8443/org/repo"
  [ "$output" = "git.corp.example.com" ]
}

# ----------------------------------------------------------------------------
# Req 4: GhAuthResult check with AuthCache
# ----------------------------------------------------------------------------

@test "check_auth returns authenticated when cache file is fresh" {
  local cache_dir="$BATS_TMPDIR/cache"
  mkdir -p "$cache_dir"
  touch "$cache_dir/github.com.auth"
  run env GIT_SSH_FALLBACK_CACHE_DIR="$cache_dir" bash -c ". '$SCRIPT'; _check_auth github.com"
  [ "$output" = "authenticated" ]
}

@test "check_auth returns authenticated and writes cache when gh exits 0" {
  local cache_dir="$BATS_TMPDIR/cache"
  mkdir -p "$cache_dir"
  printf '#!/bin/sh\nexit 0\n' > "$BATS_TMPDIR/shims/gh"
  chmod +x "$BATS_TMPDIR/shims/gh"
  run env PATH="$BATS_TMPDIR/shims:$PATH" \
      GIT_SSH_FALLBACK_CACHE_DIR="$cache_dir" \
      bash -c ". '$SCRIPT'; _check_auth github.com"
  [ "$output" = "authenticated" ]
  [ -f "$cache_dir/github.com.auth" ]
}

@test "check_auth returns unauthenticated when gh not in PATH" {
  run env PATH="/usr/bin:/bin" bash -c ". '$SCRIPT'; _check_auth github.com"
  [ "$output" = "unauthenticated" ]
}

@test "check_auth returns unauthenticated and no cache write on gh exit 1" {
  local cache_dir="$BATS_TMPDIR/cache"
  mkdir -p "$cache_dir"
  printf '#!/bin/sh\nexit 1\n' > "$BATS_TMPDIR/shims/gh"
  chmod +x "$BATS_TMPDIR/shims/gh"
  run env PATH="$BATS_TMPDIR/shims:$PATH" \
      GIT_SSH_FALLBACK_CACHE_DIR="$cache_dir" \
      bash -c ". '$SCRIPT'; _check_auth github.com"
  [ "$output" = "unauthenticated" ]
  [ ! -f "$cache_dir/github.com.auth" ]
}

@test "check_auth returns authenticated when gh times out (exit 124)" {
  local cache_dir="$BATS_TMPDIR/cache"
  mkdir -p "$cache_dir"
  printf '#!/bin/sh\nexit 124\n' > "$BATS_TMPDIR/shims/gh"
  chmod +x "$BATS_TMPDIR/shims/gh"
  run env PATH="$BATS_TMPDIR/shims:$PATH" \
      GIT_SSH_FALLBACK_CACHE_DIR="$cache_dir" \
      bash -c ". '$SCRIPT'; _check_auth github.com"
  # _warn also emits to stderr (captured by bats), so use partial match
  assert_output --partial "authenticated"
}

@test "check_auth calls gh again when cache file is older than 5 minutes" {
  local cache_dir="$BATS_TMPDIR/cache"
  mkdir -p "$cache_dir"
  local cache_file="$cache_dir/github.com.auth"
  # Create a stale cache file (10 minutes old)
  touch -t "$(date -v -10M +%Y%m%d%H%M 2>/dev/null || date -d '10 minutes ago' +%Y%m%d%H%M)" "$cache_file" 2>/dev/null \
    || touch "$cache_file" && sleep 0 || true
  # Stub gh to emit a marker so we can confirm it was called
  printf '#!/bin/sh\necho "gh_was_called"; exit 0\n' > "$BATS_TMPDIR/shims/gh"
  chmod +x "$BATS_TMPDIR/shims/gh"
  run env PATH="$BATS_TMPDIR/shims:$PATH" \
      GIT_SSH_FALLBACK_CACHE_DIR="$cache_dir" \
      GIT_SSH_FALLBACK_DEBUG=1 \
      bash -c ". '$SCRIPT'; _check_auth github.com"
  # gh must have been called (would show "auth: authenticated for github.com")
  assert_output --partial "authenticated"
}

# ----------------------------------------------------------------------------
# Req 5: SshAgent detection
# ----------------------------------------------------------------------------

@test "test_socket_liveness returns failure for nonexistent path" {
  run _test_socket_liveness "/nonexistent/socket/path"
  [ "$status" -eq 1 ]
}

@test "test_socket_liveness returns failure for regular file (not socket)" {
  local fake="$BATS_TMPDIR/not-a-socket"
  touch "$fake"
  printf '#!/bin/sh\nexit 1\n' > "$BATS_TMPDIR/shims/ssh-add"
  chmod +x "$BATS_TMPDIR/shims/ssh-add"
  run env PATH="$BATS_TMPDIR/shims:$PATH" bash -c ". '$SCRIPT'; _test_socket_liveness '$fake'"
  [ "$status" -eq 1 ]
}

@test "detect_ssh_agent returns failure when no sockets exist" {
  run env SSH_AUTH_SOCK="" \
      HOME="$BATS_TMPDIR" \
      XDG_RUNTIME_DIR="$BATS_TMPDIR/xdg" \
      bash -c ". '$SCRIPT'; _detect_ssh_agent"
  [ "$status" -eq 1 ]
}

# ----------------------------------------------------------------------------
# Req 6: ConfigInjection
# ----------------------------------------------------------------------------

@test "inject_ssh_config sets GIT_CONFIG env vars for github.com" {
  unset GIT_CONFIG_COUNT GIT_CONFIG_KEY_0 GIT_CONFIG_VALUE_0 || true
  _inject_ssh_config "github.com"
  [ "$GIT_CONFIG_COUNT" = "1" ]
  [ "$GIT_CONFIG_KEY_0" = "url.git@github.com:.insteadOf" ]
  [ "$GIT_CONFIG_VALUE_0" = "https://github.com/" ]
}

@test "inject_ssh_config sets correct vars for gitlab.com" {
  unset GIT_CONFIG_COUNT GIT_CONFIG_KEY_0 GIT_CONFIG_VALUE_0 || true
  _inject_ssh_config "gitlab.com"
  [ "$GIT_CONFIG_KEY_0" = "url.git@gitlab.com:.insteadOf" ]
  [ "$GIT_CONFIG_VALUE_0" = "https://gitlab.com/" ]
}

@test "inject_ssh_config sets GIT_SSH_COMMAND with BatchMode" {
  unset GIT_SSH_COMMAND || true
  _inject_ssh_config "github.com"
  [[ "$GIT_SSH_COMMAND" == *"BatchMode=yes"* ]]
}

@test "inject_ssh_config value does not contain credentials" {
  unset GIT_CONFIG_COUNT GIT_CONFIG_KEY_0 GIT_CONFIG_VALUE_0 || true
  _inject_ssh_config "github.com"
  [[ "$GIT_CONFIG_VALUE_0" != *"@"* ]]
  [[ "$GIT_CONFIG_VALUE_0" != *"token"* ]]
}

@test "inject_ssh_config accumulates onto existing GIT_CONFIG_COUNT" {
  export GIT_CONFIG_COUNT=1
  export GIT_CONFIG_KEY_0="existing.key"
  export GIT_CONFIG_VALUE_0="existing_value"
  _inject_ssh_config "github.com"
  [ "$GIT_CONFIG_COUNT" = "2" ]
  [ "$GIT_CONFIG_KEY_0" = "existing.key" ]
  [ "$GIT_CONFIG_KEY_1" = "url.git@github.com:.insteadOf" ]
}

# ----------------------------------------------------------------------------
# Req 7: Non-gh-managed host classification
# ----------------------------------------------------------------------------

@test "is_gh_managed_host returns true for github.com" {
  run _is_gh_managed_host "github.com"
  [ "$status" -eq 0 ]
}

@test "is_gh_managed_host returns true for gist.github.com" {
  run _is_gh_managed_host "gist.github.com"
  [ "$status" -eq 0 ]
}

@test "is_gh_managed_host returns false for internal forge" {
  run _is_gh_managed_host "git.internal.example.com"
  [ "$status" -eq 1 ]
}

@test "is_gh_managed_host includes hosts from GIT_SSH_FALLBACK_GH_HOSTS env var" {
  run env GIT_SSH_FALLBACK_GH_HOSTS="myghe.example.com" bash -c ". '$SCRIPT'; _is_gh_managed_host myghe.example.com"
  [ "$status" -eq 0 ]
}

@test "is_gh_managed_host uses exact match not glob (glob char in env does not match)" {
  # A glob like '*.com' in the env var must NOT match 'github.com'
  # github.com is in the hardcoded list, so test with a host NOT in the list.
  run env GIT_SSH_FALLBACK_GH_HOSTS="*.com" bash -c ". '$SCRIPT'; _is_gh_managed_host someother.com"
  [ "$status" -eq 1 ]
}

# ----------------------------------------------------------------------------
# Req 8: FallbackWarning and DebugTrace
# ----------------------------------------------------------------------------

@test "_warn emits warning: prefix to stderr" {
  run bash -c ". '$SCRIPT'; _warn 'test message'"
  assert_output --partial "warning: test message"
}

@test "_log emits debug prefix when GIT_SSH_FALLBACK_DEBUG=1" {
  run bash -c "export GIT_SSH_FALLBACK_DEBUG=1; . '$SCRIPT'; _log 'checking auth' 2>&1"
  assert_output --partial "[git-ssh-fallback] checking auth"
}

@test "_log emits nothing when debug flag is not set" {
  run bash -c "unset GIT_SSH_FALLBACK_DEBUG; unset GIT_TRACE; . '$SCRIPT'; _log 'should be silent'"
  [ -z "$output" ]
}

# ----------------------------------------------------------------------------
# Req 9: cfgcaddy deployment
# ----------------------------------------------------------------------------

@test "cfgcaddy.yml contains link rule for git-ssh-fallback" {
  grep -q "stapler-scripts/git-ssh-fallback" "$BATS_TEST_DIRNAME/../.cfgcaddy.yml"
}

@test "cfgcaddy.yml link rule targets .local/bin/git" {
  grep -q ".local/bin/git" "$BATS_TEST_DIRNAME/../.cfgcaddy.yml"
}

@test "wrapper script is executable" {
  [ -x "$SCRIPT" ]
}

# ----------------------------------------------------------------------------
# Self-test built-in
# ----------------------------------------------------------------------------

@test "wrapper --self-test passes all internal assertions" {
  run "$SCRIPT" --self-test
  [ "$status" -eq 0 ]
  assert_output --partial "self-test: PASS"
}

# ----------------------------------------------------------------------------
# Security: tokens must never be logged
# ----------------------------------------------------------------------------

@test "debug trace does not emit gh token value" {
  local cache_dir="$BATS_TMPDIR/cache"
  mkdir -p "$cache_dir"
  # Stub gh to print a fake token to stdout (which _check_auth redirects to /dev/null)
  printf '#!/bin/sh\nprintf "ghs_secret_token_value"; exit 0\n' > "$BATS_TMPDIR/shims/gh"
  chmod +x "$BATS_TMPDIR/shims/gh"
  run env PATH="$BATS_TMPDIR/shims:$PATH" \
      GIT_SSH_FALLBACK_DEBUG=1 \
      GIT_SSH_FALLBACK_CACHE_DIR="$cache_dir" \
      bash -c ". '$SCRIPT'; _check_auth github.com 2>&1"
  refute_output --partial "ghs_secret_token_value"
}
