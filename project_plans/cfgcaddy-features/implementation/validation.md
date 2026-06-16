# Validation Plan: cfgcaddy Feature Expansion

**Phase:** SDD Phase 4 — Pre-Implementation Validation  
**Date:** 2026-06-16  
**Source documents:**
- `project_plans/cfgcaddy-features/requirements.md`
- `project_plans/cfgcaddy-features/implementation/plan.md`
- `project_plans/cfgcaddy-features/implementation/adversarial-review.md`

---

## 1. Test Case Table

### Unit Tests

| ID | Type | Requirement | Plan Story | Description | Pass Criteria |
|----|------|-------------|------------|-------------|---------------|
| U-001 | unit | F1-AC2 | 1.3 | `LocalDataLoader.load()` returns `{}` when `local.toml` absent | No exception; return value is empty dict |
| U-002 | unit | F1-AC1, F3-AC1 | 1.3 | `LocalDataLoader` with profile merges profile keys over base keys | Conflicting key resolves to profile value |
| U-003 | unit | F3-AC1 | 1.3 | Missing profile file raises `CfgcaddyError` (not raw `FileNotFoundError`) | Exception type is `CfgcaddyError` with descriptive message |
| U-004 | unit | F1-AC1 | 1.3 | `validate_profile_name("../../../etc/passwd")` raises `CfgcaddyError` | Exception raised; no file I/O attempted |
| U-005 | unit | F1-AC1 | 1.3 | `validate_profile_name("work")` passes | No exception |
| U-006 | unit | F1-AC1 | 1.3 | `validate_profile_name("work.v2")` raises (dots disallowed) | Exception raised |
| U-007 | unit | F1-AC1 (security) | 1.3 | Profile path containment guard: PROFILES_DIR symlink attack | Resolved path outside PROFILES_DIR raises `CfgcaddyError` |
| U-008 | unit | F1-AC1 | 2.1 | Non-`.tmpl` path passes through `render_if_template` unchanged | Returned path equals input path |
| U-009 | unit | F1-AC1 | 2.1 | `.tmpl` source renders variable substitution to correct cache path | Rendered content contains substituted value; cache path has no `.tmpl` suffix |
| U-010 | unit | F1-AC2 | 2.1 | Missing variable raises `CfgcaddyError` naming variable and file path | Exception message contains variable name and source file path |
| U-011 | unit | F1-AC2 | 2.1 | `TemplateSyntaxError` raises `CfgcaddyError` mentioning `{% raw %}` | Exception message mentions `{% raw %}` and line number |
| U-012 | unit | F1-AC1 | 2.1 | Rendered output file has same permissions as source | `stat().st_mode` of src equals `stat().st_mode` of cache file |
| U-013 | unit | F1-AC1 | 2.1 | `output_dir` created if absent | Cache dir exists after `render_if_template` call |
| U-014 | unit | F1-AC1 (security) | 2.1 | `RENDERED_CACHE_DIR` created with mode `0700` | `cache_dir.stat().st_mode & 0o777 == 0o700` |
| U-015 | unit | F1-AC1 | 2.1 | Render is always performed; write skipped only when bytes identical | Second render with changed variable overwrites cache file |
| U-016 | unit | F2-AC1 | 3.1 | `parse_alternate_name` strips `.tmpl` before `##` split | `gitconfig.tmpl##os.linux` → `("gitconfig", [("os", "linux")])` |
| U-017 | unit | F2-AC1 | 3.1 | `parse_alternate_name` with no `##` returns `(base, [])` | `("gitconfig", [])` for bare `"gitconfig"` |
| U-018 | unit | F2-AC1 | 3.1 | `parse_alternate_name` with multiple conditions returns all pairs | `"gitconfig##os.darwin##hostname.work"` → two pairs |
| U-019 | unit | F2-AC1 | 3.1 | `score_candidate` returns correct score for single-condition match | `"gitconfig##os.darwin"` on darwin context → `1002` |
| U-020 | unit | F2-AC2 | 3.1 | `score_candidate` returns `None` for non-matching condition | `"gitconfig##os.linux"` on darwin context → `None` |
| U-021 | unit | F2-AC1 | 3.1 | `score_candidate` returns higher score for two matching conditions | `"gitconfig##os.darwin##hostname.work"` on darwin/work → `2034` |
| U-022 | unit | F2-AC3 | 3.1 | Bare filename scores 0 | `score_candidate("gitconfig", ctx)` → `0` |
| U-023 | unit | F2-AC3 | 3.1 | `##default` scores 0 | `score_candidate("gitconfig##default", ctx)` → `0` |
| U-024 | unit | F2-AC4 | 3.1 | Unrecognized condition key emits warning and excludes candidate | `score_candidate("gitconfig##arch.arm64", ctx)` → `None`; `logging.warning` called |
| U-025 | unit | F2-AC1 | 3.1 | `select_candidate` returns highest-scoring path | Given darwin/work machine, `##os.darwin##hostname.work` variant wins |
| U-026 | unit | F2-AC1 | 3.1 | `select_candidate` returns `None` when no candidates match | Empty result; no exception |
| U-027 | unit | F2-AC4 | 3.1 | Tied scores produce deterministic tiebreak (lex-last) with warning | Warning emitted; lex-last path returned |
| U-028 | unit | F3-AC3 | 4.1 | `##profile.work` scores `1016` when `profile="work"` | Return value is `1016` |
| U-029 | unit | F3-AC3 | 4.1 | `##profile.work` returns `None` when `profile=None` | Return value is `None` |
| U-030 | unit | F3-AC3 | 4.1 | `##profile.work` returns `None` when `profile="home"` | Return value is `None` |
| U-031 | unit | F5-DR1 | 6.1 | `run_all_checks` with one PASS + one WARN returns exit code 1 | Return value is `1` |
| U-032 | unit | F5-DR2 | 6.1 | `run_all_checks` with a FAIL returns exit code 2 | Return value is `2` |
| U-033 | unit | F5-DR2 | 6.1 | `run_all_checks` with all PASS returns exit code 0 | Return value is `0` |

