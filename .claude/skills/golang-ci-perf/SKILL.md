---
name: golang-ci-perf
description: Speed up slow Go test suites and CI pipelines. Covers measuring per-test/per-package timing, eliminating subprocess overhead (shell-outs to git/cli tools), replacing real databases/filesystems with in-memory equivalents, safe t.Parallel() adoption, and CI-level caching/sharding. Use when `make test`/`go test ./...` or CI is slow and you need to find and fix the actual bottleneck rather than guessing.
---

# Go Test Suite & CI Performance

End-to-end workflow: measure → find the dominant cost class → apply the matching fix → re-measure → parallelize what's left → cache/shard at the CI level.

Don't skip straight to `t.Parallel()`. A test suite that's slow because every test forks a `git` subprocess or writes to a real SQLite file on disk will not get meaningfully faster from parallelism alone — it moves the same wall-clock cost onto more CPUs and can even get *slower* under contention (disk I/O, subprocess scheduling). Fix the per-test cost first, then parallelize.

## Bottleneck-to-Fix Strategy

| Symptom in timing output | Likely cause | Fix | Step |
|---|---|---|---|
| Every slow test shells out (`exec.Command`, `safeexec.CommandContext`) | Subprocess fork/exec overhead, repeated across hundreds of tests | Replace with an in-process library call | Step 2 |
| Slow tests all touch a real DB file / `sql.Open("sqlite3", path)` | Real disk I/O, file locking, driver overhead | In-memory backend (`:memory:` DSN, or an in-memory fake) | Step 3 |
| Package takes N seconds serial, tests are independent | No parallelism | `t.Parallel()` | Step 4 |
| CI job slow but local `go test` is fast | Cold build cache, no module cache, serial package execution | CI-level caching + `-p`/sharding | Step 5 |

---

## Step 1 — Measure Before Fixing

Never guess which test is slow — profile the test run itself first.

```bash
# Per-test timing, sorted slowest-first (needs gotestsum, or parse -json by hand)
go test -json ./... > /tmp/test-timing.json
gotestsum --raw-command -- go test -json ./... # nicer live view

# Built-in: verbose timing per test, no extra tool
go test -v ./pkg/... 2>&1 | grep -E '^(--- PASS|--- FAIL)' | sort -t'(' -k2 -rn | head -20

# Per-package wall time (what CI actually pays for)
go test ./... -json | jq -r 'select(.Action=="pass" and .Test==null) | "\(.Elapsed)\t\(.Package)"' | sort -rn | head -20
```

```bash
# CPU profile of the test binary itself (not your app) — useful when a test is
# CPU-bound rather than I/O-bound (see golang-profiling for full pprof workflow)
go test -cpuprofile=cpu.prof -run=TestSlowThing ./pkg
go tool pprof -top cpu.prof
```

Bucket the slow tests: are they slow because of subprocess calls, real I/O, or actual CPU work? Grep the slow package for the smoking gun before touching anything:

```bash
grep -rn 'exec.Command\|safeexec.CommandContext' ./pkg/*_test.go
grep -rn 'sql.Open\|os.MkdirTemp\|ioutil.TempDir' ./pkg/*_test.go
```

---

## Step 2 — Eliminate Subprocess Overhead

Every `exec.Command("git", ...)` / `safeexec.CommandContext(ctx, "git", ...)` in a test helper is a fork+exec, which dominates wall time when it runs in hundreds of tests. If an in-process Go library exists for the same operation, use it — this also removes a dependency on the `git` binary being on `$PATH` in CI.

**Wrong (subprocess per test):**
```go
func setupTestRepo(t *testing.T) string {
	dir := t.TempDir()
	run := func(args ...string) {
		cmd := exec.Command("git", args...)
		cmd.Dir = dir
		if err := cmd.Run(); err != nil {
			t.Fatalf("git %v: %v", args, err)
		}
	}
	run("init", "-b", "main")
	run("config", "user.email", "test@test.com")
	run("config", "user.name", "Test User")
	os.WriteFile(filepath.Join(dir, "README.md"), []byte("# Test"), 0644)
	run("add", "README.md")
	run("commit", "-m", "initial")
	return dir
}
```

