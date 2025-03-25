.PHONY: all clean build run stop logs debug

GATEWAY_IP := $(shell python3 get_gateway.py)
CONTAINER_NAME := vaping-at-home-vaping-1
PYTHON_FILES := pyproject.toml requirements.lock prometheus_plugin.py
COMPOSE := $(shell if command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; else echo "docker compose"; fi)

all: run

config.yaml: config.yaml.template
	sed 's/$${GATEWAY_IP}/$(GATEWAY_IP)/g' $< > $@

build:  Dockerfile $(PYTHON_FILES)
	docker compose build

run: build config.yaml
	docker compose up -d

up: build run

stop:
	docker compose down

logs:
	$(COMPOSE) logs -f vaping

debug: build
	$(COMPOSE) up

shell: build
	docker compose exec vaping /bin/bash

clean:
	rm -f config.yaml
	$(COMPOSE) down --rmi all --volumes
