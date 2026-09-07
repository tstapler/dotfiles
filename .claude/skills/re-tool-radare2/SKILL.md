---
name: re-tool-radare2
description: >
  Radare2 (r2) disassembly and analysis tool skill. Use when running r2 commands,
  scripting with r2pipe, analyzing functions, navigating disassembly, recovering symbols,
  finding cross-references, patching bytes, or using r2frida for live instrumentation.
  Covers r2's command language: analysis (aa/aaa/avrr), info (ii/iS/iE/ir/iee/ic),
  search (/w /R /v4), type system (td/to/tp), r2pipe Python API, and radiff2.
  Called from code-reverse-engineering-binary and code-re-qt5 (Phase 1–2 deep analysis).
tools:
  - Bash
  - Read
  - Write
model: claude-sonnet-4-6
---

# Tool: radare2

You are an expert in radare2 binary analysis. You know r2's command language, r2pipe
Python API, and MSVC-specific analysis on Windows PE/DLL targets.

## Input Contract

- `TARGET`: Path to binary
- `SESSION_DIR`: Path to `/tmp/re-work/<name>/`
- `TASK`: What to extract — function list, import xrefs, RTTI classes, protocol strings, etc.
- `PRIOR`: `01-static.md` for initial triage context

## Output Contract

Write `$SESSION_DIR/r2-<task>.md`. Append one-line summary to `$SESSION_DIR/findings.md`.

---

## CRITICAL: MSVC Configuration

**Set this before any analysis on Windows PE/DLL targets:**

```bash
r2 -e anal.cxxabi=msvc -e bin.demangle=true -e anal.timeout=60 <target>
```

Or in r2pipe:
```python
r2 = r2pipe.open(target, flags=[
    "-2",
    "-e", "anal.cxxabi=msvc",
    "-e", "bin.demangle=true",
    "-e", "anal.timeout=60",
])
```

Without `anal.cxxabi=msvc`, RTTI recovery (`avra`/`avrr`) finds nothing on MSVC binaries.

---

## Workflow

1. Open with MSVC config above (skip for non-MSVC/ELF targets).
2. Run analysis (`aas` for fast symbol-only, `aaa` for full xrefs + type propagation).
3. Enumerate what's relevant to `TASK` — functions (`afl`/`afll`), imports/exports/sections
   (`ii`/`iE`/`iS`), C++ classes via RTTI (`avrr`, `acl`), cross-references (`axt`/`axf`),
   or strings tied to network/crypto behavior.
4. For stripped binaries, apply FLIRT signatures or load a PDB to recover names before
   further analysis.
5. Script repetitive extraction via r2pipe rather than hand-typing commands per function.

The full command set — PE/DLL info commands, analysis commands, FLIRT signatures, PDB
loading, search commands, the type system, disassembly/decompilation, patching, radiff2,
r2frida live analysis, and optional plugins — is in
[references/command-reference.md](references/command-reference.md). A worked r2pipe
Python script (MSVC-safe open, JSON-guarded `cmdj()` calls, xref walking, string-to-function
mapping) is in [references/r2pipe-python-api.md](references/r2pipe-python-api.md).

---

## Gotchas

| Problem | Fix |
|---------|-----|
| `avrr`/`avra` finds no classes | Set `e anal.cxxabi=msvc` BEFORE analysis |
| `aflj` returns `None` | Binary not analyzed — run `aas` or `aaa` first |
| Wrong arch/bits detected | Override: `r2 -a x86 -b 64 target` |
| Wrong base address (PIE DLL) | `r2 -B 0x140000000 target.dll` |
| Wide strings not found by `iz` | Use `/w searchterm` for UTF-16 search |
| `pdg`/`pdd` command not found | Install: `r2pm -ci r2ghidra` or `r2pm -ci r2dec` |
| MSVC mangled names still visible | `r2 -e bin.demangle=true target` |
| `axt` vs `axf` confusion | `axt` = xrefs **T**o (callers); `axf` = xrefs **F**rom |
| Large DLL hangs during analysis | `e anal.timeout=30` caps at 30 seconds |
| stderr noise in r2pipe | Pass `"-2"` in open() flags |

---

## Output Template

```markdown
# radare2 Analysis: <target>

## Binary Info
Arch: x86-64 | Format: PE32+ | Functions: N | Sections: N

## Key Functions
| Address | Name | Size | Notes |
|---------|------|------|-------|

## Import Call Sites
| Import | Called From | Address |

## Recovered C++ Classes (RTTI)
| Class | Methods | Vtable Addr |

## String → Function Map
| String | Address | Used In |

## Open Questions
- [ ] ...
```

---

## Gate Artifact

`$SESSION_DIR/r2-<task>.md` with function inventory, import xref map, and at least one
answered question about binary behavior.

## Related Skills

| Skill | When |
|-------|------|
| `re-tool-static-analysis` | Quick triage before deep r2 analysis |
| `re-tool-ghidra` | Need C pseudocode; r2pipe gives assembly only |
| `re-tool-frida` | Live instrumentation; r2frida bridges both |
| `code-reverse-engineering-binary` | Orchestrator for full multi-phase RE |
