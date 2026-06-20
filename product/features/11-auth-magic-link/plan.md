---
feature: auth-magic-link
type: plan
status: pending
coverage: 0
audited: 2026-06-20
spec: ./spec.md
sources: product/spec.md §12.2, §14.1, §14.2 (raíz `../../spec.md`); 06-data-model §2.5; 10-realtime-live-view §; 12-api §; auth/backend-auth.md; auth/frontend-auth.md
---

# Owliver — Auth magic-link sin contraseña — plan de implementación (CÓMO)

> El entregable medular **no** es "una pantalla de login", sino **un canje que
> emite la cookie de sesión correcta**: `GET /auth/callback?token=` valida la fila
> de `magic_tokens` (no consumida, no expirada), la marca consumida (1 uso),
> hace upsert del `user` y setea la cookie **HttpOnly SameSite=Lax** con el JWT.
> Esa cookie es exactamente la que autentica la live-view SSE de
> [10-realtime-live-view](../10-realtime-live-view/spec.md) (`EventSource` no manda
> `Authorization`, depende de cookies same-origin). Todo lo demás —las 4 pantallas,
> el reenvío con cooldown, las rutas BFF— cuelga de ese canje.
>
> Principio operativo: **emisión y canje están separados.** `POST /auth/magic-link`
> solo manda el correo y **siempre responde igual** exista o no el email (no se
> revela la existencia de cuentas). El plano del token **nunca** toca la DB: se
> guarda `sha256(token)` como `token_hash` (spec §3); si la DB se filtra, los
> hashes no son canjeables. Se reutiliza al máximo el flujo de password-reset ya
> implementado en `src/auth/` —es el mismo patrón "email → token de un uso →
> landing en `(public)`"— cambiando JWT-token-de-reset por fila en `magic_tokens`.

## 0. Estado de las dependencias

Esta feature monta el magic-link **sobre el módulo `auth` existente**; casi todo
ya está. Lo que **se reutiliza tal cual** (no se reinventa):

**Backend (`src/auth/` + `src/common/`):**

- **Emisión de JWT y sesión:** `backend/src/common/infrastructure/services/jwt_token_service.py`
  (`JwtTokenService.generate_token(sub, namespace)` → `JwtSession{access,refresh}`) y
  `jwt_token_builder.py`. El callback **reutiliza `generate_token`** para emitir el
  par que va a las cookies; no se inventa un JWT nuevo.
- **Patrón "email → token de un uso → landing":** ya existe end-to-end en
  password-reset: `backend/src/auth/application/use_cases/request_password_reset.py`
  (`RequestPasswordReset`: normaliza email, **silent success** si no existe, dispara
  `SendEmailCommand`) y `backend/src/auth/presentation/endpoints/reset_password.py`
  (**siempre 200** para no filtrar existencia). El magic-link copia esta postura
  literal; la única diferencia es persistir en `magic_tokens` en vez de un JWT scoped.
- **Envío de correo:** módulo `src/messaging/` —`application/commands/send_email.py`
  (`SendEmailCommand`, despachado por `command_bus`), `infrastructure/services/smtp_email.py`.
  El magic-link despacha el mismo `SendEmailCommand` con un template nuevo.
- **Upsert de `user` por email:** `GetOrCreateUserQuery`
  (`src/common/application/queries/users.py`) **despachado por el query-bus**
  (`query_bus.ask(...)`), resuelto por `GetOrCreateUserHandler`
  (`src/users/application/queries/get_user.py`, wired en `src/users/infrastructure/bus_wiring.py`).
  Es el **mismo mecanismo que usa `GoogleSessionBuilder`** en el canje del login Google;
  el callback del magic-link lo reutiliza tal cual (no se añade método al `UserRepository`).
- **Dependencia de ruta protegida:** `backend/src/common/infrastructure/dependencies/session.py`
  (`get_authenticated_user` / `AuthenticatedUserDep`) valida `Authorization: Bearer`.
  Se **extiende** (no se reemplaza) para leer también la cookie de sesión (ver §5),
  porque la live-view SSE y `GET /auth/me` se autentican por cookie, no por header.
