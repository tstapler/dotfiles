.PHONY: up down logs clean test btrfs-health

test:
	cd host && uv run --no-project --with pytest --with pyyaml pytest tests/ -q

btrfs-health:
	cd host && uv run --no-project --with pyyaml python3 btrfs_health.py

COMPOSE := $(shell if command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; else echo "docker compose"; fi)

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

clean:
	$(COMPOSE) down --rmi all --volumes
