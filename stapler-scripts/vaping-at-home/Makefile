.PHONY: all clean build run stop config

GATEWAY_IP := $(shell ip route | grep default | awk '{print $$3}')

all: config build run

config: config.yaml.template
	sed 's/$${GATEWAY_IP}/$(GATEWAY_IP)/g' config.yaml.template > config.yaml

build:
	docker compose build

run:
	docker compose up -d

stop:
	docker compose down

clean:
	rm -f config.yaml
	docker compose down --rmi all --volumes