### Integration Tests

| ID | Type | Requirement | Plan Story | Description | Pass Criteria |
|----|------|-------------|------------|-------------|---------------|
| I-001 | integration | F1-AC1, F1-AC3 | 1.5 | `LinkerConfig` with no profile + no `local.toml` → `local_data == {}` | `linker_config.local_data` is empty dict |
| I-002 | integration | F3-AC1 | 1.5 | `LinkerConfig(profile="work")` loads and merges `profiles/work.toml` | Profile key overrides base key in `linker_config.local_data` |
| I-003 | integration | F1-AC3 | 1.5 | Existing `test_linker.py` and `test_config.py` suites pass unchanged | `pytest tests/test_linker.py tests/test_config.py` exits 0 |
| I-004 | integration | F1-AC1, F2-AC1 | 2.2, 3.2 | File with both `##os.darwin` and `.tmpl` extension is scored, selected, then rendered (seam test) | Symlink points to rendered cache; cache path has no `.tmpl` suffix; correct OS variant selected |
| I-005 | integration | F2-AC1, F2-AC5 | 3.2 | Ignore pattern on base name also ignores all `##`-suffixed variants | `secrets.sh##os.darwin` absent from generated links when `ignore: ["secrets.sh"]` |
| I-006 | integration | F2-AC1 | 3.2 | Symlink dest uses base name, not `##`-suffixed name | `link.dest` equals `~/.gitconfig`, not `~/.gitconfig##os.darwin`; `link.src` retains `##` suffix |
| I-007 | integration | F2-AC1 | 3.2 | No match for current OS produces warning and no symlink | `logging.warning` called; no symlink at dest path |
| I-008 | integration | F2-AC1 | 3.2 | Full `Linker.create_links()` path with alternate file selection works end-to-end | Correct variant symlinked; wrong variants absent |
| I-009 | integration | F3-AC2 | 4.3 | `default_profile` in `.cfgcaddy.yml` activates profile when no `--profile` flag | Profile from YAML loads correct `profiles/<name>.toml` |
| I-010 | integration | F3-AC2 | 4.3 | Explicit `--profile home` overrides YAML `default_profile: work` | `linker_config.profile == "home"` |
| I-011 | integration | F4-AC4, F5-DC2 | 5.1 | `resolve_planned_links()` with no changes returns empty list (or all matched) without modifying any file | No filesystem modifications; returned list has no `"new"` entries |
| I-012 | integration | F4-AC4 | 5.1 | `resolve_planned_links()` assigns `"conflict"` label when dest is a regular file | Entry with `action="conflict"` in result; no `OSError` raised |
| I-013 | integration | F5-DC4 | 6.2 | `BrokenSymlinksCheck.run()` returns FAIL for broken symlink; `run(fix=True)` removes it and returns WARN | Symlink absent after fix; check level is WARN not FAIL |
| I-014 | integration | F5-DC5 | 6.2 | `SymlinkDriftCheck` returns WARN when symlink points to outdated source | `CheckResult.level == CheckLevel.WARN` |
| I-015 | integration | F5-DC3 | 6.2 | `MissingVariablesCheck` returns FAIL naming variable and template file | `CheckResult.message` contains variable name and file path |
| I-016 | integration | F5-DC3, F1-AC5 | 6.2 | `MissingLocalTomlCheck` returns WARN when `.tmpl` files exist but `local.toml` absent | `CheckResult.level == WARN`; message references `cfgcaddy secrets init` |
| I-017 | integration | F5-DC3 | 6.2 | `MissingLocalTomlCheck` returns PASS when no `.tmpl` files and no `local.toml` | `CheckResult.level == PASS` |
| I-018 | integration | F2-AC4, F5-DC6 | 6.2 | `AmbiguousAlternatesCheck` returns WARN for two candidates with equal non-None scores | `CheckResult.level == WARN`; both filenames in message |
| I-019 | integration | F1-AC4 | 6.2 | `OpCliCheck` returns WARN when `op://` in `local_data` and `op` not on PATH | `CheckResult.level == WARN` |
| I-020 | integration | F1-AC4 | 6.2 | `OpCliCheck` returns PASS when no `op://` references | `CheckResult.level == PASS` |
| I-021 | integration | F2-AC1, F5-DC6 | 6.2 | `NoUnmatchedAlternatesCheck` returns WARN on macOS when only `gitconfig##os.linux` present | `CheckResult.level == WARN`; base name `gitconfig` cited |

