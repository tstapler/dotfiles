push:
	git push
pull:
	git pull

.PHONY: vaping-start vaping-stop vaping-clean

VAPING_DIR=stapler-scripts/vaping-at-home
GATEWAY_IP := $(shell ip route | grep default | awk '{print $$3}')

vaping-config: $(VAPING_DIR)/config.yaml.template
	cd $(VAPING_DIR) && sed 's/$${GATEWAY_IP}/$(GATEWAY_IP)/g' config.yaml.template > config.yaml

vaping-start: vaping-config
	cd $(VAPING_DIR) && docker compose up -d

vaping-stop:
	cd $(VAPING_DIR) && docker compose down

vaping-clean:
	cd $(VAPING_DIR) && rm -f config.yaml
	cd $(VAPING_DIR) && docker compose down --rmi all --volumes
