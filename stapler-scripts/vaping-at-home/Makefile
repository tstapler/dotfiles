.PHONY: all clean build run up stop logs debug shell wifi-metrics

PYTHON_FILES := pyproject.toml requirements.lock prometheus_plugin.py dns_probe.py command_plugin.py fping_mtr_plugin.py
COMPOSE := $(shell if command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; else echo "docker compose"; fi)

all: run

config.yaml: config.yaml.template net_discovery.py generate_config.py
	python3 generate_config.py

build: config.yaml Dockerfile $(PYTHON_FILES)
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
