---
feature: auth-magic-link
type: spec
status: pending
coverage: 0
audited: 2026-06-20
sources: spec.md §12.2, §14.1 (§14 endpoints, §14.2 authZ); spec-gaps.md §5.4
---

# Owliver — Auth magic-link (flujo + sesión)

> Owliver es mayormente anónimo: el leaderboard, `/sites/{id}`, el reporte público `/r/{token}` y el scan **básico** no exigen login. Solo **watchlist/monitoreo** y los **scans activos** (intermedio/avanzado) requieren sesión. La autenticación es un flujo **magic-link sin contraseña**: el usuario pide un enlace por email, lo canjea desde su bandeja, y el callback emite una cookie HttpOnly con un JWT. Esta spec define la decisión de superficie (anónimo vs sesión), las 4 pantallas/rutas en el route-group `(public)` reutilizando el patrón BFF `/api/auth/*`, y el ciclo de vida de la tabla `magic_tokens`. La cookie HttpOnly emitida aquí es la base sobre la que se autentica la live-view SSE (ver [10-realtime-live-view](../10-realtime-live-view/README.md)).

## 1. Decisión de superficie: anónimo vs sesión

El producto se diseña para minimizar la fricción de descubrimiento: el valor de marca (el ranking de `.gob.mx`, los reportes públicos) debe ser consumible **sin registro**. La sesión solo se exige donde hay datos del usuario o acciones que tocan infraestructura ajena de forma activa.

**Superficies anónimas (sin login):**

- Leaderboard / ranking global gov (`GET /ranking?country=mx`).
- Detalle de sitio `/sites/{id}` (último escaneo + histórico).
- Reporte público `/r/{token}` (redactado, exploits ocultos por defecto — ver [09-reporting](../09-reporting/README.md)).
- El **scan básico** (pasivo): cualquiera puede lanzar un escaneo de nivel básico contra un sitio sin estar autenticado.

**Superficies que exigen sesión:**

- **Watchlist / monitoreo** (`GET/POST/DELETE /watchlist`): son los sitios del usuario, multi-tenant por `watchlist.user_id`.
- **Scans activos** (intermedio/avanzado): exigen además el gate de autorización (checkbox `authorized=true`). El nivel activo crea scans `private` con `owner_user_id` = el usuario de la sesión (ver §4 y [02-attack-levels](../02-attack-levels/README.md)).

Esta separación es la razón por la que el flujo magic-link es **opcional en el camino feliz** del pitch (un visitante puede ver el ranking y lanzar un scan básico sin tocar auth) y solo se vuelve obligatorio al guardar un sitio en la watchlist o al pedir un scan activo.

## 2. Las 4 pantallas/rutas en `(public)`

El repo base trae auth por **contraseña**, no magic-link; estas 4 pantallas hay que construirlas desde cero. Viven en el route-group **`(public)`** (layout propio: logo Owliver + CTA "Escanear mi sitio", sin sidebar) y **reutilizan el patrón BFF `/api/auth/*`** ya existente en el repo. **Decisión:** si Clerk está disponible se usa Clerk (magic-link out-of-the-box); si no, se implementan estas 4 rutas a mano. El diseño visual de las pantallas pertenece a [13-frontend](../13-frontend/README.md); aquí se define únicamente su contrato funcional y de navegación.

1. **Pedir email** — input de email + botón de envío → `POST /auth/magic-link`. El endpoint solo **envía** el correo; no abre sesión ni revela si el email existe.
2. **"Revisa tu correo"** — pantalla de confirmación tras el envío, con **cooldown/reenvío** (el botón de reenviar queda deshabilitado durante el cooldown para no permitir spam de correos).
3. **Callback / verify** — landing de `GET /auth/callback?token=`, con tres estados visibles: **verificando**, **ok** (token válido y canjeado) y **token inválido/expirado**.
4. **Sesión** — estado post-login: la cookie **HttpOnly** ya quedó seteada por el callback y se redirige a la **watchlist** o al **destino pendiente** (el `redirect` que originó el login; p. ej. el usuario intentaba guardar un sitio en la watchlist sin sesión).

