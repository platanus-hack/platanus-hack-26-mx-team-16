---
feature: realtime-live-view
type: spec
status: pending
coverage: 0
audited: 2026-06-20
sources: spec.md §12.1; spec-gaps.md §4 (§4.1, §4.2)
---

# Owliver — Live view del pentest (SSE, replay-then-tail)

> El live view es el momento estrella del pitch: el usuario manda un sitio, arranca el scan y entra a "ver en vivo" cómo el equipo de agentes audita el target en tiempo real. El reto técnico es que Redis pub/sub es **at-most-once y sin replay**, así que quien abre el stream tarde (form → scan → click "ver en vivo") perdió todo lo previo y se queda con la pantalla vacía justo cuando todos miran. La solución: la **verdad vive en Postgres** (`scan_events`), el pub/sub es **solo el canal de tail**, y el endpoint hace **replay-then-tail** sobre un esquema de eventos tipado con `seq` monótono por scan como única fuente de orden.

## 1. Modelo: Postgres es la verdad, Redis es solo el tail

Redis pub/sub entrega **at-most-once y sin replay**: un suscriptor que se conecta tarde no recibe nada de lo publicado antes de su `SUBSCRIBE`. Para el live view esto es inaceptable, porque el flujo natural del usuario (rellenar el formulario, lanzar el scan, hacer click en "ver en vivo") introduce un retraso de varios segundos durante los cuales el worker ya emitió eventos. Si dependiéramos solo del pub/sub, esos eventos se perderían y la pantalla aparecería vacía.

Por eso:

- **La verdad vive en Postgres.** La tabla `scan_events` es el registro autoritativo y ordenado de todo lo que ocurre en un scan. **`scan_events` deja de ser opcional**: es obligatoria y se persiste íntegramente.
- **Redis pub/sub es solo el canal de tail.** El canal `scan:{id}:events` transporta los eventos nuevos a los suscriptores ya conectados, pero nunca es la fuente de verdad ni de orden.
- **Orden de escritura:** cada evento se **persiste en Postgres ANTES de publicarse** en el canal Redis. Esta secuencia (PG primero, Redis después) garantiza que cualquier evento que un cliente vea por tail también esté ya disponible para replay; nunca al revés.

Se reusa el patrón ya probado en este repo (`workflows/.../event_replayer.py`, cursor `since_seq` sobre PG): el replay desde Postgres por cursor `since_seq` es el mecanismo conocido que aquí se aplica a `scan_events`.

La definición de columnas de la tabla `scan_events` pertenece al modelo de datos; ver [06-data-model](../06-data-model/spec.md).

## 2. Esquema de evento tipado

Cada evento emitido durante un scan tiene la forma (persistido en `scan_events`):

```
{ seq:int, type, agent, tool?, severity?, message, ts, payload? }
```

Reglas del esquema:

- **`seq`** es un entero **monótono por scan** y es la **única fuente de orden**. No se infiere el orden del timestamp ni del orden de llegada por Redis: solo `seq` ordena. Cada carril que emite eventos (el worker y los subagentes OWASP y agéntico) produce `seq` creciente.
- **`type`** es el **discriminador** que mapea evento → UI. Los valores válidos son:

```
agent_status | tool_start | tool_end | finding
             | phase | score | done | error
```

- **`agent`** identifica el carril emisor (worker, subagente OWASP, subagente agéntico).
- **`tool?`** (opcional) la herramienta involucrada, presente típicamente en `tool_start` / `tool_end`.
- **`severity?`** (opcional) presente en `finding`.
- **`message`** texto legible del evento.
- **`ts`** timestamp del evento.
- **`payload?`** (opcional) carga estructurada específica del tipo.
- **`progress?`** (opcional, `0–100`) porcentaje de avance del scan; presente en eventos `phase` (y opcionalmente `score`) para alimentar la **barra de progreso 0–100** del header del theater. Si un `phase` no lo trae, el front mantiene el último valor conocido.

Semántica por discriminante relevante:

- **`score`** lleva el `web_score` / `agentic_score` **parcial**, para actualizar los gauges en vivo conforme avanza el scan.
- **`finding`** lleva **severidad + categoría** (en `severity` / `payload`) para insertar el hallazgo en vivo en la UI.
- **`done`** marca el cierre del scan y lleva en su `payload` un `outcome: success | cancelled` — la **cancelación** se señala como `done` con `{outcome: 'cancelled'}`, **no** como un `type` aparte (ver [12-api](../12-api/spec.md) `POST /scans/{id}/cancel`); **`error`** marca un cierre con error. Ambos son terminales para el stream.