### CLI / End-to-End Tests (via `click.testing.CliRunner`)

| ID | Type | Requirement | Plan Story | Description | Pass Criteria |
|----|------|-------------|------------|-------------|---------------|
| C-001 | CLI | F1-AC4 | 1.4 | `cfgcaddy --profile work link` does not error on the option | Exit code 0; `LinkerConfig` receives `profile="work"` |
| C-002 | CLI | F1-AC1 | 1.4 | `cfgcaddy link` with no profile flag behaves identically to current release | Exit code unchanged; no regression in symlink output |
| C-003 | CLI | F1-AC4 | 2.3 | `cfgcaddy secrets --help` shows `init` sub-command | "init" in help output |
| C-004 | CLI | F1-AC4 | 2.3 | `cfgcaddy secrets init` prompts once per undeclared variable | Mock questionary confirms one prompt per unique variable |
| C-005 | CLI | F1-AC4 | 2.3 | `cfgcaddy secrets init` skips prompt for variable already in `local.toml` | Questionary not called for pre-existing variable |
| C-006 | CLI | F1-AC4 | 2.3 | Written `local.toml` is valid TOML parseable by `tomllib` | No parse exception after write |
| C-007 | CLI | F1-AC4 | 2.3 | `cfgcaddy secrets init` output mentions `{% raw %}` | Completion message contains `{% raw %}` |
| C-008 | CLI | F3-AC4 | 4.2 | `cfgcaddy profiles --help` shows `list` and `init` sub-commands | Both names appear in help output |
| C-009 | CLI | F3-AC4 | 4.2 | `cfgcaddy profiles list` with empty profiles dir prints "no profiles found" and exits 0 | Exit code 0; message contains "no profiles found" or equivalent |
| C-010 | CLI | F3-AC4 | 4.2 | `cfgcaddy profiles list` with two profile files prints both names | Output contains both names (without `.toml` extension) |
| C-011 | CLI | F3-AC4 | 4.2 | `cfgcaddy profiles init work` creates `profiles/work.toml` | File exists at expected path after command |
| C-012 | CLI | F3-AC4 | 4.2 | `cfgcaddy profiles init ../evil` rejected before any file I/O | Exit non-zero; no file created |
| C-013 | CLI | F4-AC1 | 5.2 | `cfgcaddy diff` exits 0 with no pending changes | Exit code 0 |
| C-014 | CLI | F4-AC1 | 5.2 | `cfgcaddy diff` exits 1 when a new link is pending | Exit code 1 |
| C-015 | CLI | F4-AC2 | 5.2 | `cfgcaddy diff` shows colored unified diff for `.tmpl` file with changed content | Output contains diff markers (`+++`, `---`) |
| C-016 | CLI | F4-AC3 | 5.2 | `cfgcaddy link --dry-run` produces same exit code as `cfgcaddy diff` | Exit codes equal; no filesystem writes |
| C-017 | CLI | F4-AC1 | 5.2 | `cfgcaddy diff` with `link.dest` as regular file exits with code indicating conflict | Exit code 2 (conflict); `[CONFLICT]` or equivalent in output |
| C-018 | CLI | F5-DC1 | 6.3 | `cfgcaddy doctor` exits 0 on clean repo | Exit code 0 |
| C-019 | CLI | F5-DC2 | 6.3 | `cfgcaddy doctor` exits 1 with only warnings | Exit code 1 |
| C-020 | CLI | F5-DC2 | 6.3 | `cfgcaddy doctor` exits 2 with any failure | Exit code 2 |
| C-021 | CLI | F5-DC4 | 6.3 | `cfgcaddy doctor --fix` repairs broken symlink and exits 1 (WARN not FAIL) | Exit code 1; symlink absent from filesystem |
| C-022 | CLI | NFR-1 | cross | `cfgcaddy link` on a repo with no `.tmpl` and no `##` files produces identical behavior to current release | Output and symlinks match pre-feature snapshot |
| C-023 | CLI | cross | cross | All 5 new commands appear in `cfgcaddy --help` | `diff`, `doctor`, `secrets`, `profiles` in help output |
| C-024 | CLI | F5-DC1 | 6.3 | `cfgcaddy doctor --help` shows `--fix` flag | `--fix` in help output |

