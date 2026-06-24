# Validation Plan: git-ssh-fallback

Date: 2026-06-24

## Happy Path Scenario

Given `gh` is not authenticated for `github.com` and a live SSH agent is present (baseline: HTTPS operations fail silently with the `gh auth git-credential` helper), when the user runs `git fetch origin` in a GitHub repo with an HTTPS remote, then the wrapper transparently rewrites the URL to SSH, emits `warning: falling back to SSH (gh not authenticated for github.com)` on stderr, and the fetch succeeds without any manual intervention.

---

## Test Stack

- Unit: bats-core (`bats stapler-scripts/git-ssh-fallback.bats`)
- Integration: bats-core with real subprocesses (invoking wrapper binary directly, stubbing `gh` and `ssh-add` via PATH-prepend shims)
- E2E / UX: N/A — pure CLI wrapper, no interactive UI

---

## Requirement → Test Mapping

### Req 1: RealGit Resolution and RecursionGuard Passthrough

**Unit — happy path**
```
@test "find_real_git_should_return_real_binary_when_wrapper_is_on_path" {
  # Place a fake 'git' wrapper earlier in PATH
  # Assert _find_real_git returns a path that is not $0
  run _find_real_git
  [ "$status" -eq 0 ]
  [ "$output" != "$BATS_TEST_DIRNAME/git" ]
  [[ "$output" == */git ]]
}
```

**Unit — error path**
```
@test "recursion_guard_should_exec_real_git_immediately_when_active_flag_set" {
  # GIT_SSH_FALLBACK_ACTIVE=1 must skip all wrapper logic
  export GIT_SSH_FALLBACK_ACTIVE=1
  run bash stapler-scripts/git-ssh-fallback --version
  [ "$status" -eq 0 ]
  # No [git-ssh-fallback] prefix in output (wrapper logic bypassed)
  refute_output --partial "[git-ssh-fallback]"
}
```

**Integration**
```
@test "wrapper_should_not_recurse_when_deployed_as_git_on_path" {
  # Symlink wrapper as git in a temp bin dir, prepend to PATH
  # Verify git --version returns real git version, no infinite loop
  local tmpbin; tmpbin=$(mktemp -d)
  ln -s "$PWD/stapler-scripts/git-ssh-fallback" "$tmpbin/git"
  PATH="$tmpbin:$PATH" run git --version
  [ "$status" -eq 0 ]
  [[ "$output" == git\ version\ * ]]
}
```

---

### Req 2: NetworkSubcommand Detection (local vs. network ops)

**Unit — happy path**
```
@test "is_network_op_should_return_true_for_fetch" {
  run _is_network_op "fetch"
  [ "$status" -eq 0 ]
}

@test "extract_subcommand_should_skip_git_flags_before_subcommand" {
  # git -C /some/path fetch → subcommand is fetch
  run _extract_subcommand "-C" "/some/path" "fetch" "origin"
  [ "$output" = "fetch" ]
}
```

**Unit — error path**
```
@test "is_network_op_should_return_false_for_status" {
  run _is_network_op "status"
  [ "$status" -eq 1 ]
}

@test "is_network_op_should_return_false_for_log" {
  run _is_network_op "log"
  [ "$status" -eq 1 ]
}
```

**Integration**
```
@test "wrapper_should_exec_real_git_without_gh_for_local_subcommands" {
  # No gh shim in PATH; wrapper must complete git status without error
  run stapler-scripts/git-ssh-fallback status
  # gh absence must not cause exit failure for local ops
  [ "$status" -eq 0 ] || [ "$status" -eq 128 ]  # 128 = not a git repo, still no wrapper error
  refute_output --partial "[git-ssh-fallback] checking auth"
}
```

---

### Req 3: RemoteHost Extraction (clone args and remote config)

