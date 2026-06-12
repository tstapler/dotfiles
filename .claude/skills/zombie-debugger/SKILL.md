---
description: Diagnosing and resolving zombie process accumulation; measuring leak rate; identifying cmd.Start() without Wait; killing residual zombies; validating a zombie fix
---

# Zombie Process Debugger

Diagnose and resolve zombie process accumulation for any parent process on macOS/Linux.

## What are zombies?

A zombie (Z state) is a process that has exited but whose parent has not called `wait4()` to reap it. Zombies consume a PID slot but no memory/CPU. The danger is PID exhaustion: macOS `kern.maxprocperuid` is typically 10,666 — hitting it prevents any new process creation.

## Quick Reference Scripts

### Snapshot: count zombies by parent

```bash
# Show all zombie-creating parents (sorted by count)
ps ax -o pid,ppid,stat,comm | awk '$3~/Z/ {print $2}' | sort | uniq -c | sort -rn | head -20

# Show zombie children of a specific PID
PARENT_PID=71576
ps ax -o pid,ppid,stat,comm | awk -v ppid=$PARENT_PID '$2==ppid && $3~/Z/ {print}'

# Total zombie count for a specific process
ps ax -o pid,ppid,stat | awk -v ppid=$PARENT_PID '$2==ppid && $3~/Z/' | wc -l
```

### Rate monitoring: is it growing?

```bash
# Sample every 15s for 90s — confirms leak rate
PARENT_PID=71576
for i in 0 15 30 45 60 75 90; do
  sleep $([[ $i -eq 0 ]] && echo 0 || echo 15)
  COUNT=$(ps ax -o pid,ppid,stat | awk -v ppid=$PARENT_PID '$2==ppid && $3~/Z/' | wc -l | tr -d ' ')
  echo "T=${i}s: ${COUNT} zombies"
done
```

Interpret results:
- Count constant → leak has stopped (residual only)
- Count growing by N every interval → rate is N per interval
- Count spikes then levels off → bursty creation (scan loop, startup)

### PID range analysis: when were zombies created?

```bash
# Min and max zombie PID (vs parent PID) shows creation timeline
PARENT_PID=71576
ps ax -o pid,ppid,stat | awk -v ppid=$PARENT_PID '$2==ppid && $3~/Z/ {print $1}' | sort -n | awk 'NR==1{min=$1} {max=$1} END{print "min:", min, "max:", max, "count:", NR}'
echo "Parent PID: $PARENT_PID (started around this PID)"
```

PIDs close to parent PID → zombies from early in process lifetime (startup burst).  
PIDs much higher than parent → ongoing leak.

### System-wide fork pressure

```bash
# Current process count vs limit
echo "Processes: $(ps ax | wc -l) / $(sysctl -n kern.maxprocperuid) ($(( $(ps ax | wc -l) * 100 / $(sysctl -n kern.maxprocperuid) ))%)"

# All zombie parents (system-wide)
ps ax -o pid,ppid,stat,comm | awk '$3~/Z/ {print $2}' | sort -u | while read ppid; do
  count=$(ps ax -o ppid,stat | awk -v ppid=$ppid '$1==ppid && $2~/Z/' | wc -l | tr -d ' ')
  comm=$(ps -p $ppid -o comm= 2>/dev/null || echo "gone")
  echo "$count zombies under PID $ppid ($comm)"
done | sort -rn
```

### Find the zombie-creating code (Go-specific)

```bash
# Find cmd.Start() without a nearby cmd.Wait() — likely zombie sources
grep -rn "\.Start()" <REPO> --include="*.go" | grep -v "_test.go" | grep -v "worktrees" 

# Confirm TimeoutExecutor has WaitDelay
grep -A5 "func.*Output\|func.*Run\|func.*CombinedOutput" executor/timeout_executor.go | grep -E "WaitDelay|func"
```

Zombie creation patterns in Go:
1. `cmd.Start()` called, `cmd.Wait()` never called (or only called on happy path)
2. `cmd.Start()` for a long-running process that exits unexpectedly — fallback path skips Wait
3. Using plain `Exec{}` executor instead of `TimeoutExecutor` (no WaitDelay → Wait blocks on grandchild pipes)

### Kill existing zombies (immediate options)

