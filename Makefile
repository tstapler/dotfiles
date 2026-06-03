.PHONY: push pull lint ansible-lint shellcheck llm-sync

push:
	git push
pull:
	git pull

# Run all local linters (mirrors CI)
lint: ansible-lint shellcheck

ansible-lint:
	cd bootstrap && ansible-lint

shellcheck:
	shellcheck install.sh bootstrap/run.sh

llm-sync:
	uv run --directory stapler-scripts/llm-sync main.py
