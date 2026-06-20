# Llamitai Development Commands
# Ports: backend=8200, frontend=8080

set dotenv-load := false

# List available commands
default:
    @just --list

# ─── ALL PROJECTS ───────────────────────────────────────────────

# Start all projects in parallel (logs interleaved)
dev-all:
    (cd backend && docker compose up) & (cd frontend && pnpm dev) & wait

# Build all projects
build-all: build-backend build-frontend

# ─── BACKEND — port 8200 ───────────────────────────────────────

# Start backend with docker-compose (API + Postgres + Redis)
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

# Run backend tests in the api container (optional path filter: just test-backend tests/auth)
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

# ─── DOCKER (production) ────────────────────────────────────────

# Build production backend image
build-prod:
    cd backend && docker compose -f docker-compose.prod.yml build

# Start production backend
up-prod:
    cd backend && docker compose -f docker-compose.prod.yml up -d

# ─── SEEDS ───────────────────────────────────────────────────────
# Run after migrate-backend.
# All seeded users share the password 12345678x; canonical login: team@owliver.com.

# Seed tenants, users and tenant-user memberships
seed-users:
    cd backend && docker compose run --rm api python scripts/seed_users.py

# ─── UTILITIES ───────────────────────────────────────────────────

# Stop all running containers
stop-all:
    cd backend && docker compose down 2>/dev/null; \
    echo "All containers stopped"

# Clean all stopped containers and dangling images
clean:
    docker system prune -f

# Show running containers
ps:
    docker ps --format "table {{{{.Names}}}}\t{{{{.Ports}}}}\t{{{{.Status}}}}"
