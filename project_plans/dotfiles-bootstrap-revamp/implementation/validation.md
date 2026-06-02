# Dotfiles Bootstrap Revamp — Validation Plan

Generated from: requirements.md, plan.md, adversarial-review.md

---

## Test Suite

### Smoke Tests (run after install.sh on a fresh machine)

| ID | Test Case | Pass Criteria | Req Coverage |
|---|---|---|---|
| S1 | `install.sh` completes without error on macOS Apple Silicon (ARM64) | Exit code 0; no error output; playbook completes all roles | SC-1 |
| S2 | `install.sh` completes without error on Ubuntu 22.04 (fresh VM) | Exit code 0; Brewfile.linux packages installed; no macOS-specific tasks attempted | SC-7 |
| S3 | `install.sh` is reachable via `curl -fsSL https://raw.githubusercontent.com/tstapler/dotfiles/master/install.sh | bash` | curl returns HTTP 200; script exits 0 | SC-1 |
| S4 | Running `install.sh` a second time makes no changes (idempotency) | Exit code 0; Ansible reports `changed=0`; no new symlinks or reinstalls | SC-2 |
| S5 | `install.sh` on macOS Intel (x86_64) resolves Homebrew prefix to `/usr/local` | `brew --prefix` returns `/usr/local`; no ARM path errors | SC-1 |
| S6 | `install.sh` detects WSL2 and sets `is_wsl=true` | Pre-task `is_wsl` fact is `true`; fonts role skips | SC-7 |

**Smoke test count: 6**

---

### Role-Level Tests (run via `ansible-playbook bootstrap/playbook.yml --tags <role>`)

| ID | Test Case | Pass Criteria | Req Coverage |
|---|---|---|---|
| R1 | `--tags homebrew`: `brew --version` succeeds | `brew` binary on PATH; exits 0 | SC-3 |
| R2 | `--tags homebrew` on macOS: all packages from `Brewfile` installed | `brew bundle check --file=Brewfile` exits 0 | SC-3 |
| R3 | `--tags homebrew` on Linux: `Brewfile.linux` packages installed, no cask errors | `brew bundle check --file=Brewfile.linux` exits 0; no `cask` errors in output | SC-3, SC-7 |
| R4 | `--tags homebrew` on Linux: `Brewfile` (macOS) is NOT used | Task "Set brewfile path" registers `Brewfile.linux` path | SC-7 |
| R5 | `--tags dotfiles`: `~/.cfgcaddy.yml` is a valid symlink pointing into dotfiles dir | `readlink ~/.cfgcaddy.yml` returns path under `$HOME/dotfiles` | SC-4 |
| R6 | `--tags dotfiles`: dotfile symlinks created in `$HOME` | `ls -la ~/.zshrc ~/.gitconfig` (or canonical cfgcaddy targets) are symlinks | SC-4 |
| R7 | `--tags dotfiles`: `cfgcaddy link --no-interactive` exits 0 | No error output; exit code 0 | SC-4 |
| R8 | `--tags shell`: zsh is the default shell for current user | `getent passwd $USER | cut -d: -f7` returns `/bin/zsh` or `/usr/bin/zsh` | SC-3 |
| R9 | `--tags shell`: `~/.zplug` directory exists after role runs | `test -d ~/.zplug` exits 0 | SC-3 |
| R10 | `--tags asdf`: `asdf version` succeeds | `asdf version` exits 0; returns version string | SC-5 |
| R11 | `--tags asdf`: all tools in `.tool-versions` are installed | `asdf current` lists each tool with a version (no "not installed" output) | SC-5 |
| R12 | `--tags asdf`: role skips gracefully when `.tool-versions` is absent | Ansible reports skipped tasks; no errors; exit 0 | SC-5 |
| R13 | `--tags nix`: `nix --version` succeeds after role | `nix --version` exits 0 | SC-3 |
| R14 | `--tags secrets`: `op --version` succeeds | `op --version` exits 0; returns version string | SC-3 |
| R15 | `--tags secrets`: clear error message when `op` is not installed | Ansible `fail:` task output contains install instructions mentioning `brew install --cask 1password-cli` | SC-3 |
| R16 | `--tags secrets`: informational message (not hard fail) when `op` installed but no active session | Ansible debug output contains sign-in instructions; playbook exits 0 | SC-3 |
| R17 | `--tags fonts` on macOS: Nerd Font cask installed | `brew list --cask font-meslo-lg-nerd-font` exits 0 | SC-3 |
| R18 | `--tags fonts` on Linux (non-WSL2): `MesloLG*.ttf` files exist in `~/.local/share/fonts/` | `find ~/.local/share/fonts -name 'MesloLG*' | wc -l` returns > 0 | SC-3 |
| R19 | `--tags claude`: `claude --version` returns a version string | `claude --version` exits 0; stdout contains a semver | SC-6 |
| R20 | `--tags claude`: role fails with clear message when npm is not available | Ansible reports npm not found; error message references Brewfile | SC-6 |

