---
name: js-playwright-wasm-glue
description: Idiomatic review for Node.js glue code that bridges Rust wasm-bindgen modules to playwright-core (e.g. crates/wasm/src/glue/*.js in stapler-mcp). Use when reviewing or writing JS/TS files that call playwright-core APIs from a wasm-bindgen import object, wrap Playwright errors for the wasm boundary, manage browser/page lifecycle, or write node:test tests around that glue.
---

# Node.js + playwright-core wasm-bindgen glue idioms

Review checklist for JS glue code sitting between a Rust wasm-bindgen module and
`playwright-core`. Applies to files like `crates/wasm/src/glue/browser.js` and their
paired Rust FFI declarations (`crates/wasm/src/browser.rs`), plus `node:test` suites
that exercise them.

For each finding: `file:line`, severity (MUST FIX / SUGGEST), and a concrete fix.

## Checklist

### Error handling across the wasm boundary (MUST FIX)

1. Never re-throw a raw `JsValue` / opaque object across the JS→Rust boundary — throw
   or reject with a real `Error` (or something `JsError`-convertible on the Rust side).
2. Wrap low-level Playwright errors with operation/selector/page context rather than
   passing them through unchanged — a bare `Timeout 30000ms exceeded` is useless without
   knowing which locator or page it came from.
3. Don't hand-roll error construction/conversion that could be mis-caught by
   wasm-bindgen's own catch wrapper. Use the `JsError` pattern or
   `#[wasm_bindgen(catch)]` idiom on the Rust side instead of ad-hoc shapes.
4. Async glue functions must reject with an `Error`-like value on failure, never
   resolve with a `{success: false, error: ...}` sentinel object — that silently
   defeats `.catch()`/`try/catch` on the Rust side and any `#[wasm_bindgen(catch)]` fn.

### Playwright API anti-patterns (MUST FIX / SUGGEST)

5. **(MUST FIX)** Flag bare `page.type()` / `frame.type()` / `locator.type()` /
   `elementHandle.type()` — deprecated; use `locator.fill()` or
   `locator.pressSequentially()`.
6. **(MUST FIX)** Flag any reliance on `page.accessibility` — removed entirely from
   the Playwright API.
7. **(MUST FIX)** Flag arbitrary `page.waitForTimeout(ms)` sleep-based waits — prefer
   built-in auto-waiting or explicit state-based waits (`waitForSelector`,
   `waitForLoadState`, locator assertions).
8. **(MUST FIX)** Verify every `newContext()` / `newPage()` has a matching `close()` in
   a `try/finally`, especially on error paths — leaked contexts/pages accumulate across
   requests in a long-lived daemon.
9. **(SUGGEST)** Locators should favor role/test-id strategies (`getByRole`,
   `getByTestId`) over brittle CSS/XPath chains.

### Lifecycle / performance (MUST FIX)

10. `setInterval` used for idle-session reaping must call `.unref()` on the returned
    `Timeout` so it doesn't keep the process alive.
11. The reaper interval must be explicitly `clearInterval`'d on shutdown, not just
    `unref()`'d — `unref()` alone doesn't stop it from firing during graceful shutdown.

### Testing (`node:test`) idioms (SUGGEST / MUST FIX)

12. **(SUGGEST)** Prefer per-test `t.mock` (the test-context mock) over the top-level
    `mock` singleton — avoids cross-test mock leakage.
13. **(SUGGEST)** Flag module-level mocking of `playwright-core` itself via
    `--experimental-test-module-mocks` — still experimental with open bugs; prefer
    dependency injection (pass a browser/context factory into the glue code) instead.
14. **(MUST FIX)** On Node 24+, nested/subtests (`t.test()`) must be explicitly
    `await`ed — Node 24 removed implicit promise return/wait for subtests, so an
    un-awaited subtest can silently not run or report a false pass.

### Naming / API stability (SUGGEST)

15. Exported function names and argument/return shapes crossing the wasm boundary
    should be stable and intention-revealing. A shape drift here (e.g. renaming a
    field the Rust side destructures) is a silent runtime break, not a compile-time
    type error — treat these signatures with the same care as a public API.

## Notes for reviewers

- Items 5–9 depend on the installed `playwright-core` version — re-check Playwright's
  release notes / API deprecation list if it has been bumped since this checklist was
  written, since the specific deprecated methods can change across major versions.
- Items 1–4, 10–15 are architecture/idiom-level and are stable regardless of Playwright
  version.