- **Excepciones / base:** `DomainError` (`src/common/domain/exceptions/_base.py`),
  `UseCase` (`src/common/domain/interfaces/use_case.py`), `BaseEnum`
  (`src/common/domain/enums/base_enum.py`), `CamelCaseRequest`
  (`src/common/domain/entities/common/requests.py`), `ApiJSONResponse`.
- **Tabla `magic_tokens`:** la **define [06-data-model](../06-data-model/spec.md) §2.5**
  (`MagicTokenORM`, PK `token_hash char(64)`, `email`, `expires_at`, `consumed_at`,
  `created_at`). Aquí **no se redefine** el ORM ni la migración; se asume creada y se
  construye el repo + use cases encima. Si 06 aún no aterrizó, este plan lista el ORM
  como dependencia bloqueante, no como entregable propio.
- **Settings:** `backend/src/common/settings.py` (`FRONTEND_HOST`, `POSTGRES_*`,
  fail-loud). Se añade `MAGIC_LINK_TTL_MINUTES: int = 10` (default spec §3).

**Frontend (`frontend/src/`):**

- **Patrón BFF canónico:** `frontend/src/app/api/auth/login/route.ts` (lee respuesta
  del backend vía `serverHttp`, setea cookies HttpOnly `COOKIE_ACCESS_TOKEN` /
  `COOKIE_REFRESH_TOKEN`). Es el molde exacto de las rutas BFF nuevas.
- **Cliente HTTP server-side:** `frontend/src/infrastructure/http/client.ts`
  (`serverHttp`, baseURL `${apiBaseUrl}/v1`). Las rutas BFF lo usan vía
  `HttpAuthRepository` (`src/infrastructure/repositories/http-auth.ts`).
- **Constantes de cookie:** `frontend/src/constants.ts`
  (`COOKIE_ACCESS_TOKEN="___AT5___"`, `COOKIE_REFRESH_TOKEN="___RT5___"`,
  `ACCESS_TOKEN_MAX_AGE`, `REFRESH_TOKEN_MAX_AGE`). Se reutilizan sin cambios.
- **Route-group y proxy:** `frontend/src/app/(public)/` (layout sin sidebar; ya
  alberga `register`, `reset-password`, `invitations/[token]`) y
  `frontend/src/proxy.ts` (rewrite `/api/v1/* → backend` con `X-Api-Key`;
  `PUBLIC_PREFIX_ROUTES` para flujos token-bearing). Las pantallas nuevas viven en
  `(public)` y sus rutas se añaden a las listas públicas del proxy.
- **SSE helper:** `backend/src/common/infrastructure/sse/streaming.py`
  (`stream_sse`) — no se toca aquí, pero la cookie que este plan emite es su
  prerrequisito de auth (ver §4).

> **Decisión Clerk vs casero (spec §2):** la spec deja la puerta abierta a Clerk si
> está disponible. **Este plan implementa la variante casera** (4 rutas a mano sobre
> el `auth` existente) porque es la que toca código del repo; Clerk se documenta como
> riesgo/alternativa en §9, no como camino de build.

## 1. Decisión de módulos — dónde viven las cosas

El magic-link es **autenticación**, no motor de pentest. Por eso, siguiendo la
asignación de [06-data-model](../06-data-model/plan.md) §1, **todo vive en `src/auth/`**
(no se crea módulo nuevo, no se toca `src/scans/` ni `src/sites/`):

| Capa | Ubicación | Qué añade |
|---|---|---|
| `domain/repositories/` | `src/auth/domain/repositories/magic_token.py` | `MagicTokenRepository(ABC)`: `create`, `find_by_hash`, `mark_consumed`. |
| `application/use_cases/` | `src/auth/application/use_cases/request_magic_link.py`, `redeem_magic_link.py` | emisión (espeja `RequestPasswordReset`) y canje. |
| `infrastructure/repositories/` | `src/auth/infrastructure/repositories/sql_magic_token.py` | `@dataclass SQLMagicTokenRepository(session)`. |
| `presentation/endpoints/` | `magic_link.py`, `callback.py`, `me.py` | los 3 endpoints nuevos (`logout` ya existe). |
| `presentation/router.py` | (existente, se extiende) | `add_api_route` para los nuevos paths. |

