# Adversarial Review: cfgcaddy Feature Expansion

**Reviewer:** Adversarial pre-implementation review  
**Date:** 2026-06-02  
**Verdict:** CONCERNS

No fatal flaws that make the plan unimplementable, but three issues are significant enough to require explicit remediation before or during implementation.

---

## Attack 1: Zero-Breakage Claim

**Finding: CONCERN — one code path change in `find_absences()` is under-specified and could regress.**

Story 3.2 modifies `cfgcaddy/link.py`'s `find_absences()` to add base-name extraction before pathspec matching. The task description says "replace the raw `ignored.match_file(path.join(rel_path, f))` check for files with a two-step." However, the plan also says `find_absences()` is responsible for constructing the `Link` dest path when `f` contains `##`, using the base name as the destination.

The risk: `find_absences()` currently returns file paths that feed into `Linker.create_links()`. The plan does NOT clarify whether `find_absences()` returns the `##`-suffixed filename (the actual disk name, needed for reading the source) or the base name (needed for the dest symlink). If the wrong name is returned, the Linker either (a) tries to open a file that doesn't exist, or (b) creates a symlink with the `##` suffix in HOME.

The acceptance criteria in Story 3.2 confirms the symlink must use the base name (`~/.gitconfig`, not `~/.gitconfig##os.darwin`), but the plan does not explicitly state whether `find_absences()` is modified to return a `(src_full_path, dest_base_name)` tuple or whether that mapping happens downstream. This ambiguity is a regression trap — whoever implements this without reading ADR-004 carefully may get it wrong.

**Recommended fix:** Add an explicit implementation note to Story 3.2 Task 2 specifying the return shape of `find_absences()` after modification — whether it returns `(src_path_with_##, dest_base_path)` tuples or the current flat list with a new companion function.

---

## Attack 2: Template Cache Coherence

**Finding: CONCERN — re-render policy is unspecified in the plan; stale cache is a real risk.**

ADR-001 and the pitfalls research both identify stale cache as a problem and recommend "always re-render on every `cfgcaddy link` run." However, Story 2.1 Task 2 says the function is "idempotent reads are OK, no write if content matches" — implying a check-before-write optimization — but never specifies WHAT triggers a re-render.

The plan is silent on the invalidation policy:
- Story 2.1 does not say "always re-render every template on every `link` run."
- Story 2.2 does not call out re-render policy.
- No story mentions what happens when `local.toml` changes between two `cfgcaddy link` runs — does the stale rendered file get overwritten?

The pitfalls research explicitly warns: "If `cfgcaddy link` only renders when the cached file doesn't exist, the following changes produce stale content: `local.toml` values change, source `.tmpl` file changes, profile changes."

The "no write if content matches" optimization in Story 2.1 is fine as a write optimization (skip the atomic rename if bytes are identical), but only if rendering always happens first. If someone reads "no write if content matches" as "skip rendering entirely if cache file exists," the stale cache problem is reintroduced.

**Race condition:** There is no explicit guard against a concurrent `cfgcaddy link` run. Two processes could both render the same template to a temp file and race on `os.rename`. `os.rename` is atomic on POSIX (last writer wins), so this is not a corruption risk, but it is worth noting.

**Recommended fix:** Add a single explicit sentence to Story 2.1 Task 2 acceptance criteria: "Rendering is performed on every invocation; the 'no write if content matches' optimization skips the atomic rename but does NOT skip calling `template.render()`." This makes the intent unambiguous.

---

## Attack 3: Scoring Algorithm Completeness — No-Match Behavior

**Finding: CONCERN (near-BLOCKED for UX) — behavior when zero candidates match is inconsistently specified across plan vs. ADR.**

The plan (Story 3.2 Task 1 acceptance criteria) says: "a repo with no `##` files is unaffected" — which is fine. But it specifies the no-match case for `##`-only repos as: "skip groups where the result is `None` with a `logging.warning`."

ADR-003 specifies something stronger: "no file is linked and a WARNING is emitted." It also says `cfgcaddy doctor` flags this as WARN. The NoUnmatchedAlternatesCheck in Story 6.2 Task 7 covers this in doctor.

The problem: Story 3.2 uses `logging.warning` (Python logger, not visible to users by default unless log level is configured). The user who has ONLY `gitconfig##os.darwin` and runs cfgcaddy on Linux will see no symlink created and NO visible output unless they have debug logging enabled. The plan does not use `click.echo` or Rich output for this warning in `generate_links()` — it buries it in the Python logging system.

For a security-adjacent scenario (secrets file with `##os.darwin` only, user on Linux), silent non-linking is actually correct behavior. But for a configuration scenario (`gitconfig##os.darwin` only, user on Linux has no git config), the silent skip will be confusing with no actionable message.