Option A — Restart the parent process (safest, clears all):
```bash
# macOS launchd service
launchctl kickstart -k gui/$(id -u)/<service-label>

# Generic: kill and let supervisor restart
kill -TERM <PARENT_PID>
```
When the parent exits, all zombie children are reparented to launchd (PID 1) which immediately reaps them.

Option B — Send SIGCHLD to trigger Wait (rarely works in Go):
```bash
kill -CHLD <PARENT_PID>
```
Go's runtime installs a SIGCHLD handler that reaps children created via `os/exec`. However, this only works for cmd objects whose `Wait()` was called (they were already reaped). Stuck zombies from `cmd.Start()` without `Wait()` won't be affected.

Option C — Wait for launchd auto-restart (if process is crashing):
If the parent is crashing due to fork exhaustion, launchd will restart it. Zombies are then automatically cleared on restart.

### Verify fix effectiveness

```bash
# After deploying fix: confirm rate drops to 0 over 3 scan intervals
# (Use the rate monitoring script above with 90s duration)
# Goal: count constant across all measurements
```

## Root Cause Patterns

### Pattern 1: Runaway polling loop (most common)
**Symptom**: Zombies accumulate continuously at high rate (hundreds/minute).  
**Cause**: A `cmd.Run()`/`cmd.Output()` call inside a tight polling loop with no timeout. The command hangs (waiting on a stuck subprocess or grandchild holding a pipe). The loop fires again, creating another process. Repeat.  
**Fix**: `exec.CommandContext` with `context.WithTimeout` + `cmd.WaitDelay = 2*time.Second`.

### Pattern 2: Startup burst then stable
**Symptom**: N zombies appear quickly after restart, then count freezes.  
**Cause**: Initial scan/polling burst creates zombies during startup before timeouts kick in, OR a one-time code path (first connection, first scan) has a missing timeout.  
**Fix**: Verify that scan/initialization code paths use TimeoutExecutor, then restart service to clear residual.

### Pattern 3: Long-running process not reaped on unexpected exit
**Symptom**: Small, slow leak correlated with external events (session disconnects, tmux session ends).  
**Cause**: `cmd.Start()` for a long-running subprocess (control mode, monitoring process). When it exits naturally, the goroutine reading its output returns, but `cmd.Wait()` is never called.  
**Fix**: Add `defer cmd.Wait()` (or call Wait in the EOF/exit path) in the goroutine that reads the process output.

### Pattern 4: Grandchild pipe hold (WaitDelay missing)
**Symptom**: Zombie count doesn't grow, but `cmd.Wait()` blocks indefinitely, starving goroutines.  
**Cause**: Parent process killed by timeout, but a grandchild (e.g. git credential helper) still holds the pipe open. `Wait()` waits for pipe EOF forever.  
**Fix**: `cmd.WaitDelay = 2*time.Second` forces Wait to return and close pipes after 2s.

## Go Fix Template

```go
// Short command (git, tmux, etc.)
ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()
cmd := exec.CommandContext(ctx, "git", args...)
cmd.WaitDelay = 2 * time.Second
out, err := cmd.Output()  // or .Run() / .CombinedOutput() — all call Wait() internally

// Long-running process started with cmd.Start()
cmd := exec.CommandContext(s.ctx, "tmux", "-C", "attach-session", "-t", name)
if err := cmd.Start(); err != nil { ... }
go func() {
    // Read output until EOF
    scanner := bufio.NewScanner(stdout)
    for scanner.Scan() { ... }
    // CRITICAL: always reap on exit
    _ = cmd.Wait()
}()
```

## Checklist: validating a zombie fix

- [ ] Rate monitoring shows 0 new zombies over 90s
- [ ] All `exec.Command` calls converted to `exec.CommandContext` (forbidigo lint passes)
- [ ] All `cmd.Start()` calls have a corresponding `cmd.Wait()` on ALL exit paths (not just happy path)
- [ ] TimeoutExecutor (or equivalent) used for polling loops — has both `context.WithTimeout` AND `WaitDelay`
- [ ] Service restarted to clear residual zombies from before fix
- [ ] Post-restart: re-run rate monitoring to confirm clean slate

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `lean-agent-loop` | Run repeated rate-monitoring iterations with minimal-context agents to confirm fix convergence |