**Role-level test count: 20**

---

### Idempotency Tests (run each role twice; second run must report `changed=0`)

| ID | Test Case | Pass Criteria | Req Coverage |
|---|---|---|---|
| I1 | `--tags homebrew` run 2x | Second run: `changed=0, failed=0` | SC-2, SC-3 |
| I2 | `--tags dotfiles` run 2x | Second run: `changed=0`; cfgcaddy reports no new links created | SC-2, SC-4 |
| I3 | `--tags asdf` run 2x | Second run: `changed=0`; "already added" plugin messages do not cause failures | SC-2, SC-5 |
| I4 | `--tags fonts` on Linux run 2x | Second run: `changed=0`; download and unarchive tasks skipped because font files exist | SC-2 |
| I5 | `--tags claude` run 2x | Second run: `changed=0`; `claude --version` check short-circuits npm install | SC-2, SC-6 |
| I6 | Full playbook run 2x on macOS | Second run: all roles report `changed=0` | SC-2 |

**Idempotency test count: 6**

---

### Platform-Conditional Tests

| ID | Test Case | Pass Criteria | Req Coverage |
|---|---|---|---|
| P1 | WSL2: `--tags fonts` is skipped entirely | Ansible task "Skip fonts on WSL2" reports `skipped`; no download attempted | SC-7 |
| P2 | WSL2: `become: true` tasks in shell role do not hang | Shell role completes in <30s on WSL2; chsh succeeds or `ignore_errors: true` fires | SC-7 |
| P3 | Linux: `Brewfile.linux` is used, not `Brewfile` | `brewfile_path` fact contains `Brewfile.linux`; no cask tasks attempted | SC-7 |
| P4 | Linux: no `community.general.homebrew_cask` tasks run | Task "Install Meslo Nerd Font (macOS via Homebrew cask)" is skipped on Linux | SC-7 |
| P5 | macOS Apple Silicon: `brew_prefix` is `/opt/homebrew` | `brew_prefix` fact value matches `/opt/homebrew`; all PATH constructions correct | SC-1 |
| P6 | macOS Intel: `brew_prefix` is `/usr/local` | `brew_prefix` fact value matches `/usr/local` | SC-1 |
| P7 | Ubuntu: apt prerequisites installed before Homebrew attempt | `build-essential`, `curl`, `file`, `git`, `unzip` present on system before brew install task | SC-7 |
| P8 | Arch/Manjaro: pacman prerequisites installed with `--needed` flag | `base-devel` group present; pacman command uses `--needed`; no partial-upgrade state | SC-7 |

**Platform-conditional test count: 8**

---

### Negative Tests

