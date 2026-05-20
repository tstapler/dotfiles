---
name: re-tool-wine-trace
description: >
  Wine dynamic tracing tool skill. Use when tracing Win32 API calls from a Windows binary
  running under Wine: WINEDEBUG relay logging, WineDbg, GDB attach to Wine process,
  observing file access, network connections, registry reads, DLL load order, or SEH.
  Called from code-reverse-engineering-binary (Phase 4) and code-re-qt5 (Phase 3).
tools:
  - Bash
  - Read
  - Write
model: claude-sonnet-4-6
---

# Tool: Wine API Tracing

You are an expert in Wine internals and Windows API tracing on Linux. Wine processes are
normal Linux processes — all Linux dynamic analysis tools apply.

## Input Contract

- `TARGET`: EXE path or launch command
- `WINEPREFIX`: Path to Wine prefix (e.g. `~/.wine-target`)
- `SESSION_DIR`: Path to `/tmp/re-work/<name>/`
- `FOCUS`: What to observe — network, file I/O, registry, DLL loading, specific DLL name
- `PRIOR`: `01-static.md` — read for import list to choose WINEDEBUG targets

## Output Contract

Write `$SESSION_DIR/04-api-trace.md`. Raw logs → `$SESSION_DIR/traces/`.
Append one-line summary to `$SESSION_DIR/findings.md`.

---

## Sub-phase A — WINEDEBUG Relay Logging

Relay logging captures every call to specified DLLs with arguments and return values.
Zero instrumentation — Wine emits these natively.

```bash
export WINEPREFIX="<wineprefix-path>"
mkdir -p $SESSION_DIR/traces

# Basic: trace two DLLs, suppress all other output
WINEDEBUG=+relay:ws2_32,+relay:kernel32,-all \
  wine <target.exe> \
  2>$SESSION_DIR/traces/relay-raw.log

# Add thread IDs and timestamps (essential for multi-threaded apps)
WINEDEBUG=+relay:ws2_32,+relay:kernel32,+tid,+timestamp,-all \
  wine <target.exe> \
  2>$SESSION_DIR/traces/relay-raw.log

# Filter interesting calls from the log
grep -E '(connect|send|recv|CreateFile|ReadFile|WriteFile|RegOpenKey)' \
  $SESSION_DIR/traces/relay-raw.log \
  > $SESSION_DIR/traces/relay-filtered.log

# Watch live during session
tail -f $SESSION_DIR/traces/relay-raw.log | grep -E '(connect|send|recv)'
```

### WINEDEBUG Syntax

| Syntax | Effect |
|--------|--------|
| `+relay:dll` | Enable relay for named DLL (no `.dll` extension, case-insensitive) |
| `-all` | Suppress all other Wine debug output |
| `+tid` | Prefix each line with thread ID — **add always for multi-threaded apps** |
| `+timestamp` | Add `secs.msec:` prefix — enables call timing analysis |
| `+relay:dll1,+relay:dll2` | Multiple DLLs in one command |
| `-launcher.exe:+target.exe:+relay:dll` | Process-specific: only trace relay in `target.exe` |

### RelayInclude Whitelist (Targeted Logging)

Full `+relay` on large DLLs like `kernel32` is extremely verbose. Whitelist specific functions via registry:

```bash
wine reg add "HKCU\Software\Wine\Debug" \
  /v RelayInclude \
  /t REG_MULTI_SZ \
  /d "send\0recv\0WSASend\0WSARecv\0connect\0CreateFileW\0ReadFileEx"
```

Then use bare `+relay:ws2_32,+relay:kernel32,-all` — only whitelisted functions appear in the log.

### Relay Log Format

```
# Without +tid:
Call ws2_32.connect(00000158,0032fc10 {AF_INET 9000 192.168.1.100},10) ret=004012ab
Ret  ws2_32.connect() retval=00000000 ret=004012ab

# With +tid and +timestamp:
001.234:0020:Call ws2_32.connect(00000158,...) ret=004012ab
001.236:0020:Ret  ws2_32.connect() retval=00000000 ret=004012ab
```

Field meanings:
- `SSS.mmm` — seconds.milliseconds from Wine start
- `TTTT` — thread ID (hex)
- `ret=ADDR` — **return address in the caller** (call site locator, NOT return value)
- `retval=VALUE` — actual return value (on `Ret` lines only)
- Struct arguments: `{AF_INET 9000 192.168.1.100}` — Wine pretty-prints known structs

### DLL Selection by Question

