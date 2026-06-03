.PHONY: push pull ready lint ansible-lint shellcheck llm-sync

BOOTSTRAP_FILES := $(shell find bootstrap -name '*.yml') bootstrap/.ansible-lint
SHELL_FILES     := install.sh bootstrap/run.sh

# Sentinel files track last successful lint run so make skips if nothing changed
.cache/ansible-lint.ok: $(BOOTSTRAP_FILES)
	@command -v ansible-lint >/dev/null 2>&1 || brew install ansible-lint
	cd bootstrap && ansible-lint
	@mkdir -p .cache && touch $@

.cache/shellcheck.ok: $(SHELL_FILES)
	@command -v shellcheck >/dev/null 2>&1 || brew install shellcheck
	shellcheck $(SHELL_FILES)
	@mkdir -p .cache && touch $@

# Named targets for convenience
ansible-lint: .cache/ansible-lint.ok
shellcheck:   .cache/shellcheck.ok

# Run all checks — use this before pushing
ready: .cache/ansible-lint.ok .cache/shellcheck.ok
	@echo "All checks passed."

lint: ready

push: ready
	git push

pull:
	git pull

llm-sync:
	uv run --directory stapler-scripts/llm-sync main.py
