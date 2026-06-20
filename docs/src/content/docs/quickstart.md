---
title: Quickstart
description: Get Doxiq running locally in 5 minutes.
sidebar:
  label: Quickstart
  order: 2
---

This guide gets the entire Doxiq stack (backend, frontend, worker, postgres) running on your machine using Docker.

## Prerequisites

- Docker 24+ and Docker Compose v2
- A Git checkout of the `doxiq` repository
- A `.env` file at the repo root (copy from `.env.example`)

## 1. Start the backend

```bash
just dev-backend
```

This boots PostgreSQL, the FastAPI API on `:8200`, and the Temporal worker.

## 2. Start the frontend

In a new terminal:

```bash
just dev-frontend
```

Next.js runs on `:3000` and talks to the backend through the BFF (`src/app/api/**/route.ts`).

## 3. Start the docs

```bash
cd docs
pnpm install
pnpm dev
```

Astro runs on `:4321`. Sign in with your Doxiq backend credentials.

## 4. Verify

```bash
curl http://localhost:8200/health
# {"status":"ok"}
```

Open `http://localhost:3000` and upload a test document from `fixtures/`.

## Common commands

| Command | What it does |
|---|---|
| `just dev-backend` | Start backend stack |
| `just dev-frontend` | Start frontend |
| `just stop-all` | Stop everything |
| `just migrate-backend-new "name"` | New Alembic migration |
| `just seed-test-user` | Create a local test user |

## What's running where

| Port | Service |
|---|---|
| `3000` | Next.js frontend |
| `4321` | Astro docs (this site) |
| `5432` | PostgreSQL |
| `6379` | Redis (broker) |
| `7233` | Temporal server |
| `8200` | FastAPI API |
| `8233` | Temporal UI |

## Where to go next

- [Architecture](/docs/architecture)
- [Backend modules](/docs/backend/modules)
- [Add a Use Case](/guides/add-a-use-case)