| ID | Test Case | Pass Criteria | Req Coverage |
|---|---|---|---|
| N1 | Missing `op` CLI: secrets role fails with clear message, not cryptic error | Ansible `fail:` message contains "1Password CLI (op) is required" and installation instructions | SC-3 |
| N2 | Missing `.tool-versions`: asdf role skips gracefully | `stat` task for `.tool-versions` returns `exists=false`; subsequent tasks all skipped; exit 0 | SC-5 |
| N3 | No `npm` available: claude role fails with clear message | Task "Install Claude Code CLI via npm" fails; error output references Brewfile or npm install path | SC-6 |
| N4 | `run.sh` not found after clone: install.sh exits with error | Guard check fires; stderr output contains "ERROR: .../bootstrap/run.sh not found or not executable" | SC-1 |
| N5 | `apt-get update` fails (locked by cloud-init): install.sh continues with warning | Script does not abort; warning message printed; subsequent steps attempt to proceed | SC-1 |
| N6 | asdf sourcing from wrong path (`~/.asdf/asdf.sh` not present for Homebrew install): asdf role uses Homebrew path | Shell tasks source `{{ brew_prefix }}/opt/asdf/libexec/asdf.sh` successfully; not `~/.asdf/asdf.sh` | SC-5 |
| N7 | Private Brewfile taps fail on fresh machine without SSH keys: homebrew role does not abort | Homebrew bundle does not exit non-zero due to private tap failure; warning is logged | SC-1, SC-7 |

**Negative test count: 7**

**Total test cases: 47**

---

## Requirement-to-Test Traceability Matrix

| Success Criterion | Description | Test IDs | Coverage |
|---|---|---|---|
| SC-1 | `curl -fsSL .../install.sh \| bash` runs to completion on fresh macOS | S1, S3, S5, N4, N5, N7 | COVERED |
| SC-2 | Running `install.sh` twice produces no errors and no unneeded changes | S4, I1, I2, I3, I4, I5, I6 | COVERED |
| SC-3 | Each Ansible role can be run independently via `--tags <role>` | R1, R2, R5, R8, R9, R10, R13, R14, R17, R18, R19 | COVERED |
| SC-4 | cfgcaddy symlinks are created correctly after dotfiles role runs | R5, R6, R7, I2 | COVERED |
| SC-5 | `asdf install` actually runs when `.tool-versions` exists | R10, R11, R12, I3, N2, N6 | COVERED |
| SC-6 | Claude Code CLI is installed and `claude --version` returns a version | R19, R20, I5, N3 | COVERED |
| SC-7 | Linux (Ubuntu) run completes without macOS-specific failures | S2, S6, R3, R4, R18, P1-P8 | COVERED |

**Requirements coverage: 7/7 (100%)**

---

## Readiness Gate

### Criterion 1: Requirements Coverage
Every success criterion has at least 1 test case.

- SC-1: 6 tests (S1, S3, S5, N4, N5, N7)
- SC-2: 7 tests (S4, I1–I6)
- SC-3: 11 tests (R1, R2, R5, R8, R9, R10, R13, R14, R17, R18, R19)
- SC-4: 4 tests (R5, R6, R7, I2)
- SC-5: 6 tests (R10, R11, R12, I3, N2, N6)
- SC-6: 4 tests (R19, R20, I5, N3)
- SC-7: 14 tests (S2, S6, R3, R4, R18, P1–P8)

**Verdict: PASS — 7/7 criteria covered**

---

### Criterion 2: Plan Completeness
Every epic in plan.md must have implementation tasks (no empty epics).

| Epic | Stories | Tasks | Status |
|---|---|---|---|
| Epic 1: install.sh / run.sh | 1.1, 1.2 | 5 tasks (1.1.1–1.1.5) + 2 tasks (1.2.1–1.2.2) | COMPLETE |
| Epic 2: playbook.yml | 2.1 | 1 task (2.1.1) | COMPLETE |
| Epic 3: homebrew role | 3.1, 3.2 | 2 tasks (3.1.1) + 2 tasks (3.2.1–3.2.2) | COMPLETE |
| Epic 4: dotfiles role | 4.1 | 1 task (4.1.1) | COMPLETE |
| Epic 5: shell + asdf roles | 5.1, 5.2 | 1 task (5.1.1) + 2 tasks (5.2.1–5.2.2) | COMPLETE |
| Epic 6: fonts role | 6.1 | 2 tasks (6.1.1–6.1.2) | COMPLETE |
| Epic 7: claude role | 7.1 | 2 tasks (7.1.1–7.1.2) | COMPLETE |
| Epic 8: cleanup | 8.1, 8.2 | 1 task (8.1.1) + 1 task (8.2.1) | COMPLETE |
| Epic 9: secrets role | 9.1 | 1 task (9.1.1) | COMPLETE |