**Test counts:** Unit: 33 | Integration: 21 | CLI: 24 | **Total: 78**

---

## 2. Requirements Coverage Matrix

The requirements document defines acceptance criteria under five features and two non-functional requirement groups. Each criterion is assigned a short ID and mapped to the test cases that cover it.

### Feature 1: Local Data File + Jinja2 Template Rendering

| Criterion ID | Criterion Text | Test IDs |
|---|---|---|
| F1-AC1 | `cfgcaddy link` renders `.tmpl` files using Jinja2 with variables from `local.toml` | U-008, U-009, U-015, I-001, I-003, I-004 |
| F1-AC2 | Missing variable raises clear error with variable name and file | U-010, I-015 |
| F1-AC3 | Non-.tmpl files are unaffected (existing behavior preserved) | U-008, I-001, I-003 |
| F1-AC4 | `cfgcaddy secrets init` wizard creates/updates `local.toml` | C-003, C-004, C-005, C-006, C-007 |
| F1-AC5 | Rendered output written to `~/.local/share/cfgcaddy/rendered/` (not committed) | U-013, U-014, I-016 |
| F1-AC6 | `local.toml` supports TOML format with nested tables | U-002, C-006 |

### Feature 2: Alternate File Scoring

| Criterion ID | Criterion Text | Test IDs |
|---|---|---|
| F2-AC1 | `cfgcaddy link` selects highest-scoring alternate file | U-019, U-021, U-025, I-005, I-006, I-007, I-008 |
| F2-AC2 | Non-matching candidates are silently ignored | U-020, I-007 |
| F2-AC3 | Files with no `##` suffix treated as `##default` (score 0); existing behavior preserved | U-022, U-023 |
| F2-AC4 | `cfgcaddy doctor` reports ambiguous tied scores | U-027, I-018 |
| F2-AC5 | `ignore` patterns apply to base name (before `##`) | I-005 |