**Recommended fix:** In Story 3.2 Task 1, change the no-match warning from `logging.warning` to a `click.echo` or Rich `console.print` with a `[yellow]WARN[/]` prefix so it is user-visible at normal verbosity. The doctor check handles deep auditing; the link command should surface the warning immediately.

---

## Attack 4: `secrets init` Wizard Variable Discovery

**Finding: CONCERN — conditional variables are under-specified.**

Story 2.3 Task 2 says the wizard: "collects all `{{ variable_name }}` references using `jinja2.Environment().parse()`."

The Jinja2 AST walker (`env.parse()` + walking `jinja2.meta.find_undeclared_variables()`) returns all variable names referenced in the template, INCLUDING those inside conditionals that will never execute on this machine. Example:

```jinja2
{% if os == "darwin" %}
export MAC_ONLY_VAR={{ mac_secret }}
{% endif %}
```

On Linux, `mac_secret` is an undeclared variable that `find_undeclared_variables()` will surface. The wizard will prompt for `mac_secret` even though the rendered output on Linux never uses it. This is a usability problem (prompting for irrelevant variables) but not a correctness problem — having extra variables in `local.toml` is harmless since `StrictUndefined` only fires on variables that ARE referenced in the rendered branch.

However, the inverse case is the real problem: a variable only used in a conditional that IS true for this machine might not be caught if the AST walk misses it. Jinja2's `find_undeclared_variables()` is thorough — it finds all references including those in false branches — so undercollection is not a risk. Overcollection (prompting for unused vars) is the only issue.

The plan's acceptance criteria ("prompts exactly once for `github_token`") only covers the simple case. There is no test coverage for conditional templates and no mention of this edge case.

**Recommended fix:** Add a note to Story 2.3 Task 2 that `find_undeclared_variables()` over-approximates (surfaces vars in false branches) and that this is acceptable behavior. Add one test case in the acceptance criteria: a template with a conditional block covering a platform-specific variable prompts for that variable even if the current machine is not the target platform.

---

## Attack 5: `diff` Command — Unmanaged Files

**Finding: CONCERN — the diff command has no explicit handling for manually-created destination files.**

Story 5.2 Task 2 specifies that for template links, the diff shows "the current symlink target content" vs freshly rendered content. Story 5.1 Task 1 says `resolve_planned_links()` returns `"changed"` for symlinks pointing to a different target.

The unaddressed case: the destination path exists as a REGULAR FILE (not a symlink) — the user created `~/.gitconfig` manually before installing cfgcaddy. In this case:
- `link.dest` exists and is a regular file (not a symlink)
- `os.readlink()` will raise `OSError: [Errno 22] Invalid argument`
- The current `action_label` enumeration does not include `"manual"` or `"conflict"` as a state

The plan's Story 5.2 action labels are `"new"`, `"changed"`, `"broken"`, `"content_changed"` — no label covers "destination exists but is not managed by cfgcaddy." The diff command will either crash (if `os.readlink()` is called without a guard) or silently misclassify the file as `"new"` (if the existence check uses `os.path.islink()` and falls through to the new-link path).

The requirements spec says `cfgcaddy diff` should show "new symlinks that would be created, existing symlinks that point to a different target, broken symlinks that would be repaired, template content changes" — it does not mention the unmanaged regular file case, suggesting it is unintentionally omitted.

**Recommended fix:** Add a `"conflict"` action label to `resolve_planned_links()` for the case where `link.dest` exists but is not a symlink. The diff command should display these prominently (e.g., red `[CONFLICT]` — would overwrite a non-symlink file) and exit with code 2 rather than 1. This prevents `cfgcaddy link` (when `--dry-run` aliases to diff) from misleading users into thinking their manually-created config is already managed.

---

## Attack 6: Epic Ordering — Hidden Dependencies

**Finding: CONCERNS — two integration pain points between epics.**

**6a. Epic 2 (templates) and Epic 3 (alternates) interact but are tested separately.**

Story 2.2 integrates `TemplateRenderer` into `generate_links()`. Story 3.2 integrates `AlternateSelector` into `generate_links()`. Both modify the same loop over `src_files`. The plan specifies them as sequential stories, but the acceptance criteria for Story 2.2 ("All existing `test_linker.py` tests continue passing") and Story 3.2 ("New tests pass; all existing tests continue to pass") do not include any integration test for a file that has BOTH a `##` suffix AND a `.tmpl` extension.

ADR-003 and pitfalls research both identify the `.tmpl` + `##` combination (e.g., `gitconfig##os.darwin.tmpl`) and require: strip `.tmpl` first, then parse `##` for scoring, then apply template rendering to the winner. The plan describes this in `parse_alternate_name` (Story 3.1 Task 2) but no story creates an end-to-end test of the full path: file is scored via `##`, selected, passed to `TemplateRenderer`, rendered, and symlinked.