> **Por qué no un repo de `magic_tokens` "compartido":** solo `auth` lo lee/escribe;
> mantenerlo dentro del módulo evita que `scans`/`sites` dependan de auth. El ORM
> `MagicTokenORM` lo posee 06-data-model pero se **registra** igual en
> `src/common/database/models/__init__.py` (punto único de `Base.metadata`).
>
> **Contraste con password-reset:** reset usa un **JWT scoped de un uso**
> (`create_one_shot_token`, `JwtTokenScope.PASSWORD_RESET`) sin tabla. El magic-link
> usa **tabla** porque la spec §3 exige `consumed_at` persistente (1 uso a prueba de
> replay incluso dentro del TTL) y `token_hash` auditable. Son dos mecanismos
> deliberadamente distintos; no se fusionan.

## 2. Mapa de archivos a crear

### 2.1 Árbol backend (`backend/`)

```
src/auth/
  domain/
    repositories/magic_token.py        # NUEVO  MagicTokenRepository(ABC)
    exceptions.py                      # EXISTE → +InvalidOrExpiredMagicTokenError
  application/
    use_cases/request_magic_link.py    # NUEVO  RequestMagicLink (emisión)
    use_cases/redeem_magic_link.py     # NUEVO  RedeemMagicLink (canje → JwtSession)
  infrastructure/
    repositories/sql_magic_token.py    # NUEVO  SQLMagicTokenRepository(session)
  presentation/
    endpoints/magic_link.py            # NUEVO  POST /auth/magic-link
    endpoints/callback.py              # NUEVO  GET  /auth/callback
    endpoints/me.py                    # NUEVO  GET  /auth/me
    router.py                          # EXISTE → +3 add_api_route
src/common/
    settings.py                        # EXISTE → +MAGIC_LINK_TTL_MINUTES
    infrastructure/dependencies/session.py  # EXISTE → +get_session_user (cookie)
    infrastructure/context_builder.py / dependencies/common.py  # EXISTE → exponer magic_token_repository
templates/email/magic_link.html        # NUEVO  template del correo (messaging)
```

> El ORM `MagicTokenORM`, su registro en `models/__init__.py` y la migración
> Alembic **son propiedad de [06-data-model](../06-data-model/plan.md) §2.5/§2.6** —
> no se duplican aquí. Si 06 no los entregó, son el primer paso bloqueante de §8.

### 2.2 Repositorio de `magic_tokens` (ABC + impl)

`domain/repositories/magic_token.py` (espeja `OTPRepository` / `UserRepository`):

```python
class MagicTokenRepository(ABC):
    async def create(self, *, token_hash: str, email: str, expires_at: datetime) -> None: ...
    async def find_by_hash(self, token_hash: str) -> MagicToken | None: ...     # dominio Pydantic
    async def mark_consumed(self, token_hash: str) -> bool: ...                 # True si pasó NULL→now (atómico)
```

`infrastructure/repositories/sql_magic_token.py` — `@dataclass SQLMagicTokenRepository(session: AsyncSession)`,
mismo patrón que `sql_user.py`. **`mark_consumed` es un UPDATE condicional atómico**
(`UPDATE magic_tokens SET consumed_at=now() WHERE token_hash=:h AND consumed_at IS NULL`)
y devuelve `rowcount == 1`: esto cierra la carrera de **doble-click sobre el enlace**
(dos requests concurrentes; solo uno gana el `consumed_at IS NULL`), sin depender de
un read-then-write.

### 2.3 Endpoints (presentation) y registro en router

| Método | Path | Endpoint | Auth | Respuesta |
|---|---|---|---|---|
| `POST` | `/auth/magic-link` | `magic_link.py:request_magic_link` | No | **siempre 200** `TaskResult.success()` (no filtra existencia) |
| `GET` | `/auth/callback` | `callback.py:callback` | No | **303 redirect** + `Set-Cookie` (ok) · **303 a pantalla error** (token inválido/expirado) |
| `GET` | `/auth/me` | `me.py:me` | Cookie | usuario actual de la sesión (presenter user) |
| `POST` | `/auth/logout` | (existente) | — | limpia cookie/refresh |

