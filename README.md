# Owliver 🦉

**Owliver** es una plataforma de **pentesting automático orquestado por agentes
IA**. Ingresas una URL + nivel de ataque, un equipo de agentes ejecuta un pentest
(OWASP **+** la **superficie agéntica** — chatbots / widgets LLM, buscando
prompt-injection y jailbreaks) y genera un reporte fácil de entender pero
técnicamente valioso, con un **score A–F**. Los resultados alimentan un **ranking
público de sitios del Estado mexicano (`.gob.mx`)** y **watchlists privadas** para
monitoreo continuo.

> **Especificación completa del producto:** [`spec.md`](product/spec.md) es la fuente de
> verdad — visión, diseño del worker / equipo Agno, motor de scanners, modelo de
> datos, scoring A–F y features. Este repo parte de una **base SaaS multi-tenant**
> (auth, usuarios, tenants, roles/permisos, invitaciones y una cola de jobs
> asíncronos SAQ) sobre la que se construye el motor de Owliver.

## Stack Tecnologico

| Capa | Tecnologia |
|------|-----------|
| Frontend | Next.js 15 + React 19 + TypeScript + Tailwind CSS v4 + shadcn |
| Backend / API | FastAPI + Python 3.12 + SQLAlchemy (async) + PostgreSQL |
| Auth | JWT + magic-link por email (base actual: JWT + Google OAuth) |
| Cola + tiempo real | Redis — cola de jobs asíncronos + pub/sub para el live-view (SSE) |
| Worker de pentest | Python + **Agno** (Team: orquestador Opus + 2 subagentes Sonnet) |
| Scanners | Nuclei · OWASP ZAP · testssl.sh · WhatWeb · Nikto · katana · sqlmap · garak / promptfoo · hexstrike-ai (en contenedores Docker) |

> El worker de pentest, los scanners y el scoring están especificados en
> [`spec.md`](product/spec.md); la base del repo hoy implementa auth / tenants / jobs SAQ.

## Arquitectura

```
owliver/
  backend/          # FastAPI + Clean Architecture (DDD)
  frontend/         # Next.js App (shadcn + Base UI)
  product/          # Specs y planes del proyecto
  spec.md           # Especificacion de producto de Owliver (fuente de verdad)
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

## Capacidades de Owliver (ver [spec.md](product/spec.md))

- **Pentest orquestado por IA** en 3 niveles (básico/pasivo, intermedio, avanzado),
  con equipo Agno (orquestador Opus + subagentes OWASP y Agéntico en Sonnet).
- **Auditoría de superficie agéntica:** detecta chatbots / widgets LLM y los sondea
  con canary, system-prompt leak y jailbreaks → mapeo a OWASP Top 10 for LLM.
- **Doble score 0–100 + grado A–F** (🛡️ Web/OWASP y 🤖 Agéntico) estilo Mozilla Observatory.
- **Ranking público `.gob.mx`** (escaneos automáticos = solo pasivos) + **watchlists
  privadas** con monitoreo recurrente y alertas (email / Slack).
- **Live-view por SSE** del pentest, **reporte "Owliver te explica"**, export PDF y
  link público compartible `/r/{token}`.

> Nota legal: el modo activo exige **atestación + consentimiento** del usuario; los
> escaneos automáticos del ranking son siempre pasivos (ver §3 de `spec.md`).

## Funcionalidades base (SaaS, en el repo)

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
| [spec.md](product/spec.md) | **Especificación de producto de Owliver** (fuente de verdad: visión, arquitectura, scoring, features) |
| [CHEATSHEET.md](CHEATSHEET.md) | Referencia ultra compacta para pedir uso de MCPs y skills en prompts |
| [PRODUCT.md](PRODUCT.md) | Direccion estrategica de producto y diseño |
| [DESIGN.md](DESIGN.md) | Sistema visual (tokens, tipografia, componentes) |
| [product/features/](product/features/) | Features (feature-first): cada carpeta con `spec.md` (QUE) + `plan.md` (COMO) |
| [product/_archive/](product/_archive/) | Insumos historicos ya fusionados |
