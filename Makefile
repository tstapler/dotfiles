.PHONY: push pull ready lint ansible-lint shellcheck llm-sync run

BOOTSTRAP_FILES := $(shell find bootstrap -name '*.yml') bootstrap/.ansible-lint bootstrap/hosts
SHELL_FILES     := install.sh bootstrap/run.sh

# Sentinel files track last successful lint run so make skips if nothing changed
.cache/ansible-lint.ok: $(BOOTSTRAP_FILES)
	cd bootstrap && uvx ansible-lint@26.4.0 playbook.yml
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

run: ready
	./bootstrap/run.sh

push: ready
	git push

pull:
	git pull

llm-sync:
	uv run --directory stapler-scripts/llm-sync main.py
