.PHONY: all clean build run stop logs debug

GATEWAY_IP := $(shell python3 get_gateway.py)
CONTAINER_NAME := vaping-at-home-vaping-1
PYTHON_FILES := pyproject.toml requirements.lock prometheus_plugin.py

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
	docker logs -f $(CONTAINER_NAME)

debug: build
	docker compose up

shell: build
	docker compose exec vaping /bin/bash

clean:
	rm -f config.yaml
	docker compose down --rmi all --volumes