### Feature 3: Profiles

| Criterion ID | Criterion Text | Test IDs |
|---|---|---|
| F3-AC1 | `cfgcaddy --profile work link` loads and merges `profiles/work.toml` | U-002, U-003, I-002, C-001 |
| F3-AC2 | Profile resolution order: CLI > env var > YAML `default_profile` > none | I-009, I-010, C-001 |
| F3-AC3 | `##profile.name` supported as scoring key | U-028, U-029, U-030 |
| F3-AC4 | `cfgcaddy profiles list` and `cfgcaddy profiles init` commands | C-008, C-009, C-010, C-011, C-012 |

### Feature 4: diff Command

| Criterion ID | Criterion Text | Test IDs |
|---|---|---|
| F4-AC1 | `cfgcaddy diff` exits 0 if no changes, 1 if changes exist | C-013, C-014, C-017 |
| F4-AC2 | Output clearly distinguishes link states including template content changes | C-015, I-011 |
| F4-AC3 | `cfgcaddy link --dry-run` is an alias for `cfgcaddy diff` | C-016 |
| F4-AC4 | Works correctly with alternate file scoring and profiles | I-004, I-011, I-012 |

### Feature 5: doctor Command

| Criterion ID | Criterion Text | Test IDs |
|---|---|---|
| F5-DC1 | Clear PASS/WARN/FAIL indicators per check | U-031, U-032, U-033, C-018 |
| F5-DC2 | Exit codes: 0=pass, 1=warnings, 2=failures | C-019, C-020, U-031, U-032 |
| F5-DC3 | Checks: broken symlinks, symlink drift, missing variables, `local.toml` absent | I-013, I-014, I-015, I-016, I-017 |
| F5-DC4 | `cfgcaddy doctor --fix` auto-repairs broken symlinks | I-013, C-021 |
| F5-DC5 | Checks: ambiguous alternates, `local.toml` missing, `op` CLI not installed | I-018, I-019, I-020, I-021 |
| F5-DC6 | `cfgcaddy doctor --fix` changes only what is safe to change | C-021 (confirms WARN not FAIL after fix) |

### Non-Functional Requirements

| Criterion ID | Criterion Text | Test IDs |
|---|---|---|
| NFR-1 | Zero regression: existing `cfgcaddy link` behavior unchanged | I-003, C-002, C-022 |
| NFR-2 | All new features opt-in (no `local.toml` = no templating, no `##` = no scoring) | U-001, I-001, U-022 |
| NFR-3 | Python 3.10+ compatibility; `tomllib` / `tomli` backport | U-001 (import test via Story 1.1) |
| NFR-4 | Dependencies added to `pyproject.toml` | Story 1.1 AC (manual smoke: `uv sync`) |
| NFR-5 | No new filesystem writes under `~/` during test execution | All tests use `tmp_path` or mock; assertion in CI |

**Coverage: 26 of 26 acceptance criteria covered (100%).**

---

## 3. Adversarial Review — Resolution Status

All seven attacks from the adversarial review are assessed for resolution in the plan.