**Unit — happy path**
```
@test "extract_host_should_return_hostname_from_https_clone_url" {
  run _extract_host "clone" "https://github.com/owner/repo.git"
  [ "$output" = "github.com" ]
}

@test "extract_host_should_strip_embedded_credentials_from_url" {
  run _extract_host "clone" "https://user:token@github.com/org/repo"
  [ "$output" = "github.com" ]
}

@test "extract_host_should_return_host_from_remote_config_for_fetch" {
  # Stub: REAL_GIT shim that returns 'https://gitlab.com/org/proj' for remote get-url
  run _extract_host "fetch" "origin"
  [ "$output" = "gitlab.com" ]
}
```

**Unit — error path**
```
@test "extract_host_should_return_empty_for_ssh_clone_url" {
  # Already SSH — no fallback needed
  run _extract_host "clone" "git@github.com:owner/repo.git"
  [ -z "$output" ]
}

@test "extract_host_should_return_empty_when_remote_get_url_fails" {
  # Outside a git repo: remote get-url exits non-zero
  run _extract_host "fetch" "origin"
  [ -z "$output" ]
}
```

**Integration**
```
@test "wrapper_should_skip_auth_check_when_remote_is_already_ssh" {
  # Stub git remote get-url to return git@github.com:owner/repo
  # Wrapper must exec real git without spawning gh
  run env GIT_SSH_FALLBACK_DEBUG=1 stapler-scripts/git-ssh-fallback fetch origin
  refute_output --partial "checking auth"
}
```

---

### Req 4: GhAuthResult Check with AuthCache (5-min TTL, timeout 1s)

**Unit — happy path**
```
@test "check_auth_should_return_authenticated_when_cache_file_is_fresh" {
  local cache_dir; cache_dir=$(mktemp -d)
  local cache_file="$cache_dir/github.com.auth"
  touch "$cache_file"  # mtime = now (< 5 min)
  GIT_SSH_FALLBACK_CACHE_DIR="$cache_dir" run _check_auth "github.com"
  [ "$output" = "authenticated" ]
}

@test "check_auth_should_write_cache_and_return_authenticated_on_gh_exit_0" {
  local cache_dir; cache_dir=$(mktemp -d)
  # Stub gh to exit 0
  PATH="$BATS_TEST_TMPDIR/shims:$PATH"
  printf '#!/bin/sh\nexit 0\n' > "$BATS_TEST_TMPDIR/shims/gh"
  chmod +x "$BATS_TEST_TMPDIR/shims/gh"
  GIT_SSH_FALLBACK_CACHE_DIR="$cache_dir" run _check_auth "github.com"
  [ "$output" = "authenticated" ]
  [ -f "$cache_dir/github.com.auth" ]
}
```

**Unit — error path**
```
@test "check_auth_should_return_unauthenticated_when_gh_not_in_path" {
  PATH="/usr/bin:/bin" run _check_auth "github.com"
  [ "$output" = "unauthenticated" ]
}

@test "check_auth_should_return_unauthenticated_and_not_write_cache_on_gh_failure" {
  local cache_dir; cache_dir=$(mktemp -d)
  # Stub gh to exit 1 (not authenticated)
  printf '#!/bin/sh\nexit 1\n' > "$BATS_TEST_TMPDIR/shims/gh"
  chmod +x "$BATS_TEST_TMPDIR/shims/gh"
  PATH="$BATS_TEST_TMPDIR/shims:$PATH"
  GIT_SSH_FALLBACK_CACHE_DIR="$cache_dir" run _check_auth "github.com"
  [ "$output" = "unauthenticated" ]
  [ ! -f "$cache_dir/github.com.auth" ]
}

@test "check_auth_should_return_unauthenticated_when_gh_times_out" {
  # Stub gh that sleeps 2s; timeout 1 must kill it (exit 124)
  printf '#!/bin/sh\nsleep 2\n' > "$BATS_TEST_TMPDIR/shims/gh"
  chmod +x "$BATS_TEST_TMPDIR/shims/gh"
  PATH="$BATS_TEST_TMPDIR/shims:$PATH"
  run _check_auth "github.com"
  [ "$output" = "unauthenticated" ]
}

@test "check_auth_should_return_authenticated_from_stale_cache_after_5_min" {
  # Cache file older than 5 minutes must NOT be treated as a hit
  local cache_dir; cache_dir=$(mktemp -d)
  local cache_file="$cache_dir/github.com.auth"
  touch -t "$(date -v -10M +%Y%m%d%H%M)" "$cache_file" 2>/dev/null || \
    touch --date="10 minutes ago" "$cache_file"
  # Stub gh to exit 0 so we can see if it gets called
  printf '#!/bin/sh\necho "gh_called"; exit 0\n' > "$BATS_TEST_TMPDIR/shims/gh"
  chmod +x "$BATS_TEST_TMPDIR/shims/gh"
  PATH="$BATS_TEST_TMPDIR/shims:$PATH"
  GIT_SSH_FALLBACK_CACHE_DIR="$cache_dir" run _check_auth "github.com"
  assert_output --partial "gh_called"
}
```

