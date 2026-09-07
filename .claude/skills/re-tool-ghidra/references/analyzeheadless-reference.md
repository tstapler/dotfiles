# analyzeHeadless Reference

Binary: `$GHIDRA_HOME/support/analyzeHeadless`

```bash
# Import and analyze (run once — slow)
$GHIDRA_HOME/support/analyzeHeadless \
  /tmp/ghidra-projects MyProject \
  -import <target> \
  -processor x86:LE:64:default \
  -cspec windows \
  -analysisTimeoutPerFile 300 \
  -overwrite

# Run scripts on cached project (fast — no reimport)
$GHIDRA_HOME/support/analyzeHeadless \
  /tmp/ghidra-projects MyProject \
  -process <target-filename> \
  -noanalysis \
  -scriptPath "/path/to/scripts" \
  -scriptlog /tmp/script.log \
  -postScript ExtractFunctions.py ++output /tmp/functions.json
```

**Key flags:**

| Flag | Purpose |
|------|---------|
| `-import <file>` | Import binary (add `-overwrite` to reimport) |
| `-process [file]` | Run scripts on existing project (no reimport) |
| `-noanalysis` | Skip analysis pass (use with `-process` for script-only runs) |
| `-postScript <Name> [args]` | Script runs AFTER analysis — all API available |
| `-preScript <Name> [args]` | Script runs BEFORE analysis — functions not yet defined |
| `-scriptlog <file>` | Redirect script `println()` to file (separates from Ghidra framework log) |
| `-analysisTimeoutPerFile <sec>` | Kill analysis after N seconds (set 300–600 for large DLLs) |
| `-loader-loadLibraries true` | Load imported DLLs for cross-DLL xrefs |
| `-librarySearchPaths "<p1>;<p2>"` | Where to find dependent DLLs |
| `-processor <langID>` | Force architecture: `x86:LE:64:default` for 64-bit PE |
| `-cspec <specID>` | Compiler spec: `windows` for Windows PE |
| `-deleteProject` | Delete project on exit (CI/ephemeral use) |

**Script argument passing** — use `++` prefix (not `-`) to avoid conflict with analyzeHeadless flags:
```bash
-postScript MyScript.py ++output /tmp/out.json ++verbose
```
In script: `args = getScriptArgs()` returns `["++output", "/tmp/out.json", "++verbose"]`

**Common language IDs:**
- `x86:LE:64:default` — 64-bit x86-64 (most Windows PE/DLL)
- `x86:LE:32:default` — 32-bit x86

## Project Reuse (Performance)

```bash
# Import once (slow, ~30–300s)
analyzeHeadless /tmp/ghidra-projects MyProject \
  -import binary.exe -processor x86:LE:64:default -cspec windows \
  -analysisTimeoutPerFile 300 -overwrite

# Re-run scripts without reimporting (fast, ~1–5s)
analyzeHeadless /tmp/ghidra-projects MyProject \
  -process binary.exe -noanalysis \
  -postScript NewScript.py
```