| Attack | Severity | Status in Plan | Verdict |
|---|---|---|---|
| 1: `find_absences()` return shape ambiguity | Medium | Story 3.2 Task 2 now explicitly states: `Link.src` retains `##` suffix; dest uses base name. The implementation note was added. | RESOLVED |
| 2: Re-render policy ambiguous ("no write if content matches") | Medium | Story 2.1 Task 2 explicitly states: "the render call always executes, never cached … only skip the write if the bytes are identical." I-015 / U-015 test the re-render behavior. | RESOLVED |
| 3: No-match warning not user-visible | Medium | Story 3.2 Task 1 specifies `logging.warning` only. The adversarial review recommends `click.echo` with `[yellow]WARN[/]`. This is NOT explicitly addressed in plan.md. | CONCERN — see §4 |
| 4: `secrets init` conditional variable over-approximation | Low | Acceptable behavior documented; no test added for conditional template edge case. | CONCERN — see §4 |
| 5: `diff` crashes on unmanaged regular files | Medium | Story 5.1 Task 1 explicitly adds `"conflict"` action label and guards `os.readlink()` with `link.dest.is_symlink()`. C-017 / I-012 cover this. | RESOLVED |
| 6a: `.tmpl` + `##` combo not integration-tested | Medium | Integration test I-004 covers this seam end-to-end. | RESOLVED |
| 6b: diff needs render-without-write path | Medium | Story 5.2 Task 2 calls `show_link_diff(..., renderer: TemplateRenderer)` and explicitly says "without writing to cache." A `render_to_string` method is implied. No Story 2.1 update explicitly adds `render_to_string`. | CONCERN — see §4 |
| 7a: Ignore pattern test not marked security-critical | Low | Test I-005 covers the invariant but the plan does not require the `# SECURITY INVARIANT` comment annotation. | MINOR GAP |
| 7b: Profile path containment guard not tested | Low-Med | U-007 tests the path containment check separately from the regex. | RESOLVED |
| 7c: `RENDERED_CACHE_DIR` mode `0700` not tested | Low-Med | U-014 tests mode `0700` on dir creation. | RESOLVED |

---

## 4. Risks and Gaps

### CONCERN-1: No-match warning visibility (Attack 3 — unresolved)

**What:** Story 3.2 Task 1 specifies `logging.warning` for the no-match case. The adversarial review recommends a user-visible `click.echo` or Rich warning. The plan text was not updated.

**Risk:** A user with only `gitconfig##os.darwin` who runs cfgcaddy on Linux will see no symlink created and no visible output (Python logging is silent at default verbosity). For a git config, this is a confusing failure mode with no actionable message.

**Mitigation before implementation:** Add an explicit note to Story 3.2 Task 1 that the no-match case emits a user-visible warning via `click.echo` or Rich in addition to `logging.warning`. Alternatively, the doctor command's `NoUnmatchedAlternatesCheck` partially covers this post-hoc — but it requires a separate command invocation.

**Testability:** Testable (CLI output assertion in I-007). This gap is a plan spec issue, not a test gap.

---

### CONCERN-2: `render_to_string` method not explicitly specified in Story 2.1 (Attack 6b — partially resolved)

**What:** Story 5.2 Task 2 requires generating a diff "without writing to cache." This requires `TemplateRenderer` to support a render-only-to-string path. Story 2.1 does not explicitly add a `render_to_string(src: Path) -> str` method.

**Risk:** The developer implementing Epic 5 either (a) calls `render_if_template()` which writes to cache — violating `--dry-run` semantics — or (b) duplicates rendering logic inline in the diff command.

**Mitigation before implementation:** Add `render_to_string(src: Path) -> str` to Story 2.1's acceptance criteria. Add one test case to `tests/test_template.py`: calling `render_to_string` does not create or modify any file on disk.

**Testability:** Testable. Gap is in plan completeness, not test design.

---

### CONCERN-3: `secrets init` conditional variable over-approximation (Attack 4 — undocumented)

**What:** `jinja2.meta.find_undeclared_variables()` surfaces variables in false conditional branches. The wizard will prompt for platform-specific variables that don't apply to the current machine. This is harmless but unexpected.

**Risk:** Low. Extra variables in `local.toml` cause no errors (`StrictUndefined` only fires at render time on variables actually referenced). Users may be confused by prompts for `mac_secret` on a Linux machine.

