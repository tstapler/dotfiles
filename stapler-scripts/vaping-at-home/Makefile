.PHONY: all clean build run up stop logs debug shell

PYTHON_FILES := pyproject.toml requirements.lock prometheus_plugin.py
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

clean:
	rm -f config.yaml
	$(COMPOSE) down --rmi all --volumes
