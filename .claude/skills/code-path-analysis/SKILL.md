---
name: code-path-analysis
description: >
  Trace static call paths through a codebase — forward ("what does this entry point reach")
  and backward ("what reaches this function") — for impact analysis before a change,
  blast-radius estimation for an incident, dead-code detection, or verifying a security-relevant
  path (auth check, sanitizer) actually sits on every route to a sink. Language-agnostic:
  prefers LSP-based call hierarchy (serena MCP) when available, falls back to per-language
  call-graph tools, falls back further to an ast-grep/ripgrep BFS. Use before touching a function
  with unclear blast radius, before removing what looks like dead code, or when asked "what
  calls this" / "what does this call" / "trace the path from X to Y".
---

# Code Path Analysis

Two distinct questions, often confused:

- **Forward reachability** — starting at an entry point (HTTP handler, CLI command, event
  consumer, or any function), what can it reach? Answers "if I change this, what downstream
  behavior might shift" and "does every path from this entry point pass through the auth check."
- **Backward reachability** — starting at a function, what calls it, directly or transitively?
  Answers "is this safe to delete/change" and "what's the actual blast radius of this bug."

Both are graph traversals over the same underlying call graph; only the traversal direction
differs. This skill is the static, source-level version — reachability by construction, not by
observed behavior. See `code-hotspot-analysis` for churn/complexity signals, `code-archaeology`
for whole-repo reverse-engineering, and **When NOT to Use This** below for where a runtime
approach (traces, profiles, coverage) is the better tool.

## Tool Tiers — Prefer the Cheapest That Answers the Question

### Tier 1: LSP-based call hierarchy (serena MCP, or an editor)

If the `serena` MCP server is configured (per this environment's `CLAUDE.md`: "use serena for
complex multi-file structural edits" — its symbol tools are built on the same LSP call-hierarchy
primitive every language server exposes), this is the right first stop for *any* language with a
working language server (Go, Java/Kotlin, Python, TypeScript/JavaScript, Rust, C/C++):

1. `find_symbol` to locate the entry point or target function precisely (not a text match — a
   resolved symbol).
