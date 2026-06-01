---
name: code-go-git
description: Idiomatic review for go-git/go-git v5 concurrent access. Use when reviewing Go code that imports go-git, uses git.Repository, Worktree, CommitIter, or ObjectStorage. Covers the library's documented non-thread-safety, per-repo mutex requirements, and iterator lifetime rules.
---

# code-go-git

Idiomatic review checklist for go-git v5 concurrent access patterns.

## MUST FIX

1. [SAFETY] `*git.Repository` is NOT goroutine-safe — a per-repo `sync.Mutex` (not `sync.RWMutex`) is required for all access. Issue #773 is open as of v5.18.
2. [SAFETY] The packfile `MemoryIndex` has a confirmed concurrent-map crash (`fatal error: concurrent map read and map write`) triggered by concurrent `repo.Log()` / `CommitObject` on the same repo. Issue #1121, June 2024, unfixed in v5.x.
3. [SAFETY] `repo.Log()`, `CommitObject()`, and all iterator types are NOT safe to call concurrently on the same `*git.Repository`.
4. [CONCURRENCY] `repo.Worktree()` / `wt.Status()` wraps the same underlying object storage — calling concurrently on the same repo is unsafe.
5. [CONCURRENCY] The per-repo mutex must cover the **full iterator lifetime**, not just the initial API call. Iterators lazily read from shared object storage on each `Next()` — releasing the lock between obtaining an iterator and exhausting it is a data race.
6. [CONCURRENCY] `sync.RWMutex` does NOT help — go-git "read" operations mutate internal maps (object cache, MemoryIndex). Use `sync.Mutex` only.
7. [SAFETY] v5.17.0 added extension validation: `git.PlainOpen` now returns errors for repos with unsupported extensions. Errors from `PlainOpen` must propagate; never store a nil repo.
8. [ANTI-PATTERN] Never cache a `CommitIter` or `ObjectIter` across calls — iterators hold internal cursor state over shared storage. Create and fully drain within one mutex-protected window.
9. [ANTI-PATTERN] Never cache a `*Worktree` in a long-lived struct — it holds a snapshot of the HEAD/filesystem state and becomes stale after `git fetch` or index changes.
10. [ANTI-PATTERN] Never call `git.PlainOpen` while holding the per-repo mutex — `PlainOpen` reads `.git/config`, `HEAD`, and packed-refs from disk (I/O-bound). Open outside the lock, then store via `sync.Map.LoadOrStore`.
11. [CONCURRENCY] Concurrency fixes for `CommitObjects().Foreach()` and related iterators are v6-exp only and NOT backported to v5. There is no "safe subset" of go-git v5 that is natively goroutine-safe for shared-repo reads.

## SUGGEST

12. [PERF] `wt.Status()` is pathologically slow on repos with large numbers of untracked files — it hashes every untracked file regardless of `.gitignore`. Issue #181, open since 2020. Consider a TTL cache on the status result or a `git status --porcelain` subprocess fallback for large repos.
13. [CONCURRENCY] `sync.Map.LoadOrStore` is correct for cache-level concurrency. A `singleflight.Group` per path would also prevent duplicate `PlainOpen` calls under contention — evaluate if `PlainOpen` latency is a measured bottleneck.

## STYLE

14. [STYLE] `sync.Map` at the cache level (one entry per repo path) is the correct granularity. Per-repo `sync.Mutex` on the `*cachedRepo` entry is the correct serialisation granularity. Do not conflate the two.
15. [STYLE] `map[plumbing.Hash]struct{}` is idiomatic for sets. `map[plumbing.Hash]bool` works but communicates less intent.

## References
- [Concurrency Issues #773](https://github.com/go-git/go-git/issues/773)
- [MemoryIndex crash #1121](https://github.com/go-git/go-git/issues/1121)
- [Status() slow with untracked files #181](https://github.com/go-git/go-git/issues/181)
