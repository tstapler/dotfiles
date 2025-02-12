.PHONY: all clean build run stop logs

GATEWAY_IP := $(shell ip route | grep default | awk '{print $$3}' 2>/dev/null || echo "192.168.1.1")
CONTAINER_NAME := vaping-at-home-vaping-1
PYTHON_FILES := pyproject.toml requirements.lock

all: run

config.yaml: config.yaml.template
	sed 's/$${GATEWAY_IP}/$(GATEWAY_IP)/g' $< > $@

build: config.yaml Dockerfile $(PYTHON_FILES)
	docker compose build

run: build
	docker compose up -d

stop:
	docker compose down

logs:
	docker logs -f $(CONTAINER_NAME)

clean:
	rm -f config.yaml
	docker compose down --rmi all --volumes