**6b. Epic 5 (diff) depends on Epic 2 and 3 being complete, but its interface assumes their internal representations.**

Story 5.2 Task 2 calls `show_link_diff(..., renderer: TemplateRenderer)` and generates a diff against "freshly rendered content (without writing to cache)." This requires `TemplateRenderer` to support a render-without-write mode, which is not specified in Story 2.1. If Epic 5 is developed after Epic 2 is "done," the developer will need to retrofit a read-only render path, or the diff command will have a side effect (writing to cache) that violates the `--dry-run` semantic.

**Recommended fix for 6a:** Add one integration test to Story 3.2 (or a new Story 3.3) that covers `gitconfig##os.darwin.tmpl` end-to-end.

**Recommended fix for 6b:** Add a `render_to_string(src: Path) -> str` method (no filesystem write) to `TemplateRenderer` in Story 2.1 and list it explicitly in the acceptance criteria. Story 5.2 should call this method rather than `render_if_template()`.

---

## Attack 7: Missing Security-Critical Test Scenarios

**Finding: CONCERN — three paths lack explicit test coverage requirements.**

**7a. Ignore pattern stripping security invariant (Epic 3)**

Story 3.2 Task 3 says: "Add tests to `test_linker.py` covering: ignore pattern on exact base name ignores all `##` variants." This is listed but as a single bullet among several. Given that ADR-004 explicitly calls this a security invariant and pitfalls research classifies it as the second-highest risk, the test requirement should be marked security-critical with a note that REMOVING this test in a future refactor is prohibited without a deliberate decision.

The current framing buries it alongside functional tests. No test is labeled to signal its security significance.

**7b. Profile path traversal (Epic 1)**

Story 1.3 Task 3 covers `validate_profile_name` rejecting path-traversal names. This is good. However, there is no test that verifies the SECOND guard — the `resolve()` check that verifies the constructed path stays within `PROFILES_DIR`. The regex check alone is sufficient to block `../` sequences, but the belt-and-suspenders path resolution check could have an off-by-one error (e.g., a profile named `a` resolving to `PROFILES_DIR/a.toml` correctly, but a symlink-based PROFILES_DIR attack not being caught). The test coverage only exercises the regex path, not the `startswith` path containment guard.

**7c. Rendered file permissions (Epic 2)**

Story 2.1 Task 4 requires testing "rendered output has same permissions as source." But there is no test requirement for the rendered DIRECTORY being created with `0700` mode. A test that verifies `RENDERED_CACHE_DIR` is created with `0700` (not the default `0755`) is missing from the plan. This is a data-security requirement stated in ADR-001 but not reflected in the test plan.

**Recommended fix:** Add explicit test cases for:
- `RENDERED_CACHE_DIR` created with mode `0700` when it doesn't exist
- Profile path containment guard (create a PROFILES_DIR that is itself a symlink pointing elsewhere, verify the guard catches it)
- Tag the `ignore: ["secrets.sh"]` ignores `secrets.sh##os.darwin` test case with a comment: `# SECURITY INVARIANT: do not remove without explicit sign-off`

---

## Summary

| # | Angel | Severity | Blocker? |
|---|-------|----------|----------|
| 1 | Zero-breakage: `find_absences()` return shape ambiguity | Medium | No — but likely to cause a regression during implementation |
| 2 | Cache coherence: re-render policy ambiguous | Medium | No — but "no write if content matches" phrasing will be misread |
| 3 | No-match behavior: warning not user-visible | Medium | No — but creates silent UX failure on new machines |
| 4 | `secrets init`: conditional variable over-approximation | Low | No — correct behavior, just undocumented |
| 5 | `diff`: unmanaged regular file case unhandled | Medium | No — but causes a crash or misleading output |
| 6a | Epic ordering: `.tmpl` + `##` combo not integration-tested | Medium | No — but guarantees a bug in the seam |
| 6b | Epic ordering: diff needs render-without-write path | Medium | No — but retrofitting will be painful |
| 7 | Missing security-critical test cases | Low-Medium | No — but reduces confidence in the security invariants |

**Top 3 issues:**

1. **Diff command crashes on unmanaged regular files (Attack 5).** `resolve_planned_links()` has no `"conflict"` state for `link.dest` existing as a regular file. `os.readlink()` will raise or the state will be silently misclassified. Fix: add `"conflict"` label and guard before the `os.readlink()` call.

2. **Re-render policy is ambiguous (Attack 2).** The phrase "no write if content matches" in Story 2.1 Task 2 can be read as "skip rendering entirely if cache exists." This must be tightened to "always render, skip the write if bytes are identical" to prevent stale cache.

3. **`find_absences()` return shape is unspecified after modification (Attack 1).** Story 3.2 modifies `find_absences()` to use base names for both pathspec matching and dest-path construction, but the return type after modification is not stated. This is the highest-probability regression during implementation.
