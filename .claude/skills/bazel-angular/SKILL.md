---
name: bazel-angular
description: Build an Angular CLI app with Bazel 9 (aspect_rules_js) in the sandbox, and embed the bundle in another target (e.g. Rust rust-embed). Use when adding or fixing a Bazel build for an Angular/ng project, when `ng build` fails under Bazel with "file is missing from the TypeScript compilation", or when wiring a UI bundle into a Rust/Go binary.
---

# Angular + Bazel (rules_js), sandboxed

Worked out on `tstapler/consolette` (branch `spike/bazel`, 2026-10-09; Bazel 9.3.0,
`aspect_rules_js` 3.5.1, `rules_nodejs` 6.7.6, Angular 19). Everything below was run there unless
marked UNVERIFIED. Layout: Angular project in `ui/`, `package-lock.json` (npm).

## The one trap: a bare `ng build` fails in the sandbox

```
✘ [ERROR] File '.../execroot/_main/bazel-out/<cfg>/bin/ui/src/main.ts' is missing from the
TypeScript compilation. [plugin angular-compiler]
```

It passes with `--spawn_strategy=local`, so it is a sandbox problem, not a config problem.
Sandbox inputs are symlinks; the path in the error is the **real** output-base path while the
TypeScript program holds the sandbox path. Consistent with the evidence: the Angular compiler
plugin and tsc disagree on file identity (not proven in the plugin source).

**Don't:**
- tag the action `no-sandbox` / `local` — works, but loses hermeticity and remote-cache eligibility.
- pass `ng build --preserve-symlinks` — fixes `main.ts` but pnpm-layout `node_modules` resolution
  needs realpaths, so transitive deps fail (`Could not resolve "@kurkle/color"`).

**Do:** make the sources real files and keep `node_modules` a symlink — copy them into a scratch
dir inside the action and run `ng` there.

`ui/bazel_ng_build.mjs`:
```js
import { spawnSync } from "node:child_process";
import { cpSync, mkdtempSync, symlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const root = process.cwd();                    // bin/ui (js_run_binary chdir)
const out = resolve(root, process.argv[2]);    // declared output dir
const work = mkdtempSync(join(tmpdir(), "ng-build-"));
for (const e of ["src", "public", "angular.json", "package.json", "tsconfig.json", "tsconfig.app.json"]) {
  cpSync(join(root, e), join(work, e), { recursive: true, dereference: true });
}
symlinkSync(join(root, "node_modules"), join(work, "node_modules"));
const r = spawnSync(process.execPath,
  [join(work, "node_modules/@angular/cli/bin/ng.js"), "build",
   "--base-href", "/dashboard/", "--output-path", out],
  { cwd: work, stdio: "inherit", env: { ...process.env, NG_CLI_ANALYTICS: "false" } });
process.exit(r.status ?? 1);
```

`ui/BUILD.bazel`:
```python
load("@aspect_rules_js//js:defs.bzl", "js_binary", "js_library", "js_run_binary")
load("@npm//:defs.bzl", "npm_link_all_packages")

npm_link_all_packages(name = "node_modules")

js_library(name = "ui_srcs", srcs = glob(["src/**", "public/**"]) + [
    "angular.json", "package.json", "tsconfig.json", "tsconfig.app.json"])

js_binary(name = "ng_build", entry_point = "bazel_ng_build.mjs")

js_run_binary(
    name = "dashboard",
    srcs = [":node_modules", ":ui_srcs"],
    args = ["dist/consolette"],        # relative to chdir
    chdir = package_name(),
    out_dirs = ["dist/consolette"],    # ng writes <out>/browser/...
    tool = ":ng_build",
)
```
Keep the input list in sync with the real project (add `tsconfig.spec.json`, assets, etc.). Output
path is relative to `chdir`: `--output-path ui/dist/...` lands in `bin/ui/ui/dist` and the declared
output dir comes back **empty** with no error — check `ls bazel-bin/<pkg>/dist/...` after the first
build.

## MODULE.bazel (npm via rules_js)