**Integration**
```
@test "wrapper_should_not_spawn_gh_on_second_invocation_within_cache_ttl" {
  local cache_dir; cache_dir=$(mktemp -d)
  local call_count_file; call_count_file=$(mktemp)
  # Stub gh that increments a counter
  printf '#!/bin/sh\necho 1 >> %s; exit 0\n' "$call_count_file" > "$BATS_TEST_TMPDIR/shims/gh"
  chmod +x "$BATS_TEST_TMPDIR/shims/gh"
  PATH="$BATS_TEST_TMPDIR/shims:$PATH" GIT_SSH_FALLBACK_CACHE_DIR="$cache_dir" \
    stapler-scripts/git-ssh-fallback --self-test
  PATH="$BATS_TEST_TMPDIR/shims:$PATH" GIT_SSH_FALLBACK_CACHE_DIR="$cache_dir" \
    stapler-scripts/git-ssh-fallback --self-test
  local call_count; call_count=$(wc -l < "$call_count_file")
  # gh must only have been called once (cache hit on second invocation)
  [ "$call_count" -le 1 ]
}
```

---

### Req 5: SshAgent Detection with Liveness Check (ssh-add -l)

**Unit — happy path**
```
@test "detect_ssh_agent_should_succeed_when_ssh_auth_sock_is_live" {
  # Create a real Unix socket to simulate a live agent
  local sock; sock=$(mktemp -u)
  socat UNIX-LISTEN:"$sock",fork /dev/null &
  local socat_pid=$!
  export SSH_AUTH_SOCK="$sock"
  # Stub ssh-add -l to exit 1 (no keys = alive)
  printf '#!/bin/sh\nexit 1\n' > "$BATS_TEST_TMPDIR/shims/ssh-add"
  chmod +x "$BATS_TEST_TMPDIR/shims/ssh-add"
  PATH="$BATS_TEST_TMPDIR/shims:$PATH" run _detect_ssh_agent
  kill "$socat_pid" 2>/dev/null
  [ "$status" -eq 0 ]
}

@test "detect_ssh_agent_should_find_1password_socket_when_ssh_auth_sock_unset" {
  unset SSH_AUTH_SOCK
  local fake_sock; fake_sock=$(mktemp -u)
  socat UNIX-LISTEN:"$fake_sock",fork /dev/null &
  local socat_pid=$!
  # Stub the 1password socket path via env override for test
  _OP_AGENT_SOCK="$fake_sock"
  printf '#!/bin/sh\nexit 0\n' > "$BATS_TEST_TMPDIR/shims/ssh-add"
  chmod +x "$BATS_TEST_TMPDIR/shims/ssh-add"
  PATH="$BATS_TEST_TMPDIR/shims:$PATH" run _detect_ssh_agent
  kill "$socat_pid" 2>/dev/null
  [ "$status" -eq 0 ]
}
```

