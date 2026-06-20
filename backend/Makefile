.PHONY: fixtures
.SILENT: clean

COMPOSE := docker compose -f docker-compose.yml
COMPOSE_API := docker compose -f docker-compose.yml run --rm api
COMPOSE_ADMIN := docker compose -f docker-compose.yml run --rm admin
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

setup_assets:
	mc alias set doxiq_local http://localhost:9000 minioadmin minioadmin
  	# Crear bucket
	mc mb doxiq_local/doxiq-ws
	# Configurar Permisos
	mc anonymous set public doxiq_local/doxiq-ws
	mc anonymous set download doxiq_local/doxiq-ws
	mc anonymous set upload doxiq_local/doxiq-ws
	# Verificar Configuración
	mc anonymous get doxiq_local/doxiq-ws
	mc ls doxiq_local/doxiq-ws/

perms_assets:
	mc alias set doxiq_local http://localhost:9000 minioadmin minioadmin

	mc anonymous set public doxiq_local/doxiq-ws
	mc anonymous set download doxiq_local/doxiq-ws
	#mc anonymous set upload doxiq_local/doxiq-ws
	# Verificar Configuración
	mc anonymous get doxiq_local/doxiq-ws
	mc ls doxiq_local/doxiq-ws/

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

# domain: https://vnext-assets.codemia.dev
tunnel_assets:
	cloudflared tunnel token 8887c0c8-c2f4-45fd-bc71-7913857b06f3 | xargs -I{} cloudflared tunnel run --token {}


# Directus Custom Modules Commands
admin_install:
	@echo "Installing Directus extension dependencies..."
	cd admin/extensions/payouts && npm install

admin_build:
	@echo "Building Directus custom modules..."
	cd admin/extensions/payouts && npm run build

admin_build_dev:
	@echo "Building Directus custom modules for DEVELOPMENT..."
	cp admin/extensions/payouts/.env.dev admin/extensions/payouts/.env
	cd admin/extensions/payouts && npm run build
	@echo "✅ Built with DEVELOPMENT environment"

admin_build_prod:
	@echo "Building Directus custom modules for PRODUCTION..."
	cp admin/extensions/payouts/.env.prod admin/extensions/payouts/.env
	cd admin/extensions/payouts && npm run build
	@echo "✅ Built with PRODUCTION environment"

admin_clean:
	@echo "Cleaning Directus build artifacts..."
	rm -rf admin/extensions/payouts/dist
	rm -rf admin/extensions/payouts/node_modules

admin_rebuild: admin_clean admin_install admin_build
	@echo "Rebuild completed!"

admin_rebuild_dev: admin_clean admin_install admin_build_dev
	@echo "Development rebuild completed!"

admin_rebuild_prod: admin_clean admin_install admin_build_prod
	@echo "Production rebuild completed!"

admin_watch:
	@echo "Watching Directus custom modules for changes..."
	cp admin/extensions/payouts/.env.dev admin/extensions/payouts/.env
	cd admin/extensions/payouts && npm run dev

# Docker builds with custom image (includes extensions in image)
admin_docker_build_dev:
	@echo "Building custom Directus image for DEVELOPMENT..."
	make admin_build_dev
	docker compose -f docker-compose.yml build admin

admin_docker_build_prod:
	@echo "Building custom Directus image for PRODUCTION..."
	make admin_build_prod
	docker compose -f docker-compose.admin-custom.yml build

admin_docker_up_custom:
	@echo "Starting Directus with custom image..."
	docker compose -f docker-compose.admin-custom.yml up -d

admin_docker_down_custom:
	@echo "Stopping Directus custom image..."
	docker compose -f docker-compose.admin-custom.yml down