Se añaden con `add_api_route()` en `src/auth/presentation/router.py` (mismo estilo que
`/login`, `/refresh`, etc.).

> **El canje vive en el backend, no en el BFF.** El backend emite el JWT y el redirect;
> el BFF de Next (`/api/auth/callback`) es un passthrough fino que **copia el
> `Set-Cookie` del backend a la cookie HttpOnly de Next** (`COOKIE_ACCESS_TOKEN` /
> `COOKIE_REFRESH_TOKEN`, igual que `login/route.ts`) y reescribe el redirect a una
> URL same-origin del frontend. Así la cookie de sesión la setea el **dominio del
> frontend** (requisito de SSE same-origin, §4), no el backend.

### 2.4 Árbol frontend (`frontend/src/`)

```
app/(public)/
  magic-link/page.tsx                  # NUEVO  Pantalla 1: pedir email
  magic-link/check-email/page.tsx      # NUEVO  Pantalla 2: "revisa tu correo" + reenvío
  auth/callback/page.tsx               # NUEVO  Pantalla 3: verificando / ok / error
                                       #        (estados ok|error vienen del query ?status=)
app/api/auth/
  magic-link/route.ts                  # NUEVO  BFF: POST → serverHttp → /auth/magic-link
  callback/route.ts                    # NUEVO  BFF: GET  → /auth/callback, copia Set-Cookie, redirige
  me/route.ts                          # NUEVO  BFF: GET  → /auth/me (reenvía cookie)
infrastructure/repositories/http-auth.ts   # EXISTE → +requestMagicLink(email)
constants.ts                           # EXISTE → +MAGIC_* paths (no cookies nuevas)
proxy.ts                               # EXISTE → +rutas públicas /magic-link, /auth/callback
```

Pantalla 4 ("Sesión") **no es una pantalla**: es el redirect post-canje a
`/dashboard` (watchlist) o al `redirect` pendiente. Lo resuelve el BFF de callback
(§3.4), no un componente.

> **Diseño visual de las 4 pantallas → [13-frontend](../13-frontend/spec.md).** Aquí
> solo se fija el contrato funcional y de navegación; el styling (tokens teal,
> `AuthContainer`, Figtree) lo gobiernan `PRODUCT.md`/`DESIGN.md`. Las pantallas
> reutilizan `AuthContainer` (ya usado por `page.tsx` de login).

## 3. Mecánica del flujo — emisión, canje, cookie, redirect

### 3.1 Emisión — `POST /auth/magic-link` (`RequestMagicLink`)

Espeja `RequestPasswordReset` línea por línea, cambiando el sink:

1. `email_norm = email.strip().lower()`.
2. Genera token plano opaco: **`secrets.token_urlsafe(32)`** (mismo generador que
   `public_reports.token` en 06).
3. `token_hash = hashlib.sha256(token_plano.encode()).hexdigest()` (64 chars hex →
   cuadra con `char(64)` de la PK).
4. `repo.create(token_hash=…, email=email_norm, expires_at = now(UTC) + timedelta(minutes=settings.MAGIC_LINK_TTL_MINUTES))`.
   `consumed_at` queda `NULL` por default del ORM.
5. Despacha `SendEmailCommand(to_emails=[email_norm], subject="Tu enlace para entrar a Owliver",
   template_name="magic_link", context={"magic_url": f"{FRONTEND_HOST}/api/auth/callback?token={token_plano}&redirect={redirect}"})`.
   El enlace apunta al **BFF de Next**, que reenvía al backend (así el `Set-Cookie`
   final lo escribe el dominio del frontend, §3.4).
6. **Siempre** `ApiJSONResponse(TaskResult.success(), 200)` — incluso si no se mandó
   correo (email desconocido → silent success, igual que reset).

> **Anti-spam / cooldown:** el reenvío lo gobierna el cooldown del cliente (Pantalla 2,
> §3.6) **+** una guarda opcional server-side (rate-limit por email usando
> `dependencies/rate_limit.py` existente). El índice/limpieza de tokens viejos es
> housekeeping (riesgo §9), no bloquea el camino feliz.

### 3.2 El plano **nunca** se persiste

Resumen de la postura de seguridad (spec §3, §47–51 de la spec data-model):

