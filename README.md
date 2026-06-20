# Doxiq

Minimal multi-tenant SaaS starter boilerplate. Provides authentication,
users, tenants, roles/permissions and invitations out of the box, plus a
generic asynchronous background-job mechanism — ready to build a product on
top of.

## Stack Tecnologico

| Capa | Tecnologia |
|------|-----------|
| Frontend | Next.js 15 + React 19 + TypeScript + Tailwind CSS v4 + shadcn |
| Backend | FastAPI + Python 3.12 + SQLAlchemy (async) + PostgreSQL |
| Background jobs | SAQ (Redis-backed async queue) |
| Auth | JWT + Google OAuth |

## Arquitectura

```
doxiq/
  backend/          # FastAPI + Clean Architecture (DDD)
  frontend/         # Next.js App (shadcn + Base UI)
  product/          # Specs y planes del proyecto
```

### Backend — Clean Architecture

Cada modulo sigue la estructura:

```
src/<module>/
  domain/           # Entidades, repositorios (ABC), excepciones
  application/      # Use cases, commands
  infrastructure/   # Repositorios SQL, servicios externos
  presentation/     # Endpoints, routers, presenters, schemas
```

**Modulos:** auth, users, profile, tenants, common, messaging (+ assets, admin)

## Funcionalidades

### Multi-tenancy
- Tenants con roles y permisos configurables
- Invitaciones de miembros
- Bootstrap de roles por defecto (admin / member)

### Autenticacion
- JWT con refresh tokens
- Login con Google OAuth
- Sesiones por tenant

### Background jobs
- Cola asincrona generica via SAQ (Redis)
- Endpoint de ejemplo que encola un job para demostrar el patron

## Desarrollo

### Requisitos
- Python 3.12+
- Node.js 18+
- Docker + Docker Compose

### Backend

```bash
# Con Docker (recomendado)
just dev-backend

# O directamente
cd backend && docker compose up
```

Backend disponible en `http://localhost:8200`

### Frontend

```bash
just dev-frontend

# O directamente
cd frontend && npm install && npm run dev
```

Frontend disponible en `http://localhost:3000`

### Comandos utiles (justfile)

```bash
just                    # Listar todos los comandos
just dev-all            # Iniciar backend + frontend
just dev-backend        # Solo backend (Docker)
just dev-frontend       # Solo frontend
just migrate-backend    # Correr migraciones
just stop-all           # Parar todos los contenedores
```

### Variables de Entorno (backend/.env)

| Variable | Descripcion |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string (SAQ + tokens) |
| `CORS_ORIGINS` | Origenes permitidos CORS |
| `JWT_SECRET_KEY` | Secret para tokens JWT |
| `GOOGLE_CLIENT_ID` | Google OAuth client id |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |

## Documentacion

| Documento | Contenido |
|-----------|----------|
| [CHEATSHEET.md](CHEATSHEET.md) | Referencia ultra compacta para pedir uso de MCPs y skills en prompts |
| [PRODUCT.md](PRODUCT.md) | Direccion estrategica de producto y diseño |
| [DESIGN.md](DESIGN.md) | Sistema visual (tokens, tipografia, componentes) |
| [product/specs/](product/specs/) | Specs (QUE se construye) |
| [product/plans/](product/plans/) | Planes (COMO, con referencia a codigo) |