El esquema con discriminador resuelve el problema de que un `scan_events` de texto plano sin `type` no permite al front mapear evento → componente de UI.

## 3. Endpoint `GET /scans/{id}/stream`: replay-then-tail

Al conectarse un cliente, el endpoint `GET /scans/{id}/stream` ejecuta tres pasos en orden:

1. **Lee el cursor.** Toma el cursor de reconexión desde el header `Last-Event-ID` (que `EventSource` reenvía automáticamente al reconectar) o del query param `?since_seq=`. Si no hay cursor, el cursor es 0 (replay completo desde el inicio del scan).
2. **Replay desde Postgres.** Lee de `scan_events` todos los eventos con `seq > cursor` y los emite por SSE con su `id:` SSE igual a `seq`. Esto reconstruye todo lo que el cliente se perdió antes de conectarse (o entre la desconexión y la reconexión).
3. **Subscribe + tail.** Se suscribe al canal Redis `scan:{id}:events` y hace **tail** de los eventos nuevos conforme se publican.

Como cada evento SSE emitido lleva `id: {seq}`, el navegador rastrea el último `seq` visto y lo reenvía como `Last-Event-ID` en cualquier reconexión, cerrando el ciclo de replay sin pérdida.

El contrato HTTP completo del endpoint (parámetros, códigos, headers) lo define la capa de API; ver [12-api](../12-api/spec.md).

### 3.1 Idempotencia de cliente

El front descarta cualquier evento con `seq <= lastSeq` ya visto. Esto cubre el solape natural entre el final del replay y el inicio del tail (un evento que entró al canal Redis justo mientras se leía el cursor de Postgres puede llegar por ambos caminos): el cliente lo deduplica por `seq` y nunca lo procesa dos veces.

### 3.2 Heartbeat y compresión desactivada

- **Heartbeat:** se emite un comentario SSE (`:` heartbeat) cada **~20s** para mantener viva la conexión y detectar cortes.
- **Compresión desactivada en esta ruta.** Next.js bufferea/comprime SSE y solo flushea al final si no se desactiva la compresión, lo que rompe el streaming en vivo (el cliente no recibe nada hasta que el scan termina). La compresión debe estar **explícitamente desactivada** en la ruta SSE para que cada evento se flushee de inmediato.

## 4. Auth por cookie (no por header)

`EventSource` **no permite headers custom**, por lo que el esquema JWT-en-header del resto de la API **no aplica al SSE**. El flujo de auth del stream es por cookie:

- El callback del magic-link setea una **cookie HttpOnly** con `SameSite=Lax`. La emisión de esa cookie pertenece al flujo de magic-link; ver [11-auth-magic-link](../11-auth-magic-link/spec.md).
- El cliente abre el stream con `new EventSource(url, { withCredentials: true })`, lo que adjunta la cookie a la petición same-origin.
- La ruta valida la cookie vía `Depends`.

Para scans **privados**, el stream **nunca queda abierto sin auth** (no se permite fuga del progreso de un scan privado a un cliente no autenticado, ni dejar el stream colgado). Como **alternativa rápida** para scans privados existe un **token efímero de un solo uso en query** (`?stream_token=`), útil cuando no se quiere depender de la cookie.

## 5. Demo level: perfil rápido con timeout duro

El live view del pitch corre solo un **perfil rápido** para que la audiencia vea avance real en pantalla en segundos:

- Nuclei subset + testssl + **1 probe** contra el bot propio.
- **Timeout duro de ~60–90s** sobre ese perfil de demo.
- ZAP full / garak / hexstrike **no** se corren en vivo en el pitch: se muestran desde resultados ya almacenados (fixtures), para que la pantalla tenga densidad sin pagar el costo de tiempo de los scanners pesados.

Ver las restricciones de concurrencia y límites de recursos en spec.md (overview, §5 «Concurrencia y límites de recursos» / §10 / §15).

## 6. Renderizado en el front

La UI del live view (el "theater": cómo se dibujan los carriles de agentes, los `tool_start`/`tool_end`, los findings en vivo y los gauges de score parcial) la define la capa de frontend; ver [13-frontend](../13-frontend/spec.md). Este subspec solo fija el **contrato de transporte**: el esquema tipado, el orden por `seq`, el replay-then-tail, la idempotencia de cliente, el heartbeat, la compresión desactivada y la auth por cookie.