**Mitigation:** Add one test case to `tests/test_data.py` (or a note in `tests/test_template.py`) documenting this behavior explicitly. Mark it as "by design" so future developers don't try to "fix" it by changing to lazy-evaluation discovery, which would introduce under-collection risk.

**Testability:** Testable (call secrets init with conditional template; verify prompt count = all variables including false-branch variables).

---

### MINOR GAP: Security invariant test comment not annotated

**What:** Test I-005 (ignore pattern on base name ignores `##` variants) covers a security invariant identified in ADR-004. The plan does not require the `# SECURITY INVARIANT: do not remove without explicit sign-off` comment annotation.

**Risk:** Negligible. The test exists. Without the annotation, a future refactor could remove it without recognizing the security significance.

**Mitigation:** Add the annotation comment when writing the test. No plan update required.

---

### CANNOT-AUTOMATE-1: `cfgcaddy link` output byte-for-byte identical to current release

**What:** Requirement NFR-1 (zero regression) is best validated by a golden-output snapshot test against the real existing release. Test C-022 provides a functional regression guard but not a byte-exact comparison.

**Mitigation:** Add a snapshot test using `pytest-snapshot` or a recorded expected-output file. Acceptable to defer to manual verification before the PR is merged.

---

### CANNOT-AUTOMATE-2: `uv sync` and import smoke tests for new dependencies

**What:** Story 1.1 requires `uv sync` to complete and specific Python imports to succeed. These are CI/environment assertions, not pytest unit tests.

**Mitigation:** Include in CI pipeline (`uv sync && python -c "import jinja2, rich, tomli_w"`) as a pre-test step. Not testable via pytest alone.

---

### CANNOT-AUTOMATE-3: `CFGCADDY_PROFILE` environment variable resolution order

**What:** Requirement F3-AC2 includes env var `CFGCADDY_PROFILE` as the second priority in profile resolution. The plan wires this via `click.option(..., envvar="CFGCADDY_PROFILE")`. CliRunner tests can set env vars, so this IS testable — but no explicit test case is defined in the current table.

**Mitigation:** Add C-025: `CliRunner(env={"CFGCADDY_PROFILE": "work"})` invokes `link` and confirms `profile="work"` is active when no `--profile` flag is passed.

---

## 5. Implementation Readiness Gate

### Gate Check Results

#### a. Requirements Coverage

Every acceptance criterion in `requirements.md` has at least one test case.

- Feature 1: 6 criteria — 6 covered
- Feature 2: 5 criteria — 5 covered
- Feature 3: 4 criteria — 4 covered
- Feature 4: 4 criteria — 4 covered
- Feature 5: 6 criteria — 6 covered
- NFR: 5 criteria — 5 covered (2 require CI pipeline assertions)

**Result: 26/26 (100%). PASS.**

---

#### b. Plan Completeness — Stories with Named Test Files

Every story in `plan.md` that requires new tests names a `tests/test_*.py` file:

| Story | Named test file | Status |
|---|---|---|
| 1.3 | `tests/test_data.py` | Named |
| 2.1 | `tests/test_template.py` | Named |
| 2.2 | No new test file (relies on `test_linker.py` regression guard) | Acceptable — regression guard is explicit |
| 2.3 | No dedicated file named | GAP — should name `tests/test_secrets.py` |
| 3.1 | `tests/test_alternate.py` | Named |
| 3.2 | `tests/test_linker.py` (additions) | Named |
| 4.1 | `tests/test_alternate.py` (additions) | Named |
| 4.2 | `tests/test_profiles.py` | Named |
| 4.3 | No dedicated test file named | MINOR GAP — `default_profile` coverage should be in `tests/test_config.py` |
| 5.1 | `tests/test_diff.py` | Named |
| 5.2 | `tests/test_diff.py` | Named |
| 6.1 | `tests/test_doctor.py` | Named |
| 6.2 | `tests/test_doctor.py` | Named |
| 6.3 | `tests/test_doctor.py` | Named |

**Result: 12/14 stories explicitly name test files. 2 minor gaps (Stories 2.3 and 4.3). CONCERNS (non-blocking).**

---

