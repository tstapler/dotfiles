.PHONY: push pull ready lint ansible-lint shellcheck llm-sync run pyinfra-lint pyinfra-dry lint-skills test-lint-skills

BOOTSTRAP_FILES := $(shell find bootstrap -name '*.yml') bootstrap/.ansible-lint bootstrap/hosts
SHELL_FILES     := install.sh bootstrap/run.sh
PYINFRA_FILES   := $(shell find bootstrap-pyinfra -name '*.py' -not -path '*/.venv/*')

# Sentinel files track last successful lint run so make skips if nothing changed
.cache/ansible-lint.ok: $(BOOTSTRAP_FILES)
	cd bootstrap && uvx ansible-lint@26.4.0 playbook.yml
	@mkdir -p .cache && touch $@

.cache/shellcheck.ok: $(SHELL_FILES)
	@command -v shellcheck >/dev/null 2>&1 || brew install shellcheck
	shellcheck $(SHELL_FILES)
	@mkdir -p .cache && touch $@

.cache/pyinfra-lint.ok: $(PYINFRA_FILES)
	cd bootstrap-pyinfra && uv run ruff check . && uv run ruff format --check . && uv run mypy .
	@mkdir -p .cache && touch $@

# Named targets for convenience
ansible-lint: .cache/ansible-lint.ok
shellcheck:   .cache/shellcheck.ok
pyinfra-lint: .cache/pyinfra-lint.ok

# No sentinel — always live, since it reflects this machine's actual current state
pyinfra-dry:
	cd bootstrap-pyinfra && uv run pyinfra -y inventory.py main.py --dry

# Deterministic lint for .claude/skills, agents, commands — frontmatter name/dirname
# drift and dangling `X` skill cross-references (see the script's module docstring
# for the check list). NOT yet in `ready`: there's existing findings to triage first.
lint-skills:
	./stapler-scripts/lint-claude-kb

# Unit tests for the linter itself, against synthetic fixtures — not the live repo.
test-lint-skills:
	python3 stapler-scripts/test_lint_claude_kb.py

# Run all checks — use this before pushing
ready: .cache/ansible-lint.ok .cache/shellcheck.ok .cache/pyinfra-lint.ok
	@echo "All checks passed."

lint: ready

run: ready
	./bootstrap/run.sh

push: ready
	git push

pull:
	git pull

llm-sync:
	uv run --directory stapler-scripts/llm-sync main.py
