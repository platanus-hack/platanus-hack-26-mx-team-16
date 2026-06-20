---
feature: devops
type: plan
status: implemented
coverage: 100
audited: 2026-06-16
---

# Spec: Promover `dev` → `main` vía GitHub App (Doxiq)

> **Para Claude Code:** Este spec es un runbook ejecutable adaptado al monorepo de Doxiq (`backend/` + `frontend/`). Los Pasos 1–5 requieren acciones manuales en la UI de GitHub que tú no puedes ejecutar — guía al usuario por esas. El Paso 6 (escribir `.github/workflows/promote.yml`) lo ejecutas tú.

## Qué entrega este spec

Un workflow manual (`workflow_dispatch`) que promueve `dev` (rolling) hacia `main` (stable), con dos estrategias:
- **`merge`** (default): fast-forward only. Falla si las branches divergieron.
- **`reset`**: `git reset --hard` + `git push --force-with-lease`. Destructivo. Útil cuando `main` divergió y `dev` es la fuente de verdad.

Se autentica con un **GitHub App** (no PAT). Los pushes deben disparar `build_backend.yml` y `build_frontend.yml` en `main`, cosa que el `GITHUB_TOKEN` default no puede hacer.

## Contexto del repo

- Branch rolling: **`dev`** — recibe todos los merges de feature branches.
- Branch stable: **`main`** — gatilla los builds de producción.
- Workflows que se disparan al pushear `main`:
  - `.github/workflows/build_backend.yml` — sólo si cambió `backend/**`.
  - `.github/workflows/build_frontend.yml` — sólo si cambió `frontend/**`.
- Ambos build workflows usan `environment: Production` (con secrets de Portainer/Cloudflare) cuando el ref es `main`.

Esto implica que un push a `main` que no haga el GitHub App **no dispararía** los builds y el deploy a producción no ocurriría — por eso usamos App, no `GITHUB_TOKEN`.

## Pre-flight checks

1. El repo tiene ambas branches `dev` y `main` activas.
2. El usuario tiene acceso admin a la org `Llamitai` (o personal si el repo es personal) para crear un GitHub App.
3. Las branches `main` debería tener branch protection. Si no existe, avisa y continúa.

## Inputs concretos

| Input | Valor para Doxiq |
|---|---|
| Source branch | `dev` |
| Target branch | `main` |
| App slug sugerido | `doxiq-ci-promote` |
| Scope | Org `Llamitai` (preferido) o personal |

## ¿Por qué un GitHub App en vez de un PAT?

| | PAT | GitHub App |
|---|---|---|
| Expiración | Manual | Ninguna (token efímero por run) |
| Vinculado a humano | Sí | No |
| Permisos granulares | Scopes gruesos | Por recurso |
| Auditoría | Acciones del user | Bot identificable |
| Dispara workflows downstream | Sí | Sí |
| Tiempo de setup | ~1 min | ~10 min |

## Pasos de implementación

### Paso 1 — Crear el GitHub App

Imprime al usuario:

> 1. Ir a **Org Settings** (`Llamitai`) → **Developer settings** → **GitHub Apps** → **New GitHub App**. (Si no es repo de org, usar Settings personal del owner.)
> 2. Rellenar:
>    - **GitHub App name**: `doxiq-ci-promote` (debe ser único globalmente en GitHub — si ya existe, agregar sufijo).
>    - **Homepage URL**: link al repo (ej. `https://github.com/Llamitai/doxiq`).
>    - **Webhook → Active**: **desmarcar**.
>    - **Repository permissions**:
>      - `Contents`: **Read and write**
>      - `Metadata`: **Read-only** (auto-asignado)
>      - `Workflows`: **Read and write** (sólo si en algún momento promote.yml llegará a modificar archivos bajo `.github/workflows/` — por ahora no, pero opcional para futuro).
>    - **Where can this GitHub App be installed?**: **Only on this account**.
> 3. **Create GitHub App**.

Espera confirmación.

### Paso 2 — Generar la Private Key

> 1. En la página del App, scroll a **Private keys** → **Generate a private key**.
> 2. Descargar el `.pem` (sólo se muestra una vez).
> 3. Anotar el **App ID** numérico (visible arriba bajo "About").

Espera confirmación.

### Paso 3 — Instalar el App en el repo `doxiq`

> 1. Sidebar del App → **Install App**.
> 2. Seleccionar la org `Llamitai`.
> 3. **Only select repositories** → marcar sólo `doxiq`.
> 4. **Install**.

Espera confirmación.

### Paso 4 — Guardar credenciales como secrets

> En el repo `Llamitai/doxiq`: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:
>
> | Secret | Valor |
> |---|---|
> | `PROMOTE_APP_ID` | El App ID numérico del Paso 2. |
> | `PROMOTE_APP_PRIVATE_KEY` | Contenido completo del `.pem`, incluyendo `-----BEGIN ... KEY-----` / `-----END ... KEY-----`. Multi-línea, pegar tal cual. |
>
> Si Doxiq llega a tener más repos en la org que necesiten promote, define ambos a nivel org (Org Settings → Secrets → Actions) en vez de repo-by-repo.

Espera confirmación.

