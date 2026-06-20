# Llamitai Development Commands
# Ports: backend=8200, frontend=8080, docs=4321

set dotenv-load := false

# List available commands
default:
    @just --list

# ─── ALL PROJECTS ───────────────────────────────────────────────

# Start all projects in parallel (logs interleaved)
dev-all:
    (cd backend && docker compose up) & (cd frontend && pnpm dev) & (cd docs && pnpm dev) & wait

# Build all projects
build-all: build-backend build-frontend build-docs

# ─── BACKEND — port 8200 ───────────────────────────────────────

# Start backend with docker-compose (API + Postgres + Redis + Temporal)
dev-backend:
    cd backend && docker compose up

# Start backend in detached mode
dev-backend-d:
    cd backend && docker compose up -d

# Build backend docker images
build-backend:
    cd backend && docker compose build

# Run backend API locally (without docker, requires postgres/redis running)
dev-backend-local:
    cd backend && uvicorn config.main:app --host 0.0.0.0 --port 8200 --reload

# Run backend worker (Temporal) locally — loads backend/.env and overrides TEMPORAL_HOST for out-of-docker execution
dev-backend-worker:
    cd backend && TEMPORAL_HOST=localhost:7233 uv run --env-file .env python run_worker.py

# Tail logs of the dockerized Temporal worker
logs-backend-worker:
    cd backend && docker compose logs -f temporal-worker

# Open bash in backend container
bash-backend:
    cd backend && docker compose run --rm api bash

# Run backend migrations
migrate-backend:
    cd backend && docker compose run --rm api alembic upgrade head

# Create a new migration
migrate-backend-new name:
    cd backend && docker compose run --rm api alembic revision --autogenerate -m "{{name}}"

# Show current migration revision
migrate-backend-current:
    cd backend && docker compose run --rm api alembic current

# Revert last migration (use steps=N to revert N migrations)
migrate-backend-down steps="1":
    cd backend && docker compose run --rm api alembic downgrade -{{steps}}

# Run backend tests in the api container (optional path filter: just test-backend tests/workflows)
test-backend path="tests":
    cd backend && docker compose run --rm api python -m pytest {{path}} -v

# Stop backend containers
stop-backend:
    cd backend && docker compose down

# Backend logs
logs-backend:
    cd backend && docker compose logs -f api

# ─── FRONTEND — port 8080 ───────────────────────────────────────

# Start frontend dev server
dev-frontend:
    cd frontend && pnpm dev

# Build frontend for production
build-frontend:
    cd frontend && pnpm build

# Install frontend dependencies
install-frontend:
    cd frontend && pnpm install

# Run frontend tests
test-frontend:
    cd frontend && pnpm test

# Lint frontend
lint-frontend:
    cd frontend && pnpm lint

# Run frontend e2e tests with Cypress (headless)
e2e:
    cd frontend && pnpm exec cypress run --browser chrome

# Open Cypress UI for interactive e2e testing
e2e-open:
    cd frontend && pnpm exec cypress open

# Run e2e tests with visible browser
e2e-headed:
    cd frontend && pnpm exec cypress run --headed --browser chrome

# Run a specific e2e spec (e.g. just e2e-spec 01-landing.cy.ts)
e2e-spec spec:
    cd frontend && pnpm exec cypress run --spec "cypress/e2e/{{spec}}" --browser chrome

# ─── DOCS — port 4321 ───────────────────────────────────────────

# Start docs dev server (Astro)
dev-docs:
    cd docs && pnpm dev

# Start docs dev server in docker (live reload)
dev-docs-d:
    cd docs && docker compose -f docker-compose.dev.yml up

# Build docs for production
build-docs:
    cd docs && pnpm build

# Preview the production build locally
preview-docs:
    cd docs && pnpm preview

# Install docs dependencies
install-docs:
    cd docs && pnpm install

# Lint docs
lint-docs:
    cd docs && pnpm lint

# Format docs
format-docs:
    cd docs && pnpm format

# Build the production docs docker image
build-docs-image:
    cd docs && docker compose build

# Start the production docs container (detached)
up-docs:
    cd docs && docker compose up -d

# Stop the production docs container
stop-docs:
    cd docs && docker compose down

# Tail docs container logs
logs-docs:
    cd docs && docker compose logs -f

# Open a shell in the docs container
bash-docs:
    cd docs && docker compose run --rm docs sh

# Re-build & re-start the production docs container
rebuild-docs:
    cd docs && docker compose down && docker compose build && docker compose up -d

# ─── DOCKER (production) ────────────────────────────────────────

# Build production backend image
build-prod:
    cd backend && docker compose -f docker-compose.prod.yml build

# Start production backend
up-prod:
    cd backend && docker compose -f docker-compose.prod.yml up -d

# ─── SEEDS ───────────────────────────────────────────────────────
# Run after migrate-backend. Order matters: common (config) -> users -> workflows.
# All seeded users share the password 12345678x; canonical login: team@llamitai.com.

# Seed everything (industries, tenants/users, workflows) in order
seed: seed-common seed-users seed-workflows

# Seed the industry catalog / global config
seed-common:
    cd backend && docker compose run --rm api python scripts/seed_common.py

# Seed tenants, users and tenant-user memberships
seed-users:
    cd backend && docker compose run --rm api python scripts/seed_users.py

# Seed test workflows (pipeline + document types + rules)
seed-workflows:
    cd backend && docker compose run --rm api python scripts/seed_workflows.py

# ─── MINIO ───────────────────────────────────────────────────────

# Set public read access on the tenants/ prefix in the doxiq-dev bucket
minio-set-public bucket="doxiq-dev":
    docker run --rm --network backend_default --entrypoint /bin/sh minio/mc \
        -c "mc alias set local http://minio:9000 minioadmin minioadmin && mc anonymous set download local/{{bucket}}/tenants"

# ─── UTILITIES ───────────────────────────────────────────────────

# Stop all running containers
stop-all:
    cd backend && docker compose down 2>/dev/null; \
    cd docs && docker compose -f docker-compose.yml down 2>/dev/null; \
    cd docs && docker compose -f docker-compose.dev.yml down 2>/dev/null; \
    echo "All containers stopped"

# Clean all stopped containers and dangling images
clean:
    docker system prune -f

# Show running containers
ps:
    docker ps --format "table {{{{.Names}}}}\t{{{{.Ports}}}}\t{{{{.Status}}}}"

# ─── WEBHOOK DEBUG — port 5000 ──────────────────────────────────

# Run the webhook debug server locally on :5000 (prints every request, returns 200 OK)
webhook-debug port="5000":
    PORT={{port}} python3 tools/webhook_server.py

# Run the webhook debug server and expose it via a Cloudflare quick tunnel (public https URL)
webhook-tunnel port="5000":
    #!/usr/bin/env bash
    set -euo pipefail
    command -v cloudflared >/dev/null || { echo "cloudflared not found — install with: brew install cloudflared"; exit 1; }
    echo "Starting webhook debug server on :{{port}}..."
    PORT={{port}} python3 tools/webhook_server.py &
    server_pid=$!
    trap 'echo; echo "Stopping webhook debug server..."; kill "$server_pid" 2>/dev/null || true' EXIT INT TERM
    sleep 1
    echo "Opening Cloudflare tunnel → http://localhost:{{port}} (public URL printed below)"
    cloudflared tunnel --url "http://localhost:{{port}}"