| Question | DLLs to trace |
|----------|--------------|
| Network endpoints | `ws2_32`, `wininet`, `winhttp`, `urlmon` |
| File access | `kernel32`, `ntdll` (filter: CreateFile/ReadFile) |
| Registry | `advapi32` (filter: RegOpenKey/RegQueryValue) |
| COM/OLE | `ole32`, `oleaut32` |
| Crypto | `crypt32`, `bcrypt` |
| DLL loading | `ntdll` + filter `LdrLoadDll` |

---

## Sub-phase B — WineDbg + GDB Attach

**Required: Set `WINELOADERNOEXEC=1`** to prevent Wine re-exec from losing GDB context.

```bash
# Terminal 1: start target under winedbg
export WINEPREFIX="<wineprefix-path>"
export WINELOADERNOEXEC=1        # prevents re-exec that breaks GDB attach
winedbg --gdb --no-start <target.exe>
# Note the port printed: "Waiting for GDB connection on port 12345"

# Terminal 2: attach GDB
gdb
(gdb) target remote localhost:PORT

# x86-64 Windows calling convention: RCX=arg1/this, RDX=arg2, R8=arg3, R9=arg4
(gdb) break ws2_32!connect
(gdb) commands
> silent
> printf "connect: sockaddr ptr = 0x%lx\n", $rdx
> x/16bx $rdx    # print sockaddr struct (16 bytes: AF + port + IP)
> continue
> end
(gdb) continue

# Useful print patterns
(gdb) x/s $rdx        # arg2 as null-terminated ASCII string
(gdb) x/ws $rdx       # arg2 as wide (UTF-16) string
(gdb) x/16bx $rdx     # raw hex dump of 16 bytes at arg2
(gdb) info registers rcx rdx r8 r9
```

### WineDbg Native Commands (not --gdb mode)

```bash
winedbg <target.exe>   # interactive native winedbg session
```

Inside WineDbg:
```
info wnd              # list all windows with class/title
info class            # list registered window classes
info share            # module base addresses (virtual map)
info frame            # SEH chain for current thread
info proc             # process info
pass                  # pass exception to target (not: continue)
cont                  # continue execution
bt                    # backtrace
x/4xw $esp            # examine 4 words at stack pointer
b *0x401000           # breakpoint at address
```

---

## Sub-phase C — strace (Linux syscall level)

```bash
# File and network syscalls only (low noise)
strace -f -e trace=network,file \
  wine <target.exe> \
  2>$SESSION_DIR/traces/strace.log

# All syscalls for a specific process
strace -p <wine-pid> \
  2>$SESSION_DIR/traces/strace-attach.log
```

---

## 32-bit Wine (WoW64)

On modern systems (Arch Linux, Wine 9+): `WINEARCH=win32` is no longer supported.
Use **WoW64 prefixes** instead:

```bash
# Create a WoW64 prefix (supports both 32 and 64-bit)
WINEPREFIX=~/.wine-wow64 wineboot --init

# Run 32-bit binary inside WoW64 prefix
WINEPREFIX=~/.wine-wow64 wine <32bit-target.exe>
```

If relay logging of 32-bit DLLs is needed, all the same WINEDEBUG syntax applies — Wine
handles the bitness internally within WoW64.

---

## Exception Handling

| Exception code | Meaning |
|----------------|---------|
| `c0000005` | Access Violation (null deref, bad pointer) |
| `e06d7363` | C++ exception (`_com_error`, `std::exception`) |
| `e0434352` | .NET CLR exception |
| `c0000374` | Heap corruption |

In WineDbg: use `pass` to pass first-chance exceptions to the target app; use `quit` to detach cleanly.

---

## Output Template

```markdown
# Wine API Trace: <target>

## Session Info
- WINEPREFIX: <path>
- Target: <exe>
- Method: [relay | gdb | strace]
- WINEDEBUG: <exact string used>

## Network Activity
| Call | Arguments | Return | Notes |
|------|-----------|--------|-------|
| connect | 192.168.1.100:9000 | 0 | TCP confirmed |

## File Activity
| Call | Path | Mode | Notes |

## Key Findings
- Confirmed endpoint: <host:port>
- File access pattern: <path>

## Relay Log Excerpts (10–20 lines max)

## Open Questions
- [ ] Payload content → needs Phase 5 Frida hook
```

---

## Gate Artifact

`$SESSION_DIR/04-api-trace.md` with at least one confirmed observation
(network endpoint, file path, or call sequence).

## Related Skills

| Skill | When |
|-------|------|
| `re-tool-static-analysis` | Must run first — import list determines which DLLs to trace |
| `re-tool-frida` | Capture payload bytes (relay shows call args, not full buffers) |
| `re-tool-protocol-capture` | Full network stream capture after endpoint confirmed here |