**Unit — error path**
```
@test "detect_ssh_agent_should_return_failure_when_no_socket_found" {
  unset SSH_AUTH_SOCK
  # Ensure no real agent sockets exist on probe paths (test isolation)
  _OP_AGENT_SOCK="/nonexistent/socket"
  run _detect_ssh_agent
  [ "$status" -eq 1 ]
}

@test "detect_ssh_agent_should_skip_stale_socket_where_ssh_add_exits_2" {
  # ssh-add exit code 2 = cannot connect to agent = stale socket
  local sock; sock=$(mktemp -u)
  touch "$sock"  # file exists but not a socket — simulate stale path
  export SSH_AUTH_SOCK="$sock"
  printf '#!/bin/sh\nexit 2\n' > "$BATS_TEST_TMPDIR/shims/ssh-add"
  chmod +x "$BATS_TEST_TMPDIR/shims/ssh-add"
  PATH="$BATS_TEST_TMPDIR/shims:$PATH" run _detect_ssh_agent
  # Must not succeed on a stale socket
  [ "$status" -eq 1 ]
}
```

**Integration**
```
@test "wrapper_should_emit_error_and_exec_real_git_when_no_ssh_agent_on_fallback_path" {
  # gh exits 1 (unauthenticated); SSH_AUTH_SOCK unset
  unset SSH_AUTH_SOCK
  printf '#!/bin/sh\nexit 1\n' > "$BATS_TEST_TMPDIR/shims/gh"
  chmod +x "$BATS_TEST_TMPDIR/shims/gh"
  run env PATH="$BATS_TEST_TMPDIR/shims:$PATH" \
    stapler-scripts/git-ssh-fallback clone https://github.com/owner/repo
  assert_output --partial "no SSH agent found"
}
```

---

### Req 6: ConfigInjection Construction for gh-Managed Hosts

**Unit — happy path**
```
@test "inject_ssh_config_should_set_git_config_env_vars_for_host" {
  _inject_ssh_config "github.com"
  [ "$GIT_CONFIG_COUNT" = "1" ]
  [ "$GIT_CONFIG_KEY_0" = "url.git@github.com:.insteadOf" ]
  [ "$GIT_CONFIG_VALUE_0" = "https://github.com/" ]
}

@test "inject_ssh_config_should_set_correct_vars_for_gitlab_host" {
  _inject_ssh_config "gitlab.com"
  [ "$GIT_CONFIG_KEY_0" = "url.git@gitlab.com:.insteadOf" ]
  [ "$GIT_CONFIG_VALUE_0" = "https://gitlab.com/" ]
}
```

**Unit — error path**
```
@test "inject_ssh_config_should_strip_credentials_from_insteadof_prefix" {
  # If host was extracted from url with embedded creds, injection must use bare host
  _inject_ssh_config "github.com"  # host already stripped by _extract_host
  [ "$GIT_CONFIG_VALUE_0" = "https://github.com/" ]
  # Must not contain '@' or ':'  in the value
  [[ "$GIT_CONFIG_VALUE_0" != *"@"* ]]
}

@test "inject_ssh_config_should_export_git_ssh_command_in_batchmode" {
  _inject_ssh_config "github.com"
  [[ "$GIT_SSH_COMMAND" == *"BatchMode=yes"* ]]
}
```

**Integration**
```
@test "wrapper_should_pass_config_injection_env_vars_to_real_git_on_fallback" {
  # Stub gh to return unauthenticated; stub ssh-add to return alive
  # Spy: capture env of exec'd real git via a shim that dumps env
  printf '#!/bin/sh\nenv | grep GIT_CONFIG\n' > "$BATS_TEST_TMPDIR/shims/git-spy"
  # ... wire up shims and invoke wrapper
  run env PATH="$BATS_TEST_TMPDIR/shims:$PATH" \
    GIT_SSH_FALLBACK_DEBUG=1 stapler-scripts/git-ssh-fallback fetch origin
  assert_output --partial "GIT_CONFIG_COUNT=1"
  assert_output --partial "GIT_CONFIG_KEY_0=url.git@github.com:.insteadOf"
}
```

---

### Req 7: Non-gh-Managed Host Proactive SSH Path

