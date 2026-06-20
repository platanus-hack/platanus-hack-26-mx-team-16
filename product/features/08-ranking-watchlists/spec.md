---
feature: ranking-watchlists
type: spec
status: pending
coverage: 0
audited: 2026-06-20
sources: spec.md §10, §12 (swing #1), §9.2–§9.4; spec-gaps.md §5.1, §6.1, §6.6, §6.7, §6.8, §6.11, §7.1, §7.2, §7.3
---

# Owliver — Ranking público gov + watchlists + monitoreo/alertas

> Este subspec define las tres superficies "de continuidad" de Owliver: el **ranking público de sitios `.gob.mx`** (un leaderboard sembrado con ~30–50 dominios auto-escaneados en modo pasivo según un cron, que muestra **solo** resultados pasivos), las **watchlists privadas** (un usuario marca `monitor=true` sobre sus dominios para re-escaneos periódicos), y el **monitoreo recurrente + alertas** que reencola watchlist y seed gov vía el cron nativo de Arq y notifica por **Resend** (email) y/o **Slack webhook** cuando el grado de un sitio baja o aparece un finding `critical`, comparando identidad de findings a nivel sitio vía `dedupe_key` / `first_seen`. Incluye además la estrategia de **fixtures pre-horneados** del leaderboard para que la primera pantalla del demo nunca aparezca vacía.

## 1. Ámbito y fronteras

Este subspec es dueño de la **lógica de negocio** del ranking, de las watchlists y del scheduler/alertas. No redefine contratos que pertenecen a otros subspecs; los referencia:

- El **invariante legal "solo pasivo en el board público"** (por qué el leaderboard nunca expone resultados de un escaneo activo) lo fija [01-legal-ethics](../01-legal-ethics/spec.md). Aquí se aplica, no se justifica.
- La **fórmula de scoring, los grados y el orden/desempate** del leaderboard son autoridad de [07-scoring](../07-scoring/spec.md). Aquí se consume `(overall_grade, penalty_raw)` y se cita la regla de orden.
- Las **tablas `sites`, `scans`, `findings`, `watchlist`, `public_reports`** y sus columnas (`is_gov`, `monitor`, `visibility`, `dedupe_key`, `first_seen`/`last_seen`, `coverage`, `penalty_raw`) las define [06-data-model](../06-data-model/spec.md). Aquí se describen solo los campos que esta feature lee/escribe.
- La **UI** del leaderboard público (`/`), de `/sites/[id]` y del dashboard de watchlist vive en [13-frontend](../13-frontend/spec.md).
- Los **endpoints HTTP, los healthchecks y el contrato de los jobs de cron** los formaliza [12-api](../12-api/spec.md). Aquí se describe el comportamiento que esos endpoints/jobs disparan.
- El **worker/agente** que ejecuta cada escaneo está en [05-agent-team](../05-agent-team/spec.md). Aquí solo se encolan jobs.

Estado general del producto en spec.md (overview).

## 2. Ranking público de sitios `.gob.mx`

### 2.1 Qué es

El ranking global vive en la raíz pública (`/`) y es un **leaderboard de `sites WHERE is_gov=true`**, filtrable por país (MX). Es la primera pantalla del pitch: tiene que estar poblada desde el minuto 0.

**Orden (autoridad: [07-scoring](../07-scoring/spec.md) §9.4):** el leaderboard **no ordena por `overall_score`** sino por:

```
ORDER BY overall_grade ASC, penalty_raw DESC
```

es decir, **peores primero**, con desempate por penalización cruda. El cap `min(100, penalty_raw)` colapsa a 0/F a cualquier sitio con ~3 criticals, dejando decenas de `.gob.mx` empatados; por eso `scans.penalty_raw` se persiste **sin clamp** y la fila muestra `penalty_raw` (o el conteo ponderado) para que el contraste entre sitios en F sea visible. El ranking nunca muestra **A** con cobertura parcial: cuando `scans.status='partial'` el grado se capa en **C** y la fila lleva la etiqueta "cobertura parcial" (ver [07-scoring](../07-scoring/spec.md) §9.2–§9.3).

### 2.2 Invariante de solo-pasivo

El board público muestra **únicamente resultados de escaneos pasivos/básicos**. Cualquier URL que un usuario envíe **en nivel pasivo/básico** entra también al ranking global; los resultados de un escaneo **activo** (intermedio/avanzado) quedan **privados** de la cuenta del usuario y solo se publican si éste genera un link público explícito (`/r/[token]`). Operativamente esto se expresa con `scans.visibility`: los escaneos gov básico/pasivo son `public`; intermedio/avanzado o sites con `owner_user_id` son `private` y nunca entran al ranking. El razonamiento legal está en [01-legal-ethics](../01-legal-ethics/spec.md).

### 2.3 Seed de dominios gov

Un archivo `seed/gob_mx.txt` contiene ~30–50 dominios `.gob.mx` (gob.mx, SAT, IMSS, INE, IMPI, Salud, Banxico, gobiernos estatales…). Un job de arranque:

1. Inserta cada dominio como `sites(is_gov=true)`.
2. Encola escaneos **nivel básico** (pasivos) para cada uno.

Así el leaderboard queda poblado desde el minuto 0 del demo. El re-escaneo periódico de este seed lo gestiona el scheduler (§4).

### 2.4 Estrategia de fixtures pre-horneados (anti-leaderboard-vacío)

El seeding real es lento: corre escaneos contra ~30–50 dominios reales, dependientes de red/WAF, y puede tardar horas. El leaderboard ES la primera pantalla del pitch; vacío o lleno de filas `failed` hunde la narrativa antes de empezar. Por eso la estrategia es de **dos capas**, decidida desde el inicio (no en la hora 14):

1. **Fixtures pre-horneados.** Un seed SQL/JSON de fixtures con **30–50 filas** `sites` + `scans` + `findings` con grados pre-calculados y un par de findings agénticos plantados (p. ej. SAT con **"C web / F agéntico"**, para exhibir la narrativa del doble score). Se carga en bloque vía el CLI de fixtures al arrancar.
2. **Sobrescritura por scans reales.** Los escaneos reales gob.mx corren en background y **sobrescriben** las filas sembradas **solo si terminan a tiempo**. Si no terminan, el demo usa los fixtures.

Esta capa garantiza que el board siempre tenga 30–50 filas coherentes con grados A–F bien distribuidos, sin importar el estado de la red del venue. Los scans reales del seed se pre-ejecutan **en el VPS** antes del demo, no contra la wifi del venue (ver [12-api](../12-api/spec.md) / contexto de deploy en spec.md overview).

## 3. Watchlists privadas

Una watchlist es la superficie privada equivalente al ranking: un usuario agrega su(s) dominio(s), puede correr niveles activos (con autorización explícita; ver el gate en [01-legal-ethics](../01-legal-ethics/spec.md)) y activar `monitor=true` por sitio para re-escaneos periódicos.

- Cada entrada de watchlist pertenece a un usuario (`watchlist.user_id`); el aislamiento multi-tenant y la authz se rigen por [06-data-model](../06-data-model/spec.md) y [12-api](../12-api/spec.md). Un sitio en watchlist con `owner_user_id` produce scans `visibility=private`: nunca aparece en el ranking público.
- `monitor=true` es la única señal que esta feature lee para decidir si un sitio de watchlist entra al cron de re-escaneo (§4).
- La UI del dashboard de watchlist (tabla hostname + grado + 🛡️/🤖 + último scan + Switch monitor + re-scan), `DELETE /watchlist/{id}` y `/sites/[id]` los cubren [13-frontend](../13-frontend/spec.md) y [12-api](../12-api/spec.md).

## 4. Monitoreo recurrente

### 4.1 Scheduler: cron nativo de Arq (NO rq-scheduler)

El monitoreo recurrente lo conduce un **scheduler basado en el cron nativo de Arq**. Owliver fija **Arq** (asyncio nativo) como cola/worker porque el worker hace `asyncio.gather` sobre scanners concurrentes; RQ es síncrono y no sirve. En consecuencia, el re-encolado periódico se hace con **cron de Arq**, **no** con `rq-scheduler` (esto cierra el fix M2: nada de rq-scheduler).

> spec.md §12 menciona "APScheduler o cron nativo de Arq" como alternativas; este subspec resuelve a favor del **cron nativo de Arq** para no introducir un proceso scheduler extra y mantener una sola cola Arq como fuente de verdad.

El cron reencola, periódicamente:

1. Los escaneos de **`watchlist.monitor=true`** (nivel según la autorización del owner).
2. Los escaneos del **seed gov** (nivel básico/pasivo).

Cada re-encolado pasa por la **misma idempotencia** que `POST /scans` para no lanzar duplicados: partial unique index `scans(site_id, level) WHERE status IN ('queued','running')` (el 2º encolado devuelve el `scan_id` existente) + `job_id` de Arq derivado de `site_id+level`. Detalle del contrato de idempotencia en [12-api](../12-api/spec.md) y [06-data-model](../06-data-model/spec.md).

### 4.2 Detección de cambios a nivel sitio

El monitoreo decide si **disparar una alerta** comparando el resultado del nuevo scan contra el histórico del sitio. La identidad estable de un finding es su **`dedupe_key`**:

```
dedupe_key = sha256(site_id + source + category + normalize(affected_url) + param + tool)
```

`first_seen` / `last_seen` se llevan a nivel **site** (no scan), con índice `findings(site_id, dedupe_key)`. Un re-scan hace **UPSERT por `(site_id, dedupe_key)`**:

- Un `dedupe_key` que **no existía** en el histórico del sitio → **finding nuevo** (`first_seen = now`).
- Un `dedupe_key` previo que **no reaparece** en el nuevo scan → se marca `status='fixed'`.

Las dos señales que disparan alerta (§5) son:

1. **Bajó el grado** del sitio respecto al scan anterior (comparando `overall_grade`).
2. **Apareció un finding `critical` nuevo** (un `dedupe_key` con severidad `critical` cuyo `first_seen` es el de este scan).

La definición canónica de `dedupe_key`, `first_seen`/`last_seen` y `status='fixed'` vive en [06-data-model](../06-data-model/spec.md); aquí solo se consume para decidir alertas.

## 5. Alertas

### 5.1 Canales: Resend (email) y/o Slack webhook

Cuando el monitoreo detecta una de las señales de §4.2, emite una alerta por uno o ambos canales:

- **Resend** — email transaccional.
- **Slack webhook** — POST a la URL de webhook configurada.

**Alertas in-app = recorte.** No se construye un centro de notificaciones dentro de la app; solo email/Slack. Esto mantiene el alcance acotado para el demo.

### 5.2 Disparadores

Una alerta se genera cuando, tras un re-escaneo de monitoreo, ocurre cualquiera de:

- **El grado del sitio baja** (p. ej. de B a D entre dos scans consecutivos del mismo `site_id`).
- **Aparece un finding `critical` nuevo** (nuevo `dedupe_key` con severidad `critical` cuyo `first_seen` corresponde a este scan).

La comparación es siempre **a nivel site** vía `dedupe_key` / `first_seen`, de modo que un mismo `critical` que ya existía no vuelve a alertar en cada ciclo: solo los **nuevos** (o las **caídas de grado**) disparan notificación.

### 5.3 Contenido de la alerta

La alerta identifica el sitio (hostname), el grado anterior → nuevo, y la lista de findings `critical` nuevos (tipo + categoría + severidad + `impact` resumido). **Nunca** debe incluir el payload de explotación crudo (mismo principio de redacción que el reporte público `/r/[token]`): el canal de alerta no es lugar para filtrar exploits reales contra el sitio del usuario.

## 6. Resumen de comportamiento (qué dispara qué)

| Disparador | Origen | Efecto |
|---|---|---|
| Arranque del demo | Job de seed | Inserta ~30–50 `sites(is_gov=true)` + encola scans básicos; fixtures pre-horneados pueblan el board ya |
| Scan real gov termina a tiempo | Worker | **Sobrescribe** la fila sembrada del sitio en el leaderboard |
| Scan real gov no termina a tiempo | — | El board sigue mostrando el fixture |
| Cron de Arq (periódico) | Scheduler | Reencola `watchlist.monitor=true` + seed gov (con idempotencia) |
| Re-scan: baja el grado | Monitoreo | Alerta vía Resend / Slack |
| Re-scan: nuevo `critical` (nuevo `dedupe_key`) | Monitoreo | Alerta vía Resend / Slack |
| Re-scan: `dedupe_key` previo no reaparece | Monitoreo | `finding.status='fixed'` (sin alerta) |
| Usuario envía URL en nivel pasivo/básico | API | Entra al ranking público |
| Usuario corre nivel activo (intermedio/avanzado) | API | `visibility=private`; **no** entra al ranking |

## 7. Notas de implementación y recortes

- **Fijar Arq + cron nativo de Arq** desde el inicio; no `rq-scheduler`, no APScheduler, no un proceso scheduler aparte.
- **Fixtures primero, scans reales después**: el seed real solo mejora el board si gana la carrera contra el reloj del pitch; nunca es el camino crítico.
- **Sin alertas in-app**: solo email (Resend) y Slack webhook.
- **El board público es solo pasivo**: el filtro `visibility=public` + `is_gov=true` es el único origen de filas del leaderboard.
- **La comparación de findings es siempre a nivel site** (`dedupe_key`, `first_seen`/`last_seen`), nunca a nivel scan; de lo contrario el monitoreo no podría distinguir "nuevo" de "ya estaba".
