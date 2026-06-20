# Backend (vnext-ws) — Features

> Stack: FastAPI + PostgreSQL (pgvector) + Redis + Temporal + S3
> Puerto: 8200

---

## Auth

- Login email/password con JWT (access 1min + refresh 2 días)
- Google OAuth
- Refresh token, logout, reset password
- Session management

**Endpoints:** `POST /v1/auth/login`, `/google-login`, `/refresh`, `/logout`, `/reset-password`, `GET /v1/auth/session`

---

## Users

- Registro de usuarios
- Password hashing (bcrypt)
- Email y teléfono como entidades separadas (normalizadas)
- Tracking de último login
- Flags: is_active, is_staff, is_superuser

---

## Multi-Tenancy

- Cada tenant tiene: nombre, slug, status, timezone, país, moneda, logo
- Estados: ACTIVE, PENDING, INACTIVE, SUSPENDED
- Usuarios asociados a tenants con roles y permisos
- Switch de tenant activo por usuario

**Endpoints:** `POST/PUT /v1/tenants`, roles CRUD, tenant users CRUD, stats

---

## RBAC (Roles & Permisos)

- Roles por tenant con permisos en JSON
- Permisos por namespace: TenantRole, TenantSetting, etc.
- Flags especiales: is_owner, is_support
- Bootstrap de roles por defecto

---

## Workspaces

- CRUD de workspaces por tenant
- Soft archive (is_archived)
- Paginación

**Endpoints:** `GET/POST/PUT/PATCH/DELETE /v1/workspaces`

---

## Profile (/me)

- Ver/editar perfil propio
- Cambiar password
- Listar tenants del usuario
- Cambiar tenant activo

**Endpoints:** `GET/PUT /v1/me/profile`, `PUT /v1/me/password`, `GET /v1/me/tenants`, `PUT /v1/me/tenants/{id}`

---

## Document Processing (Temporal)

- Workflow: `DocumentProcessingWorkflow`
- Activities: TextReader → ExtractionNormalizer → ExtractionValidator
- Signals: cancel, pause, resume
- Retry: 4 intentos, backoff exponencial (2s → 5min max)
- Timeouts: 5min lectura, 3min normalización

---

## Messaging

- Envío de emails async vía SMTP
- Templates Jinja2 (HTML + texto plano)
- Rate limiting con semáforo (MAX_CONCURRENT_EMAILS)

---

## Infraestructura

| Componente | Implementación |
|-----------|---------------|
| DB | PostgreSQL 17 + pgvector + Alembic migrations |
| Cache/Queue | Redis 7 + ARQ task queue |
| Orchestration | Temporal (document processing workflows) |
| Storage | AWS S3 (+ CloudFront) |
| Monitoring | Sentry (error tracking + sampling) |
| Email | SMTP async con TLS |

---

## Middlewares

- **CamelCase transformer** — request/response snake_case ↔ camelCase automático
- **Rate limiter** — Redis-backed, headers X-RateLimit-*
- **Request tracking** — correlation IDs por request
- **Security headers** — X-Content-Type-Options, X-Frame-Options, etc.
- **CORS** — orígenes configurables

---

## Arquitectura

```
src/
├── auth/          # JWT, Google OAuth, sessions
├── users/         # User CRUD, password mgmt
├── tenants/       # Multi-tenancy, roles, permisos
├── workspaces/    # Workspace CRUD
├── profile/       # /me endpoints
├── workflows/     # Temporal document processing
├── messaging/     # Email service
├── integrations/  # Admin utilities
└── common/
    ├── domain/    # Entities, enums, exceptions
    ├── application/ # Use cases (command/query)
    └── infrastructure/ # DB, Redis, JWT, middleware
```

**Patrón:** DDD con Command/Query, repositories, presenters, dependency injection vía FastAPI Depends().

---

## DB Models

| Tabla | PK | Campos clave |
|-------|-----|-------------|
| users | UUID | username, password, email_address_id, phone_number_id, current_tenant_id |
| tenants | UUID | name, slug, status, timezone, country_code, currency_code, owner_id |
| tenant_users | UUID | user_id, tenant_id, tenant_role_id, is_owner, permissions (JSON) |
| tenant_roles | UUID | tenant_id, name, slug, permissions (JSON), status |
| workspaces | UUID | tenant_id, name, description, is_archived |
| email_addresses | UUID | email (unique) |
| phone_numbers | UUID | phone (unique) |

Todos con `created_at`, `updated_at`.

---

## Config (env vars)

| Grupo | Variables |
|-------|----------|
| Postgres | `POSTGRES_HOST`, `_PORT`, `_USER`, `_PASSWORD`, `_DB` |
| Redis | `REDIS_HOST`, `_PORT`, `_PASSWORD`, `_DB` |
| SMTP | `SMTP_HOST`, `_PORT`, `_USER`, `_PASSWORD`, `SMTP_SENDER` |
| AWS S3 | `AWS_S3_ENDPOINT`, `_KEY`, `_SECRET`, `_BUCKET`, `AWS_CLOUDFRONT_URL` |
| Google | `GOOGLE_CLIENT_ID`, `_SECRET`, `_REDIRECT_URI` |
| Sentry | `SENTRY_DSN`, `_TRACES_SAMPLE_RATE` |
| CORS | `CORS_ORIGINS` |
