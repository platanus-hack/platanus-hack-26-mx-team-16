<div align="center">

<img src="./project-logo.png" alt="Owliver logo" width="160" />

# Owliver 🦉

**Automated AI-orchestrated pentesting that breaks your AI live and grades it from A to F.**

[![Track](https://img.shields.io/badge/Track-%F0%9F%9B%A1%EF%B8%8F%20AI%20Security-5648E8?style=for-the-badge)](#)
[![Hackathon](https://img.shields.io/badge/Platanus%20Hack%2026-CDMX-111111?style=for-the-badge)](#)
[![Team](https://img.shields.io/badge/Team-16-FF7A00?style=for-the-badge)](#)

🔗 **Live demo →** [owliver.chuspita.com](https://owliver.chuspita.com)

</div>

---

## ¿Qué es Owliver?

Le das una **URL** y un **nivel de ataque**, y un equipo de agentes de IA (un
**orquestador Opus** + **2 subagentes Sonnet**) ejecuta un pentest real sobre la
superficie clásica (**OWASP**) **y** la nueva **superficie agéntica**: los
chatbots y LLMs que las empresas exponen y que son vulnerables a
*prompt-injection* y *jailbreaks* — algo a lo que los escáneres tradicionales son
ciegos.

Owliver no solo detecta fallas: **rompe la IA y lo prueba con evidencia**. Un
juez LLM junto a un *canary token* elimina falsos positivos — si logramos que el
chatbot revele su *system-prompt* oculto, lo documentamos como éxito total.
Entrega un **reporte legible con calificación A–F** que alimenta un **ranking
público de sitios `.gob.mx`** y **watchlists privadas** para monitoreo continuo.

---

## 🏆 Hackathon

**team-16 · Platanus Hack 26: CDMX** — Track: 🛡️ **AI Security**

| Integrante | GitHub |
|---|---|
| Victor Aguilar Cusicanqui | [@victoraguilarc](https://github.com/victoraguilarc) |
| Monica Canaza Mamani | [@monihikari](https://github.com/monihikari) |
| Abril Minerva Estrada Montaño | [@xaprilapril](https://github.com/xaprilapril) |

---

## ⚡ Quickstart

Requiere [`just`](https://github.com/casey/just), Docker y [`pnpm`](https://pnpm.io/).
Puertos: **backend `8200`**, **frontend `8080`**.

```bash
just dev-backend      # API + worker + Postgres + Redis  (port 8200)
just migrate-backend  # aplica migraciones de la DB
just seed-users       # usuarios demo · login: team@owliver.com / 12345678x
just dev-frontend     # Next.js dev server               (port 8080)

# …o todo a la vez (logs interleaved):
just dev-all
```

> **🔑 Credenciales de prueba** — tras `just seed-users`, inicia sesión con
> **`team@owliver.com`** · contraseña **`12345678x`**. Todos los usuarios demo
> sembrados comparten esa contraseña.

> `just` sin argumentos lista todas las recetas disponibles.

---

## 🧰 Cheatsheet de comandos

### Backend — `:8200`

| Comando | Qué hace |
|---|---|
| `just dev-backend` | Levanta API + worker + Postgres + Redis (docker compose). |
| `just dev-backend-d` | Igual, en modo *detached*. |
| `just dev-backend-local` | API local con uvicorn `--reload` (requiere Postgres/Redis aparte). |
| `just dev-worker` | Solo el worker del motor (imagen de scanners, DooD). |
| `just build-backend` | Construye las imágenes del backend. |
| `just build-scanners` | Construye la imagen pesada de scanners + worker. |
| `just warm-scanners` | Precalienta imágenes pesadas + plantillas de Nuclei. |
| `just bash-backend` | Abre `bash` dentro del contenedor de la API. |
| `just logs-backend` | Sigue los logs de la API (`-f`). |
| `just stop-backend` | Detiene los contenedores del backend. |

### Base de datos & migraciones

| Comando | Qué hace |
|---|---|
| `just migrate-backend` | Aplica todas las migraciones (`alembic upgrade head`). |
| `just migrate-backend-new "name"` | Crea una migración nueva (autogenerate). |
| `just migrate-backend-current` | Muestra la revisión actual. |
| `just migrate-backend-down steps=1` | Revierte las últimas `N` migraciones. |
| `just seed-users` | Siembra tenants y usuarios demo (correr tras migrar). Login: `team@owliver.com` / `12345678x`. |

### Frontend — `:8080`

| Comando | Qué hace |
|---|---|
| `just dev-frontend` | Servidor de desarrollo de Next.js. |
| `just build-frontend` | Build de producción. |
| `just install-frontend` | Instala dependencias (`pnpm install`). |
| `just lint-frontend` | Linter del frontend. |

### Testing & E2E

| Comando | Qué hace |
|---|---|
| `just test-backend [path]` | Tests del backend con pytest (filtro opcional de ruta). |
| `just test-frontend` | Tests del frontend. |
| `just e2e` | Cypress headless (Chrome). |
| `just e2e-open` | Abre la UI interactiva de Cypress. |
| `just e2e-headed` | Cypress con navegador visible. |
| `just e2e-spec <spec>` | Corre un spec puntual (p. ej. `01-landing.cy.ts`). |

### Docker (producción) & utilidades

| Comando | Qué hace |
|---|---|
| `just build-all` / `just build-prod` | Build de todo / imagen de producción del backend. |
| `just up-prod` | Levanta el backend de producción (*detached*). |
| `just stop-all` | Detiene todos los contenedores. |
| `just clean` | Limpia contenedores e imágenes colgantes. |
| `just ps` | Muestra los contenedores en ejecución. |

> 🤖 ¿Trabajando con los MCPs y skills del repo (CodeGraph, context-mode, etc.)?
> Mira [`CHEATSHEET.md`](./CHEATSHEET.md).

---

## ⚠️ Deploying & integrations (Vercel, Render, etc.)

Deploy platforms like **Vercel**, **Render** or **Netlify** can only connect to
repositories **you own** — they can't be granted access to this organization repo.
To deploy (or add any integration) while keeping your commits here, mirror your
code to a personal repo:

1. Create a **personal** repository on your own GitHub account.
2. Point your local `origin` at **both** repos, so a single `git push` updates each one:

   ```bash
   # this org repo (keep it as a push target)...
   git remote set-url --add --push origin https://github.com/platanus-hack/platanus-hack-26-mx-team-16.git
   # ...and your personal repo
   git remote set-url --add --push origin https://github.com/<your-user>/<your-repo>.git
   ```

   From now on `git push` sends every commit to **both** repositories.
3. Connect your deploy service (Vercel, Render, …) to your **personal** repo and deploy from there.

Your commits stay mirrored here for judging, while the deploy runs from the repo you control.

Have fun! 🚀
