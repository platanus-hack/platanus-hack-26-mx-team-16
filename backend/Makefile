.PHONY: fixtures
.SILENT: clean

COMPOSE := docker compose -f docker-compose.yml
COMPOSE_API := docker compose -f docker-compose.yml run --rm api
COMPOSE_PROD := docker compose -f docker-compose.prod.yml

ARG=

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up

prod_up:
	$(COMPOSE_PROD) up

prod_build:
	$(COMPOSE_PROD) build

bash:
	$(COMPOSE_API) bash

debug:
	$(COMPOSE) run --service-ports api

debugpy:
	docker compose -f docker-compose.yml -f docker-compose.debug.yml up

clean:
	@echo "Cleaning containers ..."
	docker ps -aq | xargs docker stop
	docker ps -aq | xargs docker rm

clean_volumes:
	@echo "Cleaning volumes ..."
	$(COMPOSE) down -v --remove-orphans
	docker images | grep "^<none>" | awk '{print $$3}' | xargs docker rmi 2>/dev/null || true

stop:
	@echo "Stopping containers"
	docker ps -qa | xargs docker stop

test:
	$(COMPOSE_API) bash -c "pytest --pyargs -m 'not api and not llm' $(ARG)"

test_single:
	$(COMPOSE_API) bash -c "pytest --pyargs -m single"

test_llm:
	$(COMPOSE_API) bash -c "pytest --pyargs -m llm $(ARG)"

test_all:
	$(COMPOSE) up -d
	@echo "Esperando a que el servicio esté listo..."
	@while ! curl -s http://localhost:8200; do echo "Esperando al servicio..."; sleep 1; done
	@echo "Servicio listo, corriendo TODAS las pruebas (unit + api + llm)..."
	$(COMPOSE_API) bash -c "pytest --pyargs $(ARG)"
	$(COMPOSE) down

test_api:
	$(COMPOSE) up -d
	@echo "Esperando a que el servicio esté listo..."
	@while ! curl -s http://localhost:8200; do echo "Esperando al servicio..."; sleep 1; done
	@echo "Servicio listo, corriendo las pruebas API..."
	$(COMPOSE_API) bash -c "pytest -m api --pyargs $(ARG)"
	$(COMPOSE) down

format:
	@echo "Formatting..."
	@$(COMPOSE_API) ruff format .


unused:
	@echo "Check unused code"
	@$(COMPOSE_API) vulture .

lint:
	@echo "Linting..."
	@$(COMPOSE_API) ruff check . --fix

tycheck:
	@echo "Type checking with ty..."
	@$(COMPOSE_API) uv run ty check

code_quality: format lint tycheck
	@echo "Running quality checks..."

migrations:
	@echo "Creating new migration..."
	$(COMPOSE_API) alembic revision --autogenerate -m "$(ARG)"

migrate:
	@echo "Applying migrations..."
	$(COMPOSE_API) alembic upgrade head

downgrade:
	@echo "Downgrading migration..."
	$(COMPOSE_API) alembic downgrade -1

db_history:
	@echo "Showing migration history..."
	$(COMPOSE_API) alembic history

db_current:
	@echo "Showing current migration..."
	$(COMPOSE_API) alembic current

# domain: https://doxiq-ws.codemia.dev
tunnel:
	cloudflared tunnel token ca7c7ef6-856c-4c2f-9d35-3830bd58f796 | xargs -I{} cloudflared tunnel run --token {}