El cliente nunca llama al backend directamente: cada pantalla pega contra su ruta BFF (`/api/auth/magic-link`, `/api/auth/callback`, etc.), que es donde se setean/leen las cookies HttpOnly y se inyecta la `X-Api-Key`. El contrato HTTP completo de `/auth/callback`, `/auth/logout` y `/auth/me` se especifica en [12-api](../12-api/README.md); las columnas de `magic_tokens` en [06-data-model](../06-data-model/README.md).

## 3. Ciclo de vida de `magic_tokens` y canje

El flujo separa **envío** de **canje**: `POST /auth/magic-link` solo envía el enlace por correo; el canje ocurre en `GET /auth/callback?token=`.

**Tabla.** `magic_tokens(token_hash PK, email, expires_at, consumed_at NULL, created_at)`. Se guarda el **SHA256 del token**, **nunca** el token plano — si la base de datos se filtra, los hashes no son canjeables.

**Token.** Opaco, de **1 uso**, con TTL de **10 min**.

**Emisión (`POST /auth/magic-link`).** Genera un token opaco aleatorio, guarda su `SHA256` como `token_hash` con `email`, `expires_at = now + 10min` y `consumed_at = NULL`, y envía por correo el enlace que apunta a `GET /auth/callback?token=<token-plano>`. La respuesta al cliente es indistinguible exista o no el email (no se confirma existencia de cuenta).

**Canje (`GET /auth/callback?token=`).** El callback:

1. Calcula `SHA256(token)` y busca la fila por `token_hash`.
2. Verifica que esté **no consumido** (`consumed_at IS NULL`) y **no expirado** (`expires_at > now`). Si falla cualquiera → estado "token inválido/expirado" (la pantalla de callback lo muestra como tal).
3. Marca `consumed_at = now` (un solo uso: un segundo canje del mismo token falla por este chequeo).
4. Hace **upsert** en `users` con el `email`.
5. Setea una cookie **HttpOnly SameSite=Lax** con un **JWT** y **redirige** (a la watchlist o al destino pendiente).

`POST /auth/logout` limpia la cookie; `GET /auth/me` devuelve el usuario actual de la sesión.

## 4. Cookie HttpOnly y dependencia de la live-view SSE

El callback emite la sesión como una cookie **HttpOnly, SameSite=Lax** que transporta un **JWT**. Las propiedades importan:

- **HttpOnly**: el JavaScript del navegador no puede leer el token; mitiga robo de sesión vía XSS.
- **SameSite=Lax**: la cookie viaja en navegaciones top-level (incluido el redirect del callback) pero no en requests cross-site de terceros.

Esta cookie es **la dependencia de autenticación de la live-view SSE**: el stream `GET /scans/{id}/stream` (replay-then-tail) se autentica con la misma cookie de sesión, porque `EventSource` no permite cabeceras `Authorization` personalizadas y depende del envío automático de cookies same-origin. Por eso la emisión correcta de la cookie aquí es prerequisito del live-view de scans privados (ver [10-realtime-live-view](../10-realtime-live-view/README.md)).

## 5. Multi-tenant y aislamiento

La sesión identifica al `user` que es propietario de los recursos privados:

- **Watchlist**: cada sitio guardado pertenece a su dueño vía `watchlist.user_id`; `GET /watchlist` lista solo los del usuario de la sesión.
- **Scans activos / sitios con dueño**: un scan `private` (intermedio/avanzado, o un sitio con `owner_user_id`) solo es accesible por su **owner** (o por quien lo tenga en su watchlist). Sin permiso, `GET /scans/{id}` y `GET /scans/{id}/findings` devuelven **404** (no 403, para no confirmar la existencia del recurso).

Las reglas de authZ por endpoint (UUIDv4 no enumerable, `visibility ENUM(public, private)`, 404-en-vez-de-403, reporte público solo vía `/r/{token}`) son propiedad de [12-api](../12-api/README.md) y se resumen aquí solo en lo que toca a la identidad de sesión que esta spec emite.
