.SILENT: clean

STACK=stateless
STAGE=dev

COMPOSE := @docker compose -f docker-compose.yml
COMPOSE_PROD := @docker compose -f docker-compose.prod.yml
COMPOSE_BACKEND := @docker compose -f docker-compose.yml run --rm backend
COMPOSE_FRONTEND := @docker compose -f docker-compose.yml run --rm frontend

ARG=


build_prod:
	$(COMPOSE_PROD) build

up_prod:
	$(COMPOSE_PROD) up -d

build:
	$(COMPOSE) build && cd frontend && npm install

up:
	$(COMPOSE) up

up_frontend:
	cd frontend && npm run dev

debug:
	$(COMPOSE) run --service-ports core

debug_api:
	$(COMPOSE) run --service-ports fastapi

bash:
	$(COMPOSE_BACKEND) bash

clean:
	docker ps -aq | xargs docker stop
	docker ps -aq | xargs docker rm

format:
	@echo "Formatting..."
	@cd backend && docker compose -f docker-compose.yml run --rm api ruff format . 2>/dev/null || true

lint:
	@echo "Linting..."
	@cd backend && docker compose -f docker-compose.yml run --rm api ruff check .