**Unit — happy path**
```
@test "is_gh_managed_host_should_return_true_for_github_com" {
  run _is_gh_managed_host "github.com"
  [ "$status" -eq 0 ]
}

@test "is_gh_managed_host_should_return_false_for_internal_host" {
  run _is_gh_managed_host "git.internal.example.com"
  [ "$status" -eq 1 ]
}

@test "is_gh_managed_host_should_include_user_extensible_env_var_hosts" {
  GIT_SSH_FALLBACK_GH_HOSTS="myghe.example.com" run _is_gh_managed_host "myghe.example.com"
  [ "$status" -eq 0 ]
}
```

**Unit — error path**
```
@test "non_gh_host_should_skip_to_real_git_without_modification_when_no_ssh_agent" {
  unset SSH_AUTH_SOCK
  # For a non-gh host with no SSH agent, wrapper must not emit warning or inject config
  run _handle_non_gh_host "git.internal.example.com"
  refute_output --partial "warning:"
  refute_output --partial "GIT_CONFIG"
}
```

**Integration**
```
@test "wrapper_should_proactively_use_ssh_for_non_gh_host_with_live_agent" {
  # Stub ssh-add alive; confirm ConfigInjection is applied without gh call
  printf '#!/bin/sh\necho "gh_called"; exit 0\n' > "$BATS_TEST_TMPDIR/shims/gh"
  chmod +x "$BATS_TEST_TMPDIR/shims/gh"
  # Arrange live SSH_AUTH_SOCK via socat shim
  run env GIT_SSH_FALLBACK_DEBUG=1 PATH="$BATS_TEST_TMPDIR/shims:$PATH" \
    stapler-scripts/git-ssh-fallback clone https://git.internal.example.com/org/repo
  refute_output --partial "gh_called"
  assert_output --partial "non-gh host"
  assert_output --partial "warning: falling back to SSH"
}
```

---

### Req 8: FallbackWarning Emission and DebugTrace

**Unit — happy path**
```
@test "warn_should_emit_warning_prefix_to_stderr" {
  run bash -c 'source stapler-scripts/git-ssh-fallback; _warn "test message"'
  assert_output --partial "warning: test message"
}

@test "log_should_emit_debug_prefix_when_debug_flag_set" {
  GIT_SSH_FALLBACK_DEBUG=1 run bash -c \
    'source stapler-scripts/git-ssh-fallback; _log "checking auth"'
  assert_output --partial "[git-ssh-fallback] checking auth"
}
```

**Unit — error path**
```
@test "log_should_emit_nothing_when_debug_flag_not_set" {
  unset GIT_SSH_FALLBACK_DEBUG GIT_TRACE
  run bash -c 'source stapler-scripts/git-ssh-fallback; _log "should be silent"'
  [ -z "$output" ]
}
```

**Integration**
```
@test "wrapper_should_emit_fallback_warning_on_stderr_when_gh_unauthenticated" {
  # Stub gh: exit 1; stub ssh-add: alive
  run env GIT_SSH_FALLBACK_DEBUG=0 PATH="$BATS_TEST_TMPDIR/shims:$PATH" \
    stapler-scripts/git-ssh-fallback fetch origin 2>&1
  assert_output --partial "warning: falling back to SSH (gh not authenticated for github.com)"
}

@test "wrapper_should_emit_all_debug_trace_lines_in_debug_mode" {
  run env GIT_SSH_FALLBACK_DEBUG=1 PATH="$BATS_TEST_TMPDIR/shims:$PATH" \
    stapler-scripts/git-ssh-fallback fetch origin 2>&1
  assert_output --partial "[git-ssh-fallback]"
  assert_output --partial "rewriting https://github.com/"
}
```

---

### Req 9: cfgcaddy Deployment (PATH Position)

**Unit — happy path**
```
@test "cfgcaddy_yml_should_contain_link_rule_for_git_wrapper" {
  grep -q "stapler-scripts/git-ssh-fallback" .cfgcaddy.yml
  grep -q ".local/bin/git" .cfgcaddy.yml
}
```

