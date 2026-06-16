# ADR-004: Ignore Pattern Matching on Base Name
Status: Accepted
Date: 2026-06-15

## Context

cfgcaddy's `.cfgcaddy.yml` supports an `ignore` list of gitignore-style glob patterns. The existing implementation uses `pathspec.PathSpec.from_lines("gitwildmatch", ...)` to filter files before linking. Patterns like `secrets.sh` or `*.op.sh` prevent sensitive files from being symlinked to HOME.

Feature 2 introduces `##`-suffixed alternate filenames. Under gitignore glob rules, `##` is a literal character — it changes the filename that pathspec sees. Testing confirms:

| Pattern | Filename | Matches? |
|---------|----------|----------|
| `secrets.sh` | `secrets.sh##os.darwin` | **No** |
| `*.yml` | `config.yml##os.darwin` | **No** |
| `secrets*` | `secrets.sh##os.linux` | Yes |
| `secrets.sh` | `secrets.sh##os.linux` | **No** |

An exact-name ignore pattern for `secrets.sh` will not match `secrets.sh##os.linux`. Without a fix, any user who has secrets files protected by exact-name ignore patterns will find those files silently linked to HOME after upgrading to the `##` feature — a security regression.

This is classified as the second-highest risk in the pitfalls research, behind only the Jinja2 `StrictUndefined` issue.

## Decision

Before applying pathspec ignore pattern matching, strip the `##` suffix from each candidate filename to extract the base name:

```python
base_name = f.split("##")[0] if "##" in f else f
base_rel = os.path.join(rel_path, base_name)
if ignored.match_file(base_rel):
    continue  # skip this ## variant
```

The implementation detail is: split on `##` and take index 0. This is correct for all valid `##`-suffixed filenames:

- `secrets.sh##os.darwin` → base `secrets.sh`
- `gitconfig##os.darwin##hostname.work-laptop` → base `gitconfig`
- `config.yml##default` → base `config.yml`
- `secrets.sh` (no `##`) → base `secrets.sh` (unchanged)

The pathspec check then uses the base name against the ignore patterns. If the base name matches an ignore pattern, the candidate is skipped regardless of its `##` suffix.

This logic is applied in `find_absences()` (or its equivalent in the new implementation) at the point where files are filtered before scoring.

## Alternatives Considered

**Require users to update ignore patterns to use wildcards**
Rejected. This is a breaking change to existing configurations. Users who have `ignore: ["secrets.sh", "*.op.sh"]` would need to update every pattern to `secrets.sh*` or `secrets*`. This is an invisible migration hazard — users who don't read the changelog would silently expose their secrets files. The base-name stripping approach requires zero user action.

**Apply ignore patterns to both the base name and the full `##`-suffixed name**
Considered but rejected. Checking both is redundant — if the base name matches, the file should be ignored. Checking the full name first would mean exact patterns never match `##` variants (reproducing the bug). The correct semantic is: ignore patterns are defined against the logical file name, which is the base name before `##` suffixes.

**Expand the gitignore pattern set automatically (e.g., append `##*` variants)**
Rejected. Auto-expanding `secrets.sh` to `secrets.sh` and `secrets.sh##*` would work but adds complexity to the pattern management layer. The base-name extraction is simpler and has the same effect.

**Document the behavior and let users add `##`-aware patterns**
Rejected. The security consequence of the default behavior is too severe. A dotfile manager that silently links secrets files because the user upgraded and didn't read the changelog is unacceptable. The safe default must be that existing ignore patterns continue to protect existing files and all their `##` variants.

## Consequences

**Positive:**
- Existing `.cfgcaddy.yml` ignore patterns continue to work correctly after the `##` feature is introduced — zero configuration migration required.
- `ignore: ["secrets.sh"]` protects `secrets.sh`, `secrets.sh##os.darwin`, `secrets.sh##hostname.work-laptop`, and all other variants.
- Security regression is avoided: sensitive files are not silently linked to HOME.

**Negative:**
- There is no way to ignore a `##` variant while keeping the base file. For example, a user cannot write an ignore pattern that skips `gitconfig##os.windows` but keeps `gitconfig`. This edge case is unusual and can be addressed in a future feature if needed (e.g., an explicit `##`-aware ignore syntax).

**Implementation notes:**
- The split is `f.split("##")[0]` — always take the first segment. Do not use `rsplit` or strip from the end, as that would break filenames like `my##weird##file.txt` where the base is `my`.
- This logic must be applied before the pathspec match, not after. Filtering first, then scoring, is the correct order.

**Test requirements (required, not optional):**
- `ignore: ["secrets.sh"]` must ignore `secrets.sh##os.darwin`. This test case must be explicit and named to document the security invariant.
- `ignore: ["*.yml"]` must ignore `config.yml##default`.
- `ignore: ["secrets.sh"]` must NOT ignore `other-secrets.sh` (verify no over-matching).
- Bare `secrets.sh` (no `##`) continues to be ignored by `ignore: ["secrets.sh"]`.
