.PHONY: all clean build run up stop logs debug shell wifi-metrics btrfs-health test

PYTHON_FILES := pyproject.toml requirements.lock prometheus_plugin.py dns_probe.py command_plugin.py fping_mtr_plugin.py
COMPOSE := $(shell if command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; else echo "docker compose"; fi)

all: run

config.yaml: config.yaml.template net_discovery.py generate_config.py
	python3 generate_config.py

TARGETS_SRC := $(if $(filter Darwin,$(shell uname -s)),macos,linux)

# Re-copied every run so a stale file from another OS can't survive a checkout swap.
.PHONY: prometheus_targets.d/node-exporter.yml
prometheus_targets.d/node-exporter.yml:
	cp prometheus_targets.d/node-exporter.$(TARGETS_SRC).yml.dist $@

btrfs-health:
	uv run --no-project --with pyyaml python3 btrfs_health.py

test:
	uv run --no-project --with pytest --with pyyaml pytest tests/ -q

build: config.yaml prometheus_targets.d/node-exporter.yml Dockerfile $(PYTHON_FILES)
	$(COMPOSE) build

run: build
	$(COMPOSE) up -d

up: build run

stop:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f vaping

debug: build
	$(COMPOSE) up

shell: build
	$(COMPOSE) exec vaping /bin/bash

wifi-metrics:
	python3 wifi_signal_exporter.py

clean:
	rm -f config.yaml
	$(COMPOSE) down --rmi all --volumes
