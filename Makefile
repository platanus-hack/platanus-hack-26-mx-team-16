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

bash_dev:
	$(COMPOSE_CORE)_dev bash

try_process:
	$(COMPOSE_CORE) python run_cli.py -f "raw-images/CC-standard.tif"

lock:
	$(COMPOSE_CORE) poetry lock

clean:
	docker ps -aq | xargs docker stop
	docker ps -aq | xargs docker rm

publish:
	$(COMPOSE_CORE) bash build.sh

build_api:
	docker build -f Dockerfile --platform=linux/amd64 --target fastapi -t documente-core-api .


format:
	@echo "Formatting..."
	@cd backend && docker compose -f docker-compose.yml run --rm api ruff format . 2>/dev/null || true

lint:
	@echo "Linting..."
	@$(COMPOSE_CORE) ruff check .