```python
bazel_dep(name = "aspect_rules_js", version = "3.5.1")
bazel_dep(name = "rules_nodejs", version = "6.7.6")

node = use_extension("@rules_nodejs//nodejs:extensions.bzl", "node")
node.toolchain(node_version = "20.19.0")

npm = use_extension("@aspect_rules_js//npm:extensions.bzl", "npm")
npm.npm_translate_lock(
    name = "npm",
    npm_package_lock = "//ui:package-lock.json",
    pnpm_lock = "//ui:pnpm-lock.yaml",        # required in bzlmod; generated, commit it
    update_pnpm_lock = True,
    data = ["//ui:package.json", "//ui:pnpm-workspace.yaml"],
    run_lifecycle_hooks = False,              # esbuild/parcel ship prebuilt platform binaries
)
use_repo(npm, "npm")
```

Setup gotchas, in the order you hit them:
1. Root-level `//:Cargo.lock`-style labels need a `BUILD.bazel` in that package first.
2. `npm_translate_lock` has no `package_json` attribute; pass it via `data`.
3. rules_js refuses to run until pnpm build-script policy is declared: create
   `ui/pnpm-workspace.yaml` with `onlyBuiltDependencies: []` (npm ignores the file).
4. `pnpm_lock` must be set even with `npm_package_lock`. Create an empty `ui/pnpm-lock.yaml`; the
   first build fails with "file updated. Please run your build again" — run it again.
5. Keep the two lockfiles in sync when dependencies change: `bazel run @npm//:sync`
   (UNVERIFIED — the first-run auto-update was exercised, the sync command was not).
6. Aspect telemetry is on by default; opt out with `common --repo_env=DO_NOT_TRACK=1` in `.bazelrc`.
7. Bazel 9 has no `WORKSPACE`; also load `rules_cc` etc. explicitly (see `bazel-version-upgrades`).

## Embedding the bundle in Rust (`rust-embed`)

```python
# MODULE.bazel — crate_universe annotations do NOT forward Cargo features, so name all three
[crate.annotation(crate = n, crate_features = ["debug-embed"])
 for n in ["rust-embed", "rust-embed-impl", "rust-embed-utils"]]
```
```python
# BUILD.bazel
rust_library(
    name = "lib",
    compile_data = glob(["src/**"], exclude = ["src/**/*.rs"]) + ["//ui:dashboard"],
    rustc_env = {"CARGO_MANIFEST_DIR": "$(BINDIR)"},   # `#[folder]` resolves under bin/, where the UI lives
    ...
)
```
- Without `debug-embed`, debug/fastbuild reads the folder at **runtime**; with it only on
  `rust-embed`, the derive fails with `no variant ... Dynamic found for enum Filenames`.
- `include_str!`/`include_bytes!` data files need to be in `compile_data` (errors show a
  `bazel-out/.../bin/src/...` path that "doesn't exist").
- Unit tests that `include_str!` fixtures need their own `compile_data`.
- Set the Angular `<base href>` to wherever the server mounts the SPA (`--base-href /dashboard/`);
  a wrong base makes the browser request assets at `/` and 404, with the page itself returning 200.

## Verify (don't stop at "build succeeded")

```bash
bazel build //ui:dashboard 2>&1 | grep -E "JsRunBinary.*sandbox"   # runs sandboxed, not "local"
ls bazel-bin/ui/dist/consolette/browser | head                     # outputs non-empty
# a UI edit that really changes the bundle must change the binary:
sed -i.x 's#<title>Ui</title>#<title>Ui probe</title>#' ui/src/index.html
bazel build //:app && shasum -a 256 bazel-bin/app                  # hash changed
mv ui/src/index.html.x ui/src/index.html                           # revert
```
A comment-only UI edit does **not** change the bundle, so the Rust target correctly doesn't
rebuild (early cutoff) — don't read that as "the UI isn't tracked". Also keep one test that reads
the embedded `index.html` and checks every referenced asset resolves under the base href.

Measured (consolette, macOS arm64): cold ≈ 9 min / ~1000 actions for the Rust side; no-op rebuild
0.6 s; UI-only change ≈ 12 s for the sandboxed `ng` action; Rust edit ≈ 23 s.

## Not covered (UNVERIFIED)

Linux, remote cache, bundle determinism across machines, `rules_ts`/`ts_project` for type-check
as a separate cached step, `ng test`/Karma under Bazel, `ng serve` dev loop (keep using plain
`npm start` for that).

## Related skills

`bazel-version-upgrades` (Bazel 9 migration), `bazel-github-actions-ci` (CI + caches),
`bazel-perf` (profiling), `rust-development`.