- DB guarda **solo** `token_hash`. El plano vive en el correo del usuario y en el
  query-string del enlace; jamás se loguea ni se escribe en la fila.
- Lookup en el canje = `sha256(token_recibido)` → match por PK. Un dump de la DB no
  permite construir enlaces canjeables.

### 3.3 Canje — `GET /auth/callback?token=` (`RedeemMagicLink`)

El use case `RedeemMagicLink` (dataclass `UseCase`) recibe `token`, `magic_token_repository`,
`query_bus`, `token_service`:

1. `token_hash = sha256(token)`; `row = await repo.find_by_hash(token_hash)`.
2. Si `row is None` o `row.consumed_at is not None` o `row.expires_at <= now(UTC)`
   → `raise InvalidOrExpiredMagicTokenError` (DomainError 401). **El chequeo de
   expiración/consumo se hace en Python**, pero el consumo real es atómico (paso 4).
3. (válido) **upsert del `user`**: `user = await query_bus.ask(GetOrCreateUserQuery(email=row.email))`
   — el **mismo `GetOrCreateUserQuery` despachado por el query-bus** que ya usa
   `GoogleSessionBuilder` (`backend/src/auth/application/use_cases/google_session_builder.py:27`,
   `query_bus.ask(...)`). **No es un método de repo** (`UserRepository` no expone
   `get_or_create_by_email`); el upsert vive en `GetOrCreateUserHandler`
   (`src/users/application/queries/get_user.py`). Validar `isinstance(user, User)` como
   hace el builder.
4. `consumed = await repo.mark_consumed(token_hash)`; si `consumed is False` (otro
   request ganó la carrera) → `raise InvalidOrExpiredMagicTokenError`. **Esta es la
   garantía real de 1-uso**, no el read del paso 2.
5. `session = await token_service.generate_token(sub=str(user.uuid), namespace="USER")`
   — el mismo `JwtSession{access,refresh}` que produce el login.
6. Devuelve `(session, user)` al endpoint.

El **endpoint `callback.py`** envuelve el use case:

- **éxito** → `Response(303)` con `Location` a la pantalla de éxito/destino y
  `Set-Cookie` del access+refresh (mismas flags que login). El endpoint sí setea
  cookie en la respuesta del backend; el BFF la re-emite en el dominio del frontend.
- **`InvalidOrExpiredMagicTokenError`** → `303` a `/auth/callback?status=expired`
  (sin cookie). La pantalla 3 lee `status` y muestra el estado "token inválido/expirado".

### 3.4 Cookie HttpOnly + redirect (BFF `app/api/auth/callback/route.ts`)

El correo apunta a `/api/auth/callback?token=…&redirect=…` (BFF de Next). El BFF:

1. `GET` server-side a `serverHttp /auth/callback?token=…` (vía
   `HttpAuthRepository.redeemMagicLink` o fetch directo con `redirect: "manual"`).
2. Si el backend respondió ok con tokens en su payload/`Set-Cookie`: setea
   `COOKIE_ACCESS_TOKEN` y `COOKIE_REFRESH_TOKEN` HttpOnly **exactamente como
   `login/route.ts`** (`secure: Settings.isProd`, `sameSite: "lax"`, `path: "/"`,
   `maxAge: ACCESS/REFRESH_TOKEN_MAX_AGE`) y devuelve `NextResponse.redirect(dest, 303)`
   donde `dest = sanitize(redirect) ?? "/dashboard"`.
3. Si el backend devolvió expirado/inválido → `NextResponse.redirect("/auth/callback?status=expired", 303)`.

`sanitize(redirect)`: solo se acepta **path relativo same-origin** (empieza con `/`,
no `//`, no `http`) para evitar open-redirect. Esto es la "pantalla 4 / sesión": no
hay UI, es el redirect al destino pendiente.

### 3.5 Por qué `SameSite=Lax` y no `Strict`

El redirect del callback es una **navegación top-level** disparada por un click en el
correo (cross-site → frontend). `Lax` permite que la cookie viaje en esa navegación
GET top-level; `Strict` la bloquearía y el usuario llegaría sin sesión. `Lax` además
mitiga CSRF en POSTs cross-site. (Idéntico a la decisión ya tomada para las cookies de
login en `frontend-auth.md`.)