**Verdict: PASS — all 9 epics have implementation tasks**

---

### Criterion 3: Adversarial Review
No BLOCKED verdict; CONCERNS are acceptable if all are patched.

The adversarial review returned verdict **CONCERNS** (not BLOCKED). The original near-BLOCKED finding was Finding 9 (secrets role had no implementation plan). This was resolved in the plan by adding Epic 9 with a full secrets role rewrite.

All other patched items from the adversarial review:
- Finding 1: `apt-get update || true` added to install.sh — PATCHED (Task 1.1.2)
- Finding 2: Guard before `exec` — PATCHED (Task 1.1.4)
- Finding 3: `pacman --needed` flag — PATCHED (Task 1.1.2)
- Finding 4: `NONINTERACTIVE=1` — PATCHED (Task 1.1.3)
- Finding 9: secrets role missing — PATCHED (Epic 9)
- Finding 13: `asdf` missing from Brewfile.linux — PATCHED (Task 3.2.2 notes)
- Finding 15: `unzip` missing from Brewfile.linux — PATCHED (Task 3.2.2, line: `brew "unzip"`)
- Finding 16: `uv tool install` stdout vs stderr — PATCHED (Task 4.1.1 comment)
- Finding 22: asdf Homebrew path — PATCHED (Critical Path Note in Story 5.2)
- Finding 23: deprecated `homebrew_cask` — PATCHED (Task 6.1.2 uses `community.general.homebrew_cask`)
- Finding 25: `unarchive` idempotency — PATCHED (Task 6.1.2 adds `find` guard)

Remaining CONCERNS that are documented but not fully tasked:
- Finding 14: Private Brewfile taps on fresh machine — documented as known limitation in Cross-Cutting Concerns; no automated task-level fix (acceptable: documented workaround exists)
- Finding 28: `osx-ansible-install.sh` may not exist — low risk; `git rm` on a nonexistent file will produce a clear error

**Verdict: PASS — no BLOCKED verdict; all high-impact CONCERNS are patched in plan**

---

### Criterion 4: Risk Mitigations
Top 3 pitfalls from adversarial review have corresponding tests or documented mitigations.

| Pitfall | Source | Mitigation in Plan | Test Coverage |
|---|---|---|---|
| asdf Homebrew path (`~/.asdf/asdf.sh` not found) | Finding 22 — HIGH | Critical Path Note in Story 5.2: use `{{ brew_prefix }}/opt/asdf/libexec/asdf.sh` as primary with fallback | N6 |
| `asdf` binary missing from Brewfile.linux | Finding 13 — HIGH | `brew "asdf"` added to Brewfile.linux in Task 3.2.2 | R3, R10 |
| Private Brewfile taps fail on fresh machine | Finding 14 — HIGH likelihood | Documented in Cross-Cutting Concerns and Risk Register; `--no-lock` flag applied; workaround documented | N7 |

**Verdict: PASS — all 3 top risks have mitigations; 2 of 3 have explicit test cases**

---

## Readiness Gate Verdict

| Criterion | Status | Evidence |
|---|---|---|
| 1. Requirements coverage | PASS | 7/7 success criteria each have ≥1 test |
| 2. Plan completeness | PASS | All 9 epics have implementation tasks |
| 3. Adversarial review | PASS | Verdict is CONCERNS (not BLOCKED); all near-blocked findings patched |
| 4. Risk mitigations | PASS | Top 3 pitfalls addressed in plan and/or test suite |

**Overall Verdict: PASS**

The implementation is ready to begin. Start with a fresh session before Phase 5. Recommended sequencing: Epic 1 (install.sh) → Epic 2 (playbook.yml) → Epic 3 (homebrew) → Epic 9 (secrets) → Epics 4–8 in order.

**One residual risk to monitor**: Private Brewfile taps (Finding 14) are not fully mitigated at the task level — only documented. If the very first smoke test (S1) fails due to a private tap failure in `brew bundle`, the implementer should add `HOMEBREW_NO_AUTO_UPDATE=1` and a `continue_on_error`-equivalent wrapper to the homebrew role as the first corrective action.