### Paso 5 — Configurar bypass en branch protection de `main`

Si `main` tiene branch protection (preguntar si hay dudas), imprime:

> Editar la regla de protección de `main`:
>
> | Setting | `merge` strategy | `reset` strategy |
> |---|---|---|
> | **Require a pull request before merging** | `doxiq-ci-promote[bot]` en "Allow specified actors to bypass" | Lo mismo |
> | **Require status checks to pass** | Los checks deben haber pasado en `dev` previamente (los builds en dev sirven de proxy) | Lo mismo |
> | **Allow force pushes** | No necesario | `doxiq-ci-promote[bot]` en "Specify who can force push" |
> | **Restrict who can push** | App en el allowlist | Lo mismo |
>
> El App aparece en los selectors sólo después de instalarlo (Paso 3).

Si no hay branch protection, avísale al usuario que debería configurarla antes de exponer el workflow.

### Paso 6 — Escribir `.github/workflows/promote.yml`

Este paso lo ejecuta Claude Code. El archivo final está en el repo.

### Paso 7 — Reportar al usuario

Resumen post-implementación:
1. Workflow `.github/workflows/promote.yml` creado.
2. El usuario aún debe completar Pasos 1–5 (App + secrets + branch protection).
3. Cómo correrlo: GitHub UI → Actions → **Promote dev → main** → Run workflow → elegir estrategia (`merge` por defecto).
4. Tras el push, `build_backend.yml` y `build_frontend.yml` en `main` se disparan automáticamente y deployan a Producción.

## Verificación

1. Actions → "Promote dev → main" → Run workflow con `merge`.
2. El step "Generate GitHub App token" debe pasar sin `Bad credentials`.
3. El push a `main` se completa.
4. `build_backend.yml` y/o `build_frontend.yml` se disparan en `main` (sólo si cambiaron archivos bajo `backend/**` o `frontend/**`).
5. El commit en `main` queda atribuido a `doxiq-ci-promote[bot]`.

## Cuándo usar cada estrategia

| Situación | Estrategia |
|---|---|
| Flujo normal: todo pasa por `dev`, sin commits directos a `main` | `merge` |
| `main` recibió un hotfix directo que ya no quieres y no está en `dev` | `reset` |
| `main` y `dev` divergieron de formas irreconciliables y `dev` es la fuente de verdad | `reset` |
| Quieres merge commits / preservar historias separadas | Ninguna — usar PR normal |

## Troubleshooting

| Error | Causa | Fix |
|---|---|---|
| `Bad credentials` en el step de token | `PROMOTE_APP_ID` o PEM mal formado | Re-pegar el PEM con marcadores BEGIN/END completos. Regenerar si hay dudas. |
| `Resource not accessible by integration` al push | App sin permiso `Contents: write` o no instalado en `doxiq` | Verificar permisos e instalación |
| `Protected branch hook declined` | Branch protection de `main` bloquea al App | Agregar al bypass list |
| `Updates were rejected ...` (con `merge`) | `dev` y `main` divergieron — ff-only imposible | Usar `reset` o resolver manualmente |
| `force-with-lease` falla | Push concurrente durante el run | Re-correr e investigar |
| `build_backend.yml` / `build_frontend.yml` no se disparan tras promote | El workflow promote usa `GITHUB_TOKEN` en vez del App token | Verificar que `checkout` usa `steps.app-token.outputs.token` |
| `build_*` se disparan pero no había cambios reales | Promote arrastró commits que no tocan `backend/**` ni `frontend/**` — esto es OK, los paths filters lo cortan | No action needed |

## Rotación y mantenimiento

- **Private key**: rotar anualmente o si se sospecha filtración. Generar nueva → actualizar `PROMOTE_APP_PRIVATE_KEY` → eliminar la vieja.
- **Permisos**: si el workflow se extiende (ej. crear PRs, editar workflows), bumpear permisos del App y aceptar el cambio en la página de instalación.
- **Auditoría**: las acciones quedan en **Settings → Security log** identificadas por `doxiq-ci-promote[bot]`.

## Trade-offs y caveats

- **¿Por qué no `GITHUB_TOKEN`?** Sus pushes no disparan otros workflows, así que `build_backend.yml` y `build_frontend.yml` no correrían en `main` después del promote.
- **¿Por qué `--force-with-lease` en vez de `--force`?** El lease aborta si el remote se movió desde el último fetch — atrapa pushes concurrentes.
- **¿Por qué ff-only para `merge`?** Un merge no-ff crea merge commits y oscurece la historia lineal. El fallo ff-only es señal útil de que algo divergió.
- **Reuso a nivel org**: el mismo App puede instalarse en otros repos `Llamitai/*` que tengan el mismo patrón `dev → main`. Definir secrets a nivel org evita duplicación.

## Manifiesto de archivos

Archivos que este spec crea o modifica en el repo:
- `.github/workflows/promote.yml` (crear)

Artefactos externos (UI de GitHub):
- GitHub App `doxiq-ci-promote` instalado en `Llamitai/doxiq`.
- Secrets `PROMOTE_APP_ID` y `PROMOTE_APP_PRIVATE_KEY` (repo o nivel org).
- Bypass del App en branch protection de `main`.