### 3.6 Las 4 pantallas `(public)` — contrato funcional

1. **`/magic-link` (pedir email).** Input email + submit → `fetch("/api/auth/magic-link",
   {method:"POST", body:{email, redirect}})`. Tras 200 → `router.push("/magic-link/check-email?email=…")`.
   No revela existencia (la respuesta es siempre 200). Reutiliza `AuthContainer` + `Field`.
2. **`/magic-link/check-email` (revisa tu correo).** Muestra el email enmascarado,
   botón **"Reenviar enlace"** deshabilitado durante **cooldown** (countdown en
   `useState`/`setInterval`, p.ej. 60 s); al reenviar vuelve a pegar
   `/api/auth/magic-link` y reinicia el cooldown. El cooldown vive en el cliente para
   no permitir spam de correos.
3. **`/auth/callback` (verificando/ok/error).** Server component que lee `?status`:
   sin `status` (el usuario llegó directo del enlace, pero el BFF ya redirigió) →
   estado **verificando** efímero; `status=ok` → breve confirmación + `router.replace(dest)`;
   `status=expired` → estado **token inválido/expirado** con CTA "Pedir un enlace nuevo"
   → `/magic-link`. El canje real ya ocurrió en el BFF; esta pantalla solo refleja el
   resultado.
4. **Sesión (post-login).** No es ruta propia: el BFF de callback redirige a
   `redirect` saneado o `/dashboard`. El usuario aterriza ya con cookie.

## 4. Dependencia de la live-view SSE

La cookie que emite §3.4 es **la dependencia de auth de
[10-realtime-live-view](../10-realtime-live-view/spec.md)**. El stream
`GET /scans/{id}/stream` se sirve con `stream_sse`
(`backend/src/common/infrastructure/sse/streaming.py`); `EventSource` **no** permite
cabeceras `Authorization` personalizadas, así que la ownership-check previa al
`stream_sse(...)` debe leer la **cookie de sesión same-origin** (vía el nuevo
`get_session_user` de §5), no un Bearer. Por eso:

- La cookie se emite en el **dominio del frontend** (BFF, §3.4) → es same-origin con
  el `EventSource` que abre el navegador.
- `SameSite=Lax` + `path:"/"` garantizan que viaje en el GET del stream.

Sin la cookie correcta, el live-view de scans privados no autentica: la emisión aquí
es prerrequisito duro de 10.

## 5. AuthZ por cookie — `get_session_user`

`dependencies/session.py` hoy solo valida `Authorization: Bearer`
(`get_authenticated_user`). El magic-link, `/auth/me` y el stream SSE se autentican
por **cookie**. Se añade (no se reemplaza):

```python
async def get_session_user(request, domain_context, bus_context) -> User:
    token = request.cookies.get(ACCESS_COOKIE_NAME)          # mismo nombre que setea el BFF
    claim = await token_service.get_claims(token, scope=ACCESS)
    ...  # mismas validaciones que get_authenticated_user, devuelve User o 401
```

`SessionUserDep = Annotated[User, Depends(get_session_user)]`. Lo consumen `/auth/me`,
el stream de 10 y los endpoints privados de watchlist/scans activos
([12-api](../12-api/spec.md) §14.2). Las reglas finas de authZ (404-en-vez-de-403,
UUID no enumerable, `visibility`) son propiedad de 12-api; aquí solo se provee la
identidad de sesión.

> **Límite de alcance (recordatorio para revisor/implementador).** Este plan **solo
> emite y valida la identidad de sesión** (`get_session_user` → `User`). El aislamiento
> multi-tenant real de la spec §5 —**404-en-vez-de-403** para recursos privados ajenos,
> `visibility ENUM(public, private)`, UUIDv4 no enumerable, ownership por
> `watchlist.user_id` / `owner_user_id`— **se valida en [12-api](../12-api/spec.md) §5**,
> no aquí (la propia spec §5 lo declara propiedad de 12-api). No es un hueco de este plan:
> es delegación deliberada. Quien implemente un endpoint privado **no** debe asumir que
> `get_session_user` ya filtra por dueño; solo dice *quién* es el usuario, no *qué* puede ver.