**Unit — error path**
```
@test "wrapper_script_should_be_executable" {
  [ -x stapler-scripts/git-ssh-fallback ]
}
```

**Integration**
```
@test "wrapper_should_shadow_usr_bin_git_when_deployed_to_local_bin" {
  local tmpbin; tmpbin=$(mktemp -d)
  ln -s "$PWD/stapler-scripts/git-ssh-fallback" "$tmpbin/git"
  which_result=$(PATH="$tmpbin:/usr/bin:/bin" which git)
  [ "$which_result" = "$tmpbin/git" ]
}

@test "wrapper_deployed_via_symlink_should_still_resolve_real_git_without_recursion" {
  local tmpbin; tmpbin=$(mktemp -d)
  ln -s "$PWD/stapler-scripts/git-ssh-fallback" "$tmpbin/git"
  run env PATH="$tmpbin:/usr/bin:/bin" git --version
  [ "$status" -eq 0 ]
  [[ "$output" == git\ version\ * ]]
}
```

---

## Self-Test Coverage

The wrapper includes a `--self-test` flag that provides built-in smoke testing:

```
@test "wrapper_self_test_should_pass_all_internal_assertions" {
  run stapler-scripts/git-ssh-fallback --self-test
  [ "$status" -eq 0 ]
  assert_output --partial "self-test: PASS"
}
```

---

## Coverage Targets and How to Measure

| Layer | Command | Coverage Target |
|-------|---------|-----------------|
| Unit (bats) | `bats stapler-scripts/git-ssh-fallback.bats` | All 9 requirements, 1 happy + 1 error path each = 18 unit tests |
| Integration (bats) | `bats stapler-scripts/git-ssh-fallback.integration.bats` | 9 integration tests covering data flow across component boundaries |
| Self-test (built-in) | `stapler-scripts/git-ssh-fallback --self-test` | 3 assertions (RealGit, subcommand extraction, local op classification) |

---

## Test Infrastructure: Shim Pattern

All tests that involve `gh`, `ssh-add`, or the real `git` binary use the same shim pattern:

```sh
setup() {
  BATS_TEST_TMPDIR=$(mktemp -d)
  mkdir -p "$BATS_TEST_TMPDIR/shims"
}

teardown() {
  rm -rf "$BATS_TEST_TMPDIR"
}

# Usage in test: PATH="$BATS_TEST_TMPDIR/shims:$PATH"
```

This avoids mocking frameworks and keeps tests POSIX-compatible. Each shim is a script that exits with the desired code or echoes a marker string.

---

## Security Constraint Verification

One test must explicitly verify that tokens are never logged:

```
@test "debug_trace_should_not_emit_gh_token_value_in_output" {
  # Even in debug mode, the raw token from 'gh auth token' must never appear
  printf '#!/bin/sh\necho "ghs_secret_token_value"\n' > "$BATS_TEST_TMPDIR/shims/gh"
  chmod +x "$BATS_TEST_TMPDIR/shims/gh"
  run env GIT_SSH_FALLBACK_DEBUG=1 PATH="$BATS_TEST_TMPDIR/shims:$PATH" \
    stapler-scripts/git-ssh-fallback fetch origin 2>&1
  refute_output --partial "ghs_secret_token_value"
}
```

---

## Summary: Test Case Counts

| Type | Count | Notes |
|------|-------|-------|
| Unit — happy path | 18 | 2 per requirement (some requirements yield 3) |
| Unit — error path | 13 | Edge cases: stale cache, missing gh, stale socket, non-gh host without agent, debug suppression |
| Integration | 10 | Invoke wrapper binary directly with shim PATH |
| Self-test (built-in) | 1 bats test (3 internal assertions) | Verifies `--self-test` flag works |
| Security constraint | 1 | Token never logged |
| **Total** | **43** | |

**Requirements coverage: 9/9 (100%)**

Every requirement in the plan has at least one unit happy path, one unit error path, and one integration test. The cfgcaddy deployment requirement (Req 9) is verified via filesystem assertions rather than process invocation, which is appropriate for a symlink/PATH test.