2. `find_referencing_symbols` on it — this is backward reachability (LSP's `incomingCalls`) in
   one call, already deduplicated and resolved through interfaces/generics where the language
   server can.
3. Recurse on each result up to a bounded depth (3-4 hops is usually enough to answer "is this
   safe" — see **Anti-Patterns** on unbounded recursion).
4. For forward reachability, `get_symbols_overview` on the entry point's file/class plus reading
   the function body directly is usually faster than chaining `outgoingCalls` — forward tracing
   from one starting point is naturally a smaller, more linear search than backward tracing from
   a widely-used utility.

No editor and no serena? Any IDE with a real language server does the same thing manually:
IntelliJ/VS Code "Find Usages" (backward) and "Call Hierarchy" (both directions) panels. This is
the same LSP `incomingCalls`/`outgoingCalls` data serena queries programmatically — reach for it
when you need one focused answer and don't want to script anything.

### Tier 2: Dedicated call-graph tools, per language

Reach for these instead of Tier 1 when you need the **whole graph** (to render, to diff between
two commits, to feed into another tool) rather than one function's neighbors — Tier 1 answers
one query at a time; these dump the full structure.

| Language | Tool | Notes |
|---|---|---|
| Go | `golang.org/x/tools/cmd/callgraph`, `go-callvis` | Whole-program call graph; `-algo=cha` is precise but can hang on large codebases with generics (same Go 1.25+ `gotypesalias` gotcha as `code-hotspot-analysis` — fall back to `-algo=static` for intraprocedural-only) |
| Python | `pyan3`, `pycg` | Static only — misses anything dispatched via `getattr`/duck typing/decorators that rewrite the call target; treat gaps as expected, not tool failure |
| JS/TS | `js-callgraph` (function-level), `madge` (module/import-level only — **not** a call graph, don't conflate the two) | Dynamic dispatch (higher-order callbacks, `.bind`, framework DI containers like NestJS/Angular) is invisible to static JS call-graph tools; treat results as a lower bound |
| Java/Kotlin | IDE call hierarchy (IntelliJ `Ctrl+Alt+H`) is the practical default — dedicated CLI call-graph tools (WALA, Soot) are heavyweight to stand up for an ad hoc question | Spring/DI-heavy codebases break static call graphs badly: a `@Autowired` interface call resolves to whichever bean is wired at runtime, which the graph can't know. Cross-check with Sourcegraph/GHES code search for "find implementations of this interface" instead of trusting the static edge |
| Rust | rust-analyzer's call hierarchy via any LSP-aware editor (Tier 1 covers this) | No mature standalone CLI whole-graph tool for application code; `cargo-call-stack` exists but targets embedded/no_std stack-depth analysis, not general call-graph export |
| C/C++ | `cscope`, `cflow`, `clang -Xclang -ast-dump` | `cscope`'s "find callers of this function" is the fastest path for a single backward query without full LSP setup |
| Cross-repo, any language | Sourcegraph (`sourcegraph-official` MCP tools when connected) | Best option when the call spans repos a local checkout doesn't have — code search + "find references" across the whole indexed org, not just one clone |

### Tier 3: Generic fallback (no language server, no dedicated tool)

Works on anything, including config-driven or dynamically-typed code where the tools above give
up. Slower and noisier — text matching, not semantic resolution — but always available.

```bash
# 1. Locate the function definition precisely (ast-grep, not grep, so you match the
#    declaration and not every mention of the name in comments/strings):
sg run --pattern 'function $NAME($$$) { $$$ }' --lang js .       # adjust pattern per language
sg run --pattern 'func $NAME($$$PARAMS) $$$RET { $$$ }' --lang go .

# 2. Backward: find call sites of that name across the repo, then repeat step 1 on each
#    enclosing function to walk one hop further up:
rg -n '\bfunctionName\(' --type js -g '!*.test.*'

# 3. Forward: read the function body found in step 1, extract the names it calls, repeat.
```

A small BFS script is worth writing the moment you're tracing more than 2-3 hops by hand —
maintain an explicit `visited` set keyed by (file, function) and stop descending into anything
already visited. This is the single most important correctness detail in tier 3: without it,
mutual recursion or a common utility called from many places turns a bounded trace into an
infinite loop or an exponential blow-up of duplicate work.

```python
#!/usr/bin/env python3
"""Generic backward-reachability BFS: who (transitively) calls TARGET.
Text-based — a lower bound on the true call graph, not a precise one. Good enough to scope
a change's blast radius when no language server / dedicated tool is available.
"""
import re, subprocess, sys
from collections import deque

def callers_of(name, exclude_globs=("*_test.*", "*.test.*")):
    cmd = ["rg", "-n", "--no-heading", rf"\b{re.escape(name)}\s*\("]
    for g in exclude_globs:
        cmd += ["-g", f"!{g}"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return {line.split(":", 1)[0] for line in out.splitlines()}  # set of files; refine to
    # enclosing-function-name per hit if you need node-level (not file-level) resolution

def bfs(target, max_depth=4):
    visited, frontier, depth = {target}, deque([(target, 0)]), {}
    while frontier:
        name, d = frontier.popleft()
        if d >= max_depth:
            continue
        for f in callers_of(name):
            key = f"{f}::{name}"          # file-level node; coarse but avoids re-deriving
            if key in visited:            # the calling function's own name from grep output
                continue
            visited.add(key)
            print(f"{'  ' * (d+1)}{key}")
            frontier.append((name, d + 1))  # NOTE: re-queuing `name`, not the caller's name —
            # a real implementation should extract the enclosing function per hit and queue
            # THAT; this stub illustrates the visited-set/depth-bound structure, not a
            # ready-to-run tool. Extracting the enclosing function is language-specific
            # (indentation for Python, brace-matching for C-family) — reuse tier 1/2 instead
            # of writing that parser if a language server is available at all.
    return visited

if __name__ == "__main__":
    bfs(sys.argv[1], max_depth=int(sys.argv[2]) if len(sys.argv) > 2 else 4)
```

## Workflow

1. State the question precisely before picking a tool: forward or backward, from which exact
   symbol (not just a filename), to what depth, and why (a refactor's blast radius, a security
   path's completeness, a dead-code claim). The direction and depth determine which tier is worth
   the setup cost.
2. Try Tier 1 (serena/LSP or an editor) first — it's the cheapest correct answer for a single
   function's immediate neighbors and resolves through most language features tier 2/3 can't
   (generics, interfaces, some overloading).
3. Escalate to Tier 2 only when you need the whole graph rendered/exported, or the language
   server can't resolve the dispatch (see the Java/Python DI caveats above) and you need a
   coarser but complete static picture instead.
4. Fall back to Tier 3 only when neither is available — config-driven codebases, unsupported
   languages, or a quick one-off in an unfamiliar repo with no LSP set up.
5. At every tier, explicitly flag where the trace goes dark: reflection, dependency injection,
   dynamic dispatch, event buses/pub-sub, and third-party library internals all break static
   analysis. State the gap rather than silently treating an unresolved edge as "no callers."
6. For a security or correctness claim ("every path to this sink passes through the sanitizer"),
   forward-trace from *every* entry point that can reach the sink, not just the one you started
   from — a single confirmed path proves the property holds *somewhere*, not everywhere.
7. Record findings as an indented text tree or a `.dot` graph if the trace is going into a
   PR description, ADR, or incident writeup — a screenshot of an IDE call-hierarchy panel is not
   reproducible for a reviewer without the same setup; a text trace or rendered graph is.

## When NOT to Use This

- **"What actually executes for this request in prod"** — that's a runtime question. Use traces
  (Edgar/Jaeger/whatever your APM is), a profiler (Pyroscope, `pprof`), or test-coverage
  instrumentation instead of static analysis, which shows what's *possible*, not what *happens*.
- **Heavily dynamic-dispatch codebases without a runtime cross-check** — Spring DI, JS callback
  soup, Python duck typing, Ruby metaprogramming. Static tracing still narrows the search space,
  but treat every result as a lower bound and pair it with a runtime signal before making a
  destructive claim ("nothing calls this") on that basis alone.
- **Whole-codebase architectural review** — that's `code-hotspot-analysis` (coupling/complexity
  prioritization) or `code-architecture-best-practices` (principle-level review), not a
  point-to-point trace.

## Anti-Patterns

- **Unbounded recursion with no visited set.** Recursive functions, mutual recursion, and widely
  shared utilities all turn an un-guarded traversal into an infinite loop or a combinatorial
  blow-up. Always track visited nodes and cap depth explicitly.
- **Treating an unresolved dynamic-dispatch edge as "confirmed: no callers."** Silence from a
  static tool at a DI/reflection/event-bus boundary means "couldn't determine," not "none exist."
  Say so.
- **Conflating module/import graphs with call graphs.** `madge`, `goda`, and similar
  dependency-graph tools show "file A imports file B," not "function in A calls function in B."
  A file can import another and never call anything in it; treat import graphs as a coarser,
  different signal, useful for `code-hotspot-analysis`'s coupling axis but not a substitute here.
- **Stopping at your own repo's boundary without saying so, when the real question spans repos.**
  If the entry point calls into a library or a different service, say the trace stopped there
  rather than implying completeness — use Sourcegraph/GHES search to continue if the question
  genuinely requires it.

## Related Skills

| Skill | When to apply |
|---|---|
| `code-hotspot-analysis` | Complexity × churn prioritization — a different axis (where to look), not a path trace (how X reaches Y) |
| `code-ast-grep` | Deeper `sg` pattern syntax for Tier 3's structural queries |
| `code-archaeology` | Whole-unfamiliar-repo reverse engineering; use this skill for one specific path within a repo you already understand structurally |
| `quality:find-dead-code` | Backward-reachability tracing is the manual version of what that command automates for "is this ever called" claims |
| `security-review` | Forward-tracing from untrusted input to a sink, and confirming a sanitizer/auth-check sits on every path, is this skill applied to a security question specifically |