## 6. Suite de tests

Convención del repo: `backend/tests/<área>/...`, pytest, librería **`expects`**,
funciones standalone, AAA, fixtures por función; repos async contra la DB de test
(`tests/conftest.py`, DB `doxiq_test`, `create_all` sobre `Base.metadata`). Frontend:
vitest/testing-library.

| Archivo | Capa | Asserts |
|---|---|---|
| `backend/tests/auth/application/test_request_magic_link.py` | use case (mock repo+bus) | genera `token_urlsafe`, persiste `sha256` (no el plano), `expires_at = now+TTL`; email desconocido ⇒ **no** despacha `SendEmailCommand` y **no** lanza (silent success); el `magic_url` contiene el token plano. |
| `backend/tests/auth/application/test_redeem_magic_link.py` | use case (mock repo + mock query_bus) | token válido ⇒ `query_bus.ask(GetOrCreateUserQuery(email=row.email))` (upsert user) + `generate_token` + `mark_consumed`; consumido ⇒ `InvalidOrExpiredMagicTokenError`; expirado ⇒ misma excepción; segundo canje (mark_consumed→False) ⇒ excepción. |
| `backend/tests/auth/infrastructure/test_sql_magic_token.py` | repo (DB) | `create`+`find_by_hash` round-trip; `mark_consumed` pasa `NULL→now` y devuelve True; segunda llamada devuelve **False** (atomicidad 1-uso); `find_by_hash` de hash inexistente ⇒ None. |
| `backend/tests/auth/presentation/test_magic_link_endpoint.py` | E2E HTTP | `POST /auth/magic-link` con email válido e inválido ⇒ **ambos 200** `TaskResult.success` (no filtra existencia); no expone token en la respuesta. |
| `backend/tests/auth/presentation/test_callback_endpoint.py` | E2E HTTP | canje válido ⇒ **303** + `Set-Cookie` access/refresh (HttpOnly, Lax); token expirado/consumido ⇒ 303 a `?status=expired` **sin** `Set-Cookie`; replay del mismo token ⇒ no re-emite cookie. |
| `backend/tests/auth/presentation/test_session_cookie_dep.py` | E2E HTTP | `get_session_user` autentica con cookie válida; cookie ausente/expirada ⇒ 401; `/auth/me` devuelve el user de la cookie. |
| `frontend/src/app/(public)/magic-link/page.test.tsx` | vitest/RTL | submit pega `/api/auth/magic-link` y navega a `check-email`; valida formato de email; no muestra "email no existe". |
| `frontend/src/app/(public)/magic-link/check-email/page.test.tsx` | vitest/RTL | botón reenviar deshabilitado durante cooldown; al expirar se habilita y re-pega el endpoint. |
| `frontend/src/app/api/auth/callback/route.test.ts` | vitest (BFF) | ok del backend ⇒ setea cookies HttpOnly y `redirect` saneado; `redirect` absoluto/`//` ⇒ cae a `/dashboard`; expirado ⇒ redirige a `?status=expired` sin cookies. |

Los tests de authZ por endpoint privado (watchlist/scans, 404-vs-403, paginación)
viven en [12-api](../12-api/spec.md); aquí se cubre emisión, canje, cookie y sesión.

## 7. Contrato HTTP (resumen, dueño = 12-api)

El contrato completo de `/auth/callback`, `/auth/logout`, `/auth/me` es propiedad de
[12-api](../12-api/spec.md). Lo que esta feature congela:

- `POST /auth/magic-link` → siempre `200 {data:{status:"success"}}`.
- `GET /auth/callback?token=&redirect=` → `303` (Location + Set-Cookie en ok;
  Location `?status=expired` sin cookie en fallo).
- `GET /auth/me` → `200 {data: user}` con cookie válida; `401` sin ella.

## 8. Secuencia de build