#### c. Adversarial Review Items — All Resolved?

| Attack | Blocker? | Resolved in Plan? |
|---|---|---|
| 1 — `find_absences()` return shape | No | YES |
| 2 — Re-render policy | No | YES |
| 3 — No-match warning visibility | No | NO (CONCERN) |
| 4 — Conditional variable over-approximation | No | DOCUMENTED (acceptable, undocumented in plan) |
| 5 — Diff unmanaged file crash | No | YES |
| 6a — `.tmpl` + `##` integration test | No | YES (I-004) |
| 6b — render-without-write path | No | PARTIALLY (implied but not explicit in Story 2.1) |
| 7a — Security invariant annotation | No | MINOR GAP |
| 7b — Profile path containment guard | No | YES (U-007) |
| 7c — Cache dir mode `0700` | No | YES (U-014) |

No items were marked BLOCKED in the adversarial review. All three Medium-severity concerns are either resolved or remain as non-blocking CONCERNS.

**Result: 7/10 fully resolved; 3 unresolved non-blockers. CONCERNS.**

---

#### d. Ambiguity Check — All Acceptance Criteria Automatically Testable?

Reviewing all 26 acceptance criteria:

- All Feature 1–5 criteria are testable via `tmp_path`, mocking, and CliRunner.
- `CFGCADDY_PROFILE` env var (F3-AC2) is testable via CliRunner `env=` parameter — a test case was omitted from the initial table (see CANNOT-AUTOMATE-3 for the fix).
- `uv sync` and Python import smoke tests (NFR-3, NFR-4) require CI pipeline steps, not pytest. These are infrastructure-level assertions, not logic assertions. They are identified and bounded.
- "byte-for-byte identical output" (NFR-1) requires a snapshot baseline. Identified above.

**Result: 24/26 criteria testable automatically; 2 require CI pipeline steps. CONCERNS (bounded and identified).**

---

### Gate Verdict: CONCERNS

**Not FAIL** — no criterion is untestable, no adversarial item was BLOCKED, and all critical paths have test coverage.

**CONCERNS (must be addressed before or during Story implementation):**

1. **CONCERN-1:** Story 3.2 no-match warning must be user-visible (`click.echo` or Rich), not buried in `logging.warning`. Requires a one-line plan update to Story 3.2 Task 1.

2. **CONCERN-2:** `TemplateRenderer.render_to_string(src: Path) -> str` must be explicitly added to Story 2.1 acceptance criteria before Epic 5 implementation begins, to prevent `--dry-run` from writing to cache.

3. **CONCERN-3 (minor):** Story 2.3 and Story 4.3 should name explicit test files (`tests/test_secrets.py` and `tests/test_config.py` additions respectively) for traceability.

4. **CONCERN-4 (minor):** Add test case C-025 for `CFGCADDY_PROFILE` env var resolution order (F3-AC2 currently has no dedicated env var test).

**None of the above concerns block implementation of Epics 1–2.** Epics 3–6 should not begin until CONCERN-1 and CONCERN-2 are resolved in plan.md.

---

## 6. Test File Summary

| File | Owned by Stories | Test IDs |
|---|---|---|
| `tests/test_data.py` | 1.3 | U-001 through U-007, I-001, I-002 |
| `tests/test_template.py` | 2.1 | U-008 through U-015 |
| `tests/test_linker.py` | 1.5, 2.2, 3.2 (additions) | I-003, I-004, I-005, I-006, I-007, I-008 |
| `tests/test_alternate.py` | 3.1, 4.1 | U-016 through U-030 |
| `tests/test_config.py` | 4.3 (additions) | I-009, I-010 |
| `tests/test_profiles.py` | 4.2 | C-008 through C-012 |
| `tests/test_secrets.py` | 2.3 (to be named) | C-003 through C-007 |
| `tests/test_diff.py` | 5.1, 5.2 | I-011, I-012, C-013 through C-017 |
| `tests/test_doctor.py` | 6.1, 6.2, 6.3 | U-031 through U-033, I-013 through I-021, C-018 through C-024 |