**Right (go-git, in-process):**
```go
func setupTestRepo(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()

	repo, err := git.PlainInitWithOptions(dir, &git.PlainInitOptions{
		InitOptions: git.InitOptions{DefaultBranch: plumbing.NewBranchReferenceName("main")},
	})
	if err != nil {
		t.Fatalf("git init failed: %v", err)
	}
	if err := os.WriteFile(filepath.Join(dir, "README.md"), []byte("# Test"), 0644); err != nil {
		t.Fatalf("write README: %v", err)
	}
	wt, err := repo.Worktree()
	if err != nil {
		t.Fatalf("worktree: %v", err)
	}
	if _, err := wt.Add("README.md"); err != nil {
		t.Fatalf("add: %v", err)
	}
	if _, err := wt.Commit("initial", &git.CommitOptions{
		Author: &object.Signature{Name: "Test User", Email: "test@test.com", When: time.Now()},
	}); err != nil {
		t.Fatalf("commit: %v", err)
	}
	return dir
}
```

`github.com/go-git/go-git/v5` covers init/add/commit/worktree/most read operations. It is **not** a full replacement for the `git` CLI everywhere — keep the subprocess for operations go-git handles poorly or not at all:

| Keep as subprocess | Why |
|---|---|
| Real `git merge` with conflict resolution | go-git's merge support is limited |
| `git clone`/fetch/push against a real remote | Needs credential helpers, transport auth |
| `git rebase`, interactive history rewrites | Not supported by go-git |
| A specific documented race workaround (e.g. a torn-read on ref files) | Only fall back for the *specific* failure mode, not "just in case" |

If two packages in the repo already import go-git under different names, watch for an import alias collision when the same file also imports an internal package literally named `git` — alias the go-git import (`gogit "github.com/go-git/go-git/v5"`) rather than renaming the internal one. See `code-go-git` skill for the broader native-Go-git-library pattern, and `.claude/rules/prefer-go-git-over-subshells.md`-style rules for the general subprocess-elimination principle if this repo has one.

Apply the same lens to any other CLI your tests shell out to repeatedly (`jj`, `docker`, cloud CLIs) — check whether a Go SDK/library exists before assuming the subprocess is unavoidable.

---

## Step 3 — Replace Real I/O With In-Memory Equivalents

A test DB backed by a real file on disk pays for file creation, locking, and fsync on every test. Most SQL drivers support an in-memory mode that's a drop-in DSN change.

```go
// Before: real file per test
db, err := sql.Open("sqlite3", filepath.Join(t.TempDir(), "test.db"))

// After: in-memory, same driver, same SQL dialect
db, err := sql.Open("sqlite3", "file::memory:?cache=shared")
```

Caveats:
- `cache=shared` is required if multiple connections in the same test need to see the same in-memory database (a connection pool with >1 conn otherwise gets a *fresh* empty DB per connection).
- In-memory means no state survives the test process — fine for unit tests, wrong for a test that's specifically verifying on-disk durability/crash-recovery behavior. Keep a real-file-backed version for those specific tests.
- Same principle applies beyond SQL: an in-memory `fstest.MapFS` instead of writing real files when the code under test only needs an `fs.FS`, or an in-process fake instead of a real network listener when only the protocol matters.

---

## Step 4 — Parallelize What's Left

Once per-test cost is down to real, independent work, add `t.Parallel()`.

```go
func TestSomething(t *testing.T) {
	t.Parallel() // must be the first statement (after t.Helper() if present)
	// ...
}
```

**Table-driven subtests** — check the module's Go version first (`go.mod`'s `go` directive):

```go
for _, tc := range cases {
	tc := tc // only needed pre-Go 1.22; loop var is per-iteration from 1.22 onward
	t.Run(tc.name, func(t *testing.T) {
		t.Parallel()
		// ...
	})
}
```

### When NOT to add t.Parallel()

| Blocker | Why |
|---|---|
| `t.Setenv(...)` anywhere in the test | Go's `testing` package panics if `t.Setenv` is called after/with `t.Parallel()` — they are mutually exclusive by design |
| `os.Chdir` (process-wide CWD) | Races with every other parallel test's relative paths |
| Shared package-level `var` / singleton mock | Data race unless properly synchronized — don't paper over with a mutex just to force parallelism |
| Fixed port / fixed file path (not `t.TempDir()`/`:0` port) | Two parallel tests collide |
| Test asserts on real wall-clock ordering relative to another test | Parallel execution order is unspecified |

Run with `-race` after adding parallelism — `t.Parallel()` is exactly the kind of change that turns a latent data race into a flaky failure:

```bash
go test -race -parallel 8 ./pkg/...
```

A parent test with parallel subtests doesn't finish until all subtests do — `t.Parallel()` at the parent level lets *sibling top-level tests* run concurrently with each other, not with their own subtests.