1. **Bloqueante + assert de contrato:** confirmar que `MagicTokenORM` + su registro en
   `models/__init__.py` + la migración existen ([06-data-model](../06-data-model/plan.md)
   §2.5/§2.6). Si no, crearlos primero ahí (no en este módulo). **Antes de construir el
   repo, verificar que el ORM expone exactamente los campos que este plan consume**
   (06-data-model §2.5 los define así): `token_hash` **PK `char(64)`** (sha256 hex,
   nunca el plano), `email`, `expires_at`, `consumed_at` **nullable**, `created_at`.
   `find_by_hash` lee por PK; `mark_consumed` hace `UPDATE ... SET consumed_at=now()
   WHERE token_hash=:h AND consumed_at IS NULL`. Si cualquier campo difiere (tipo de PK,
   `consumed_at` no-nullable, falta `expires_at`), parar: el contrato lo fija 06, no se
   parchea aquí.
2. **Repo** `MagicTokenRepository` (ABC) + `SQLMagicTokenRepository` con
   `mark_consumed` atómico. Test de repo (§6).
3. **Settings** `MAGIC_LINK_TTL_MINUTES`; excepción `InvalidOrExpiredMagicTokenError`;
   wiring del repo en `context_builder`/`dependencies/common`.
4. **Use cases** `RequestMagicLink` (copia de `RequestPasswordReset`) y
   `RedeemMagicLink`; template `magic_link.html` en messaging. Tests de use case (§6).
5. **Endpoints** `magic_link.py`, `callback.py`, `me.py` + `add_api_route` en
   `router.py`; `get_session_user` en `dependencies/session.py`. Tests E2E (§6).
6. **Frontend BFF** `/api/auth/magic-link`, `/api/auth/callback`, `/api/auth/me`
   (molde `login/route.ts`); `requestMagicLink` en `http-auth.ts`; rutas públicas en
   `proxy.ts`. Test de BFF callback (§6).
7. **Pantallas** `(public)/magic-link`, `check-email`, `auth/callback` (reutilizan
   `AuthContainer`; visual gobernado por 13-frontend). Tests RTL (§6).
8. **Verificación cruzada con 10:** el stream `/scans/{id}/stream` autentica con la
   cookie emitida aquí (smoke same-origin).

`implemented`/coverage>0 cuando: el canje emite la cookie correcta, el doble-canje
falla, `POST /auth/magic-link` no filtra existencia, y toda la suite del §6 pasa.

## 9. Decisiones y riesgos abiertos

1. **Clerk vs casero** — resuelto para este plan: **casero** sobre `src/auth/`. Clerk
   queda como alternativa documentada (spec §2); si se adopta, las 4 pantallas y el BFF
   se reemplazan por sus widgets y este plan aplica solo a la columna de datos.
2. **Tabla vs JWT scoped** — resuelto: **tabla `magic_tokens`** (no `create_one_shot_token`
   como reset) porque la spec §3 exige `consumed_at` persistente (1-uso a prueba de
   replay) y `token_hash` auditable. Coexisten dos mecanismos a propósito.
3. **1-uso = `mark_consumed` atómico**, no el read previo — la garantía real contra
   doble-click es el `UPDATE ... WHERE consumed_at IS NULL` con `rowcount==1`; el chequeo
   en Python (§3.3 paso 2) es solo para el mensaje de error temprano.
4. **Cookie la setea el dominio del frontend** (vía BFF), no el backend — requisito de
   SSE same-origin (§4). El `Set-Cookie` del backend es interno server-to-server.
5. **Open-redirect** — `redirect` se sanea a path relativo same-origin en el BFF
   (§3.4). Riesgo si alguien lo salta; cubierto por test.
6. **Upsert de `users` en el canje** — un email nuevo crea cuenta en el primer canje
   (reusa `GetOrCreateUserQuery` vía `query_bus.ask(...)`, no un método de repo).
   Implica que el magic-link es **registro + login** a la vez; aceptable y deseado para
   el flujo anónimo→sesión de la spec §1.
7. **Housekeeping de tokens** — la limpieza de filas expiradas/consumidas (cron o TTL
   index) es deuda menor; no bloquea. Riesgo: crecimiento de tabla si no se barre.
8. **TTL 10 min** — hardcode default en settings; corto a propósito (spec §3). Si el
   correo tarda, el usuario re-pide enlace (cooldown lo permite tras 60 s).
9. **DB de test `doxiq_test`** (herencia del base vnext) — los tests nuevos cuelgan del
   `conftest`/`Base.metadata` existentes; no se toca.
