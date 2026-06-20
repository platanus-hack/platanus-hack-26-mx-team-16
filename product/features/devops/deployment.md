---
feature: devops
type: plan
status: implemented
coverage: 98
audited: 2026-06-16
---

# Spec: Despliegues Docker Versionados (Doxiq monorepo) vía GitHub Tags + Portainer API

> **Para Claude Code:** Este spec es el runbook ejecutable adaptado a Doxiq. El proyecto es un monorepo con `backend/` y `frontend/` independientes, cada uno con su propio Dockerfile, compose files y stack en Portainer. Sigue los pasos en orden y reporta si algo falla.

## Qué entrega este spec

Pipeline de deploy donde:
- Push a `dev` o `main` → build & deploy de `backend/` y/o `frontend/` (sólo los que cambiaron) con tag `sha-<short>`.
- Tag `v*.*.*` → build de **ambos** servicios + deploy a Production con aliases semver (`v1.2.3`, `1.2`, `1`, `stable`, `sha-<short>`).
- Workflow manual `redeploy.yml` → redeploya cualquier tag existente para backend/frontend/ambos sin reconstruir.
- Cuatro compose files (`backend/docker-compose.{dev,prod}.yml`, `frontend/docker-compose.{dev,prod}.yml`) ya parametrizados con `${IMAGE_TAG:-latest}`.

## Pre-flight checks

1. `backend/Dockerfile` define target `production_builder` y `production` final stage. ✓
2. `frontend/Dockerfile` define target `production`. ✓
3. `backend/docker-compose.{dev,prod}.yml` existen y referencian `${IMAGE_TAG:-latest}`. ✓
4. `frontend/docker-compose.{dev,prod}.yml` existen y referencian `${IMAGE_TAG:-latest}`. ✓
5. `.github/workflows/` existe con `build_backend.yml` y `build_frontend.yml` (a reemplazar). ✓
6. Plataforma destino: Portainer + GHCR.

## Estructura de imágenes

| Servicio | Repository URI Dev | Repository URI Prod |
|---|---|---|
| Backend | `ghcr.io/llamitai/doxiq-ws-dev` | `ghcr.io/llamitai/doxiq-ws-prod` |
| Frontend | `ghcr.io/llamitai/doxiq-web-dev` | `ghcr.io/llamitai/doxiq-web-prod` |

Estos valores vienen de **GitHub Environment Variables** (`BACKEND_REPOSITORY_URI`, `FRONTEND_REPOSITORY_URI`) — distintos por environment.

## Decisiones de adaptación

- **Portainer API** (no webhooks). Migramos de `curl POST webhook?IMAGE_TAG=...` a `cssnr/portainer-stack-deploy-action@v1`. Trade-off: se pierde CF Access (los headers `CF-Access-*` no se soportan); requiere exponer Portainer API al runner de GitHub (whitelist o público con token).
- **Tag único `v*.*.*`** para versionado conjunto backend+frontend. Un solo `git tag v1.2.3` libera ambos servicios con el mismo número.
- **Un solo `redeploy.yml`** con selector `service` (`backend` | `frontend` | `both`).
- **Stacks deben ser tipo "Git Repository"** en Portainer (no standalone-webhook). Los stacks actuales se deben reconfigurar manualmente.

## GitHub Environments — secrets & variables

Dos environments: `Development` y `Production`.

### Variables (por environment)
- `BACKEND_REPOSITORY_URI` — URI sin tag (ej. `ghcr.io/llamitai/doxiq-ws-prod`)
- `FRONTEND_REPOSITORY_URI` — URI sin tag (ej. `ghcr.io/llamitai/doxiq-web-prod`)
- `PORTAINER_URL` — base URL del Portainer
- `BACKEND_DEPLOYMENT_SERVICE` — nombre del stack backend en Portainer
- `FRONTEND_DEPLOYMENT_SERVICE` — nombre del stack frontend en Portainer
- `BACKEND_DEPLOYMENT_COMPOSE_FILE` — ruta repo (ej. `backend/docker-compose.prod.yml`)
- `FRONTEND_DEPLOYMENT_COMPOSE_FILE` — ruta repo (ej. `frontend/docker-compose.prod.yml`)
- `INFISICAL_SECRET_ENV`, `PROJECT_ID`, `INFISICAL_API_URL`
- `ADMIN_EMAIL`, `ADMIN_DB_HOST`, `ADMIN_DB_DATABASE`, `ADMIN_DB_USER`, `ADMIN_PUBLIC_URL`

### Secrets (por environment)
- `PORTAINER_TOKEN` — token de API Portainer con permiso de update stack
- `INFISICAL_MACHINE_CLIENT_ID`, `INFISICAL_MACHINE_CLIENT_SECRET`
- `ADMIN_SECRET`, `ADMIN_PASSWORD`, `ADMIN_DB_PASSWORD`

## Workflows

### `.github/workflows/build_backend.yml`
Trigger: push a `dev`/`main` con cambios en `backend/**`. Tag `sha-<short>` + `latest`. Deploy via Portainer API.

### `.github/workflows/build_frontend.yml`
Trigger: push a `dev`/`main` con cambios en `frontend/**`. Tag `sha-<short>` + `latest`. Deploy via Portainer API.

### `.github/workflows/release.yml`
Trigger: push de tag `v*.*.*`. Builds backend Y frontend en paralelo con semver tags. Deploy a Production de ambos.

### `.github/workflows/redeploy.yml`
Manual `workflow_dispatch`. Inputs: `service` (`backend`/`frontend`/`both`), `target_environment` (`Development`/`Production`), `version`. Verifica imagen existe y deploya.

## Verificación

1. Push a `dev` con cambios en `backend/` → `build_backend.yml` corre → stack `doxiq-backend-dev` en Portainer toma `IMAGE_TAG=sha-<short>`.
2. `git tag v0.0.1 && git push origin v0.0.1` → `release.yml` corre → stacks Production de ambos servicios toman `IMAGE_TAG=v0.0.1`.
3. Actions UI → "Redeploy Version" → `service=backend`, `version=v0.0.1`, `target_environment=Production` → step "Verify image exists" pasa → Portainer redeploya.

## Trade-offs y caveats

- **Sin CF Access.** El runner de GH debe poder llegar a `PORTAINER_URL`. Opciones: IP whitelist del rango de GHA runners (no recomendado, cambia), túnel inverso, o exponer Portainer con autenticación token-only.
- **`stable` es alias móvil.** Útil para monitoring, nunca pinnees a `stable` en prod.
- **Build duplicado entre `build_*.yml` y `release.yml`.** Separación de responsabilidades — fácil razonar sobre la matriz de triggers.
- **`env_data` reemplaza vars del stack en Portainer.** Todas las env vars deben venir de GitHub Environments — Portainer ya no las almacena.
- **`linux/amd64` única.** Multi-arch agregaría `platforms: linux/amd64,linux/arm64` en `build-push-action`.

## Manifiesto de archivos

Modifica:
- `.github/workflows/build_backend.yml`
- `.github/workflows/build_frontend.yml`

Crea:
- `.github/workflows/release.yml`
- `.github/workflows/redeploy.yml`

No toca:
- Compose files (ya están parametrizados).
- Dockerfiles (ya tienen target `production`).
- `.github/workflows/promote.yml` (cubierto por `product/features/devops/promote.md`).