---

## Step 5 — CI-Level Speedups

Fixes above reduce total CPU-seconds. These reduce wall-clock time in CI specifically, on top of that:

```yaml
# .github/workflows/test.yml
- uses: actions/setup-go@v5
  with: { go-version: stable }
  # actions/setup-go caches the module + build cache keyed on go.sum automatically
  # when cache: true (default) — verify it's not disabled before adding a manual cache step

- name: Test
  run: go test ./... -p 4 -timeout=10m
  # -p N caps how many packages build/test concurrently — tune to the runner's CPU count,
  # don't leave it at the Go default if the runner has fewer cores than the local dev machine
```

- **`-short` for a fast CI gate, full suite on a slower/nightly job** — mark expensive integration tests with `if testing.Short() { t.Skip(...) }` and run `go test -short ./...` on every push, `go test ./...` on a schedule or pre-merge queue.
- **Test sharding** — split `go test ./...` across N CI jobs by package (`go list ./... | split -n l/$N`) when a single job's wall time dominates the pipeline, rather than fighting for more parallelism inside one job.
- **Don't cache what changes every run** — caching `go build` output keyed on `go.sum` is safe; caching test *results* is not (masks real failures) unless the CI system's test-caching is content-addressed and you understand what invalidates it (`go test` itself already skips unchanged, successful packages via its own build cache — verify this isn't being defeated by `-count=1` in CI when it doesn't need to be).

---

## Quick Reference

| Goal | Command |
|---|---|
| Slowest tests, sorted | `go test -json ./... \| jq -r 'select(.Action=="pass" and .Test==null) \| "\(.Elapsed)\t\(.Package)"' \| sort -rn` |
| Find subprocess calls in tests | `grep -rn 'exec.Command\|safeexec.CommandContext' **/*_test.go` |
| Find real-file DB opens | `grep -rn 'sql.Open' **/*_test.go` |
| In-memory SQLite DSN | `file::memory:?cache=shared` |
| Run with race detector after parallelizing | `go test -race -parallel 8 ./...` |
| Cap package-level test concurrency | `go test -p 4 ./...` |
| Fast CI gate (skip expensive tests) | `go test -short ./...` |
| CPU profile a specific slow test | `go test -cpuprofile=cpu.prof -run=TestName ./pkg` |

---

## Related Skills

| Skill | When to apply |
|---|---|
| `golang-profiling` | The test binary itself is CPU/memory-bound (not I/O/subprocess-bound) — full pprof workflow |
| `golang-testing` | Writing/structuring tests themselves (table-driven, testify, fixtures, naming) — this skill assumes tests already exist and focuses on making them fast |
| `code-go-git` | Deeper reference on replacing git subprocess calls with go-git specifically |
| `fix-ci-failures` | CI is failing rather than just slow |
| `infra-docker-build-test` | The slow step is a container build/test cycle, not `go test` itself |

## Common Pitfalls

- **Parallelizing before fixing the per-test cost** — `t.Parallel()` on a subprocess-heavy suite mostly just contends more subprocesses for the same CPUs; fix Step 2/3 first.
- **`t.Setenv` + `t.Parallel()`** — Go's testing package will panic at runtime (`testing: t.Setenv called after t.Parallel`); remove one or the other, don't work around it with `os.Setenv` directly (that reintroduces the race `t.Setenv`'s restriction exists to prevent).
- **Loop-variable capture in parallel subtests** — only a real bug pre-Go 1.22; check `go.mod` before assuming you need `tc := tc`, and don't add it needlessly on 1.22+ (dead code that suggests a bug that can't happen).
- **In-memory DB losing state between connections** — forgetting `?cache=shared` (or equivalent) makes a pooled in-memory DB look empty from a second connection; this reads as a flaky/failing test, not an obvious config issue.
- **Silent scope creep during subprocess conversion** — a helper reused by both a simple init/commit path and a complex merge/rebase path; convert only the call sites that are genuinely simple, and grep for every caller before deleting the subprocess version.
- **`-count=1` blanket-applied in CI** — defeats Go's own test result caching for packages that didn't change; only add it where you specifically need to force a re-run (e.g. after a flaky-test investigation), not as a default.
- **Declaring victory on `go build` after editing `_test.go` files** — `go build ./...` does not compile test files at all. Use `go vet ./...` (or `go test -run=^$ ./...` to compile without running) to confirm test-file edits actually compile.
