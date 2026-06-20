---
feature: scoring
type: plan
status: pending
coverage: 0
audited: 2026-06-20
spec: ./spec.md
sources: spec.md §9.1–§9.5; 06-data-model §2/§5/§3.3; 02-attack-levels §3–§4; 08-ranking-watchlists §2/§4; 05-agent-team §4
---

# Owliver — Modelo de scoring (doble score, grados A–F) — plan de implementación (CÓMO)

> El entregable medular es **un módulo de dominio puro** —
> `src/scans/domain/services/scoring.py` + una **tabla de pesos versionada**
> (`scoring_weights.py`)— que toma `list[Finding]` ya deduplicados + `coverage`
> + `agentic_status` y devuelve un `ScoreResult` congelado (`web_score`,
> `agentic_score`, `overall_score`, `overall_grade`, `penalty_raw`). Nada de I/O,
> nada de DB, **nada de LLM**: es la fórmula determinista de [spec §9](./spec.md)
> traducida a Python table-driven, y su **suite de tests table-driven es el
> corazón de la feature**.
>
> Principio operativo: **el LLM (Opus) nunca calcula el score** — solo redacta la
> narrativa "Owliver te explica" a partir del resumen ya numerado (spec §1,
> [05-agent-team](../05-agent-team/spec.md) §4). El worker invoca `compute_score()`
> **después** de que [04-scanning-engine](../04-scanning-engine/spec.md) parsea y
> [06-data-model](../06-data-model/spec.md) deduplica por `dedupe_key`; el
> resultado se escribe tal cual en las columnas `scans.*` que 06 ya definió. Este
> plan **no redefine** el esquema: lo **llena**.

## 0. Estado de las dependencias

El scoring **no crea tablas ni endpoints**: consume contratos y columnas que ya
existen (06) o que son creación net-new de 06, y produce un servicio de dominio
puro. Lo que se reutiliza tal cual:

- **Contrato `Finding` congelado** (hora 0–2): `src/scans/domain/contracts/finding.py`
  — `Finding` con `source` (`owasp|agentic`), `severity`
  (`critical|high|medium|low|info`), `confidence` (`alta|media|baja`), `category`,
  `affected_url`, `endpoint`, `param`. El scoring lee **solo** esos campos; no
  necesita el resto del shape. (Lo posee [06-data-model](../06-data-model/spec.md) §2.2;
  **no se modifica**.)
- **`AgenticResult` congelado**: mismo `finding.py` — incluye `agentic_status`
  (`no_surface|detected_not_tested|tested`), fuente de la columna `scans.agentic_status`.
  El scoring recibe el `agentic_status` ya resuelto por el subagente agéntico
  ([03-agentic-surface](../03-agentic-surface/spec.md), [05-agent-team](../05-agent-team/spec.md));
  **no lo infiere**.
- **Enums del SCAN**: `src/common/domain/enums/scans.py` (`FindingSeverity`,
  `FindingConfidence`, `FindingSource`, `AgenticStatus`) — `BaseEnum(Enum)` con
  valores `str` (`backend/src/common/domain/enums/base_enum.py`). El scoring
  indexa la tabla de pesos por estos enums; **no** redeclara las cadenas.
- **Columnas destino en `scans`** (creación de 06, migración `…_scan_engine.py`):
  `web_score int`, `agentic_score int nullable`, `overall_score int`,
  `overall_grade char(1)`, `penalty_raw int`, `coverage JSONB`, `agentic_status`
  (enum-`String`), `status` (`queued|running|partial|done|…`). Ver
  [06-data-model §2.4](../06-data-model/plan.md). El scoring **produce los valores**;
  el repo `SQLScanRepository` (06) los persiste.
- **`coverage` jsonb**: `[{tool, status: ok|failed|timeout}]`, lo escribe el motor
  ([04-scanning-engine §4.3](../04-scanning-engine/plan.md)). El scoring lo **lee**
  para decidir el cap-C de cobertura parcial (§4); no lo construye.
- **Tests**: `backend/tests/<área>/...`, pytest, librería **`expects`** (ver
  `tests/common/domain/permissions/test_checker.py`), funciones/fixtures
  standalone, AAA. Los tests de scoring son **dominio puro** → no tocan
  `conftest`/DB; importan el servicio y afirman sobre el `ScoreResult`.

> **Lo único net-new de esta feature** son dos archivos de dominio
> (`scoring_weights.py`, `scoring.py`), su `__init__` de servicios, y la suite
> `tests/scans/domain/test_scoring*.py`. Cero migraciones, cero ORM, cero router.

## 1. Decisión de módulos — dónde vive el scoring

El scoring es **lógica de dominio del scan**, no infraestructura compartida ni un
módulo propio: gira enteramente alrededor de `list[Finding]` + el estado del scan.
Vive dentro de `src/scans/`, junto a los otros servicios puros que 06 **declara
como net-new** y creará ahí (`services/dedupe.py`, `services/host.py` —análogo en
`sites`—; ninguno existe aún en el repo, los tres se crean en sus respectivas
features):

| Pieza | Ruta (net-new) | Razón |
|---|---|---|
| Tabla de pesos versionada | `src/scans/domain/services/scoring_weights.py` | **Constante curada** (severity→peso, confidence→factor, bandas de grado). Un solo archivo, versionado por `SCORING_VERSION`, para auditar/ajustar la curva sin tocar el algoritmo. |
| Algoritmo puro | `src/scans/domain/services/scoring.py` | `compute_score(...) -> ScoreResult`. Funciones puras, table-driven sobre `scoring_weights`. Sin DB, sin LLM, sin I/O. |
| Resultado congelado | (dataclass dentro de `scoring.py`) | `ScoreResult` frozen — el shape que el worker escribe a `scans.*`. |

> **Por qué dict/módulo Python y no YAML externo:** la spec admite "dict/YAML
> estático curado". Se elige **módulo Python** (`dict` + `enum` keys) porque (a)
> los pesos se indexan por los enums de `enums/scans.py` con type-checking, (b) no
> añade un loader/parse ni un path de archivo que cargar en runtime, y (c) queda
> versionado en git junto al algoritmo que lo consume. `SCORING_VERSION: str` en
> el mismo módulo permite congelar la curva (cualquier cambio de pesos bumpea la
> versión y rompe los tests de frontera adrede → revisión consciente).

El servicio **no** importa ORM ni repos: recibe `list[Finding]` (Pydantic) y
primitivos. Quien lo invoca (el worker, [05-agent-team §4](../05-agent-team/plan.md))
arma el `ScoreInput` y persiste el `ScoreResult` vía `SQLScanRepository`.

## 2. Mapa de archivos a crear

```
backend/src/scans/domain/services/
  scoring_weights.py        # NET-NEW: SEVERITY_PENALTY, CONFIDENCE_FACTOR,
                            #          GRADE_BANDS, PARTIAL_COVERAGE_CAP, SCORING_VERSION
  scoring.py                # NET-NEW: ScoreInput, ScoreResult, compute_score() y helpers puros
  __init__.py               # re-exporta compute_score, ScoreResult (import corto)

backend/tests/scans/domain/
  test_scoring_penalty.py   # NET-NEW: suma de penalties, info=0, penalty_raw sin clamp
  test_scoring_grades.py    # NET-NEW: fronteras de banda A/B/C/D/E/F (table-driven)
  test_scoring_coverage.py  # NET-NEW: cap-C por cobertura parcial
  test_scoring_agentic.py   # NET-NEW: modulación por agentic_status (3 estados) + overall
  test_scoring_leaderboard.py # NET-NEW: desempate F/0 vía penalty_raw, caso "mayoría .gob.mx en 0"
```

### 2.1 `scoring_weights.py` — la tabla curada

```python
SCORING_VERSION = "1"   # bump deliberado al ajustar la curva (rompe tests de frontera)

# Peso por severidad (spec §9.2). info=0: NO mueve el score (§3).
SEVERITY_PENALTY: dict[FindingSeverity, int] = {
    FindingSeverity.CRITICAL: 40,
    FindingSeverity.HIGH:     20,
    FindingSeverity.MEDIUM:    8,
    FindingSeverity.LOW:       3,
    FindingSeverity.INFO:      0,
}

# Factor por confianza (spec §9.2).
CONFIDENCE_FACTOR: dict[FindingConfidence, float] = {
    FindingConfidence.ALTA:  1.0,
    FindingConfidence.MEDIA: 0.7,
    FindingConfidence.BAJA:  0.4,
}

# Bandas de grado sobre overall_score (spec §9.5.1). Orden DESC; primera que cumple gana.
GRADE_BANDS: tuple[tuple[int, str], ...] = (
    (90, "A"), (80, "B"), (70, "C"), (60, "D"), (40, "E"), (0, "F"),
)

PARTIAL_COVERAGE_CAP = "C"     # grado máximo con scans.status='partial' (§4)
```

### 2.2 `scoring.py` — entradas, salida y algoritmo

| Símbolo | Tipo | Notas |
|---|---|---|
| `ScoreInput` | `@dataclass(frozen=True)` | `findings: list[Finding]`, `agentic_status: AgenticStatus`, `partial_coverage: bool`. **No** recibe DB ni el `coverage` jsonb crudo: quien invoca deriva `partial_coverage = any(t.status != 'ok')` (§4). |
| `ScoreResult` | `@dataclass(frozen=True)` | `web_score: int`, `agentic_score: int \| None`, `overall_score: int`, `overall_grade: str` (1 char), `penalty_raw: int`, `coverage_partial: bool`, `version: str`. Es el shape que el worker escribe a `scans.*`. |
| `compute_score(inp) -> ScoreResult` | función pura | Orquesta los helpers de abajo. **Única** entrada pública. |

Helpers puros (privados, todos table-driven sobre §2.1):

```python
def _penalty_raw(findings: list[Finding]) -> int:
    # Σ SEVERITY_PENALTY[f.severity] * CONFIDENCE_FACTOR[f.confidence]  → round() final
    # SIN cap. info=0 contribuye 0. (§3)

def _sub_score(penalty_raw: int) -> int:
    return max(0, 100 - min(100, penalty_raw))     # cap solo para mostrar 0–100

def _grade_for(score: int) -> str:
    # primera banda DESC cuyo umbral <= score (GRADE_BANDS)

def _apply_caps(grade: str, *, partial: bool) -> str:
    # si partial y grade es mejor que "C" → degradar a "C" (§4, §5.2)
```

> El `agentic` se computa sobre `findings` con `source == 'agentic'`; el `web`
> sobre `source == 'owasp'`. `penalty_raw` persistido = el **del web** (driver del
> leaderboard gov, §6); el agéntico es informativo para el gauge. (Decisión §8.4.)

## 3. Fórmula base: `penalty_raw` y sub-score

Implementa [spec §9.2](./spec.md) **literal**, separando lo que se clampa de lo que no:

1. **Particionar** por `source`: `web = [f for f in findings if f.source == owasp]`,
   `agentic = [... == agentic]`.
2. **`penalty_raw(sub)`** = `Σ SEVERITY_PENALTY[sev] × CONFIDENCE_FACTOR[conf]`
   sobre el sub-conjunto deduplicado. **SIN cap** — se redondea al final, no por
   término. Los `info` (peso 0) contribuyen 0 → **no mueven el score** (incluye los
   findings-meta "tool X no completó" / "cobertura incompleta" que el motor emite,
   [04-scanning-engine §4.3](../04-scanning-engine/plan.md)).
3. **`sub_score`** = `max(0, 100 − min(100, penalty_raw))` — el cap
   `min(100, …)` aplica **solo** al valor 0–100 mostrado, **nunca** al
   `penalty_raw` que se persiste.
4. **`web_score`** = `_sub_score(_penalty_raw(web))`;
   **`agentic_score`** = `_sub_score(_penalty_raw(agentic))` (modulado por §5).

`penalty_raw` se entrega **sin clamp** en `ScoreResult.penalty_raw` y se escribe a
`scans.penalty_raw int` (06): es lo que desempata el leaderboard cuando decenas de
`.gob.mx` colapsan a 0/F (§6). El test `test_scoring_penalty` afirma que un sitio
con 5 criticals reporta `penalty_raw ≈ 200` (no 100) aunque `web_score == 0`.

> **Anti-inflado por duplicados (opcional, spec §9.2 nota).** Más allá del dedupe
> por `dedupe_key` (06 §3.3, que corre **antes**), se puede contar **solo el peor
> finding por `(category, endpoint)`** dentro de `_penalty_raw`. Se deja como flag
> interno `collapse_by_category: bool = False` (decisión abierta §8.3): por defecto
> **off** para no divergir del conteo crudo en el demo; si se activa, hay test que
> fija el comportamiento de colapso.

## 4. Cobertura parcial — cap del grado en C

Cierra el incentivo invertido de [spec §9.4](./spec.md): un sitio que tira
ZAP/Nuclei/testssl produce 0 findings de esa tool y **no** puede salir con A.

- Quien invoca `compute_score` deriva `partial_coverage` del `coverage` jsonb que
  el motor escribió (`any(tool.status != 'ok')`,
  [04-scanning-engine §4.3](../04-scanning-engine/plan.md)) y lo pasa en `ScoreInput`.
  El scoring **no** lee el jsonb crudo: recibe el booleano ya resuelto (mantiene el
  dominio puro y sin conocer la forma de `coverage`).
- Cuando `partial_coverage is True`:
  - `_apply_caps` degrada `overall_grade` a **C** si el grado numérico era mejor
    (A/B). **Nunca** A/B con cobertura parcial.
  - El `overall_score` numérico **no se toca** (el cap es solo sobre el grado, §5.2);
    el reporte/leaderboard muestran la etiqueta **"cobertura parcial"** a partir de
    `scans.status='partial'` (lo setea el worker, no el scoring).
  - Los **grados por dimensión** (display-only, §5) y el `penalty_raw` **no** se
    capan: el cap-C es **solo** sobre `overall_grade` (autoritativo).
- El finding-meta `info` "cobertura incompleta" lo emite el motor; como es `info`
  (peso 0) **no** entra en `penalty_raw` (§3). El cap es estructural, no numérico.

`ScoreResult.coverage_partial` propaga el booleano para que el presenter de
[09-reporting](../09-reporting/spec.md) y el leaderboard
([08-ranking-watchlists](../08-ranking-watchlists/spec.md)) pinten la etiqueta sin
recalcular.

## 5. Grados A–F (con E) y grados por dimensión

Implementa [spec §9.5](./spec.md):

```
overall_grade:  A ≥90 · B ≥80 · C ≥70 · D ≥60 · E ≥40 · F <40   (sobre overall_score)
```

- El escalón **E (40–59)** abre resolución en la zona poblada del leaderboard gov
  (muchos `.gob.mx` reales caen ahí); sin él, D→F apelmaza todo en F. `GRADE_BANDS`
  (§2.1) codifica las 6 bandas; `_grade_for` toma la primera DESC que cumple.
- **Caso "mayoría .gob.mx en 0"** (§6): cuando `overall_score == 0` el grado es
  **F** (no E) — `0 < 40`. El escalón E **no** rescata a los colapsados; solo
  ordena la franja 40–59. El desempate entre dos F/0 lo da `penalty_raw` (§6), no
  el grado. Test en `test_scoring_leaderboard`.
- **Grados por dimensión (display-only, spec §9.5.1).** La UI dibuja, junto a cada
  gauge (🛡️ Web / 🤖 Agéntico), un grado-letra por dimensión aplicando **las mismas
  bandas** a `web_score` y `agentic_score`. Se exponen como helper puro
  `dimension_grade(score) -> str` (= `_grade_for`, reutilizado), pero **no se
  persisten en columna propia**, **no** entran al orden del leaderboard y **no**
  sustituyen a `overall_grade`. Habilitan el contraste estrella
  ("🛡️ C web / 🤖 F agéntico", spec §9.7). Los **caps de §4 aplican solo a
  `overall_grade`**, nunca a los grados por dimensión.

## 6. `overall_score`, `agentic_status` y orden del leaderboard

### 6.1 Combinación ponderada según `agentic_status`

Implementa [spec §9.3](./spec.md). El estado lo trae `ScoreInput.agentic_status`
(de `AgenticResult`, [03-agentic-surface](../03-agentic-surface/spec.md)):

```
agentic_status = tested              → overall = round(0.6*web + 0.4*agentic)
                                        agentic_score válido entra al promedio
agentic_status = no_surface          → overall = web_score
                                        agentic_score = None (N/A legítimo, no penaliza)
agentic_status = detected_not_tested → overall = web_score
                                        agentic_score = None, PERO ScoreResult marca
                                        agentic_detected_untested=True → badge
                                        "IA detectada, sin auditar"; NUNCA 100, NUNCA promediado
```

| `agentic_status` | `agentic_score` | `overall_score` | Marca |
|---|---|---|---|
| `no_surface` | `None` | `web_score` | — |
| `detected_not_tested` | `None` | `web_score` | badge "IA detectada, sin auditar" |
| `tested` | `int` 0–100 | `round(0.6·web + 0.4·agentic)` | entra al promedio |

> La diferencia crítica (spec §9.7): `detected_not_tested` **no** es lo mismo que
> `no_surface`. Ambos dejan `overall = web_score`, pero el primero **declara riesgo
> sin auditar** (badge), nunca premia con 100 ni se reporta como sitio limpio. El
> `ScoreResult` lleva un flag `agentic_detected_untested: bool` para que el reporte
> distinga los dos casos sin re-mirar `agentic_status`. Test en
> `test_scoring_agentic`.

### 6.2 Orden y desempate del leaderboard (criterio consumido por 08)

El scoring **fija el criterio**; la consulta, los filtros (país MX, `is_gov`) y la
UI los posee [08-ranking-watchlists §2/§4](../08-ranking-watchlists/spec.md) y
[13-frontend](../13-frontend/spec.md). El criterio autoritativo
([spec §9.4](./spec.md), autoridad de orden) es:

```
ORDER BY overall_grade ASC, penalty_raw DESC      -- peores primero, desempate por penalización cruda
```

- El cap `min(100, penalty_raw)` colapsa a 0/F a cualquier sitio con ~3 criticals;
  por eso el orden **no** usa `overall_score` sino `(overall_grade, penalty_raw)`.
  `penalty_raw` (sin clamp, §3) es lo que distingue dos sitios ambos en F.
- La columna de grado **autoritativa** es `overall_grade` (datos + orden + grade
  badge principal). Los grados por dimensión (§5) son display-only, **nunca**
  `overall_grade`.
- El índice físico `scans (overall_grade ASC, penalty_raw DESC)` lo crea la
  migración de 06 ([06-data-model §3.4](../06-data-model/plan.md)); aquí solo se
  garantiza que `ScoreResult` produce ambos valores consistentes con ese orden.

## 7. Punto de invocación (contrato con el worker)

El scoring se invoca **una vez por scan**, tras el parsing y la deduplicación,
dentro del flujo del worker ([05-agent-team §4](../05-agent-team/plan.md)),
**antes** de redactar la narrativa LLM:

```python
# en el worker (05), Python determinista — el LLM NO participa
result = compute_score(ScoreInput(
    findings=deduped_findings,                      # ya pasados por dedupe (06 §3.3)
    agentic_status=agentic_result.agentic_status,   # de AgenticResult (03/05)
    partial_coverage=any(t["status"] != "ok" for t in coverage),  # de coverage jsonb (04)
))
# persistir vía SQLScanRepository (06): result.web_score, result.agentic_score,
#   result.overall_score, result.overall_grade, result.penalty_raw
```

El scoring **no** importa el repo ni la sesión: devuelve el `ScoreResult` y el
worker lo escribe. Esto mantiene el servicio testeable en aislamiento puro y
respeta "el LLM no escribe columnas calculadas" ([06-data-model](../06-data-model/plan.md)
principio operativo). El resumen compacto que sí ve el LLM (top-3, conteos) se
deriva del `ScoreResult` + `findings`, no al revés.

## 8. Suite de tests — `backend/tests/scans/domain/`

Convención del repo: `tests/<área>/...`, pytest, **`expects`**, funciones
standalone, AAA, **table-driven** vía `@pytest.mark.parametrize`. **Dominio puro:
sin DB, sin `conftest`/`create_all`** — importan `compute_score`/`ScoreResult` y
afirman sobre el resultado. Es el **corazón** de la feature.

| Archivo | Capa | Asserts |
|---|---|---|
| `test_scoring_penalty.py` | dominio (puro) | `_penalty_raw` = Σ peso×factor exacto sobre casos tabulados (1 critical/alta=40; 1 medium/media=5.6→round; mezcla); **`info` contribuye 0** (no mueve score ni penalty); `penalty_raw` **sin clamp** (5 criticals → ~200, no 100) mientras `web_score==0`; `_sub_score` clampa a 0–100. |
| `test_scoring_grades.py` | dominio (puro) | **fronteras de banda** parametrizadas: 90→A, 89→B, 80→B, 79→C, 70→C, 69→D, 60→D, 59→E, 40→E, 39→F, 0→F; el escalón **E** existe en 40–59; `dimension_grade` aplica las mismas bandas a un `web_score`/`agentic_score` arbitrario. |
| `test_scoring_coverage.py` | dominio (puro) | `partial_coverage=True` con `overall_score` de A/B ⇒ `overall_grade=='C'` (cap); con score que ya da D/E/F ⇒ el cap **no** sube el grado; `coverage_partial=True` se propaga; **`penalty_raw` y los grados por dimensión NO se capan**; `partial_coverage=False` ⇒ sin cap. |
| `test_scoring_agentic.py` | dominio (puro) | `tested` ⇒ `overall==round(0.6·web+0.4·agentic)` y `agentic_score` no es None; `no_surface` ⇒ `overall==web_score`, `agentic_score is None`, sin badge; `detected_not_tested` ⇒ `overall==web_score`, `agentic_score is None`, `agentic_detected_untested is True` (**nunca 100, nunca promediado**); redondeo de `overall` verificado. |
| `test_scoring_leaderboard.py` | dominio (puro) | **desempate F/0**: dos `ScoreResult` ambos `overall_grade=='F'`, `overall_score==0`, distinto `penalty_raw` ⇒ ordenar `(grade ASC, penalty_raw DESC)` pone primero el de mayor `penalty_raw`; **caso "mayoría .gob.mx en 0"**: `overall_score==0 ⇒ grade=='F'` (el escalón E no lo rescata); `version==SCORING_VERSION`. |

> Los tests de **persistencia** de estas columnas (UPSERT, leaderboard query) viven
> en [06-data-model §5](../06-data-model/plan.md) (`test_leaderboard_order.py`); los
> de **endpoint** (badge en la respuesta, orden servido) en [12-api](../12-api/spec.md).
> Aquí se prueba **solo la fórmula**, no la DB ni la API — no se duplica.

## 9. Secuencia de build

1. **`scoring_weights.py`** — tabla curada (`SEVERITY_PENALTY`,
   `CONFIDENCE_FACTOR`, `GRADE_BANDS`, `PARTIAL_COVERAGE_CAP`, `SCORING_VERSION`).
   Depende solo de `enums/scans.py` (06 §2.1). Es lo que se congela primero.
2. **`scoring.py`** — `ScoreInput`/`ScoreResult` + `_penalty_raw`, `_sub_score`,
   `_grade_for`, `_apply_caps`, `compute_score`, `dimension_grade`. Puro, sin I/O.
3. **Suite §8** — table-driven sobre fronteras, penalties, cap-C, 3 estados
   agénticos, desempate F/0. Verde = feature lista a nivel dominio.
4. **Enganche en el worker** ([05-agent-team §4](../05-agent-team/plan.md)): el
   worker construye `ScoreInput` tras dedupe + parsing y persiste el `ScoreResult`
   vía `SQLScanRepository` (06). El consumo de `overall_grade`/`penalty_raw` por el
   leaderboard lo cablea 08; el badge agéntico, 09/13.

La feature se considera `implemented`/coverage>0 cuando `compute_score` existe,
toda la suite §8 pasa, y el worker escribe los 5 campos
(`web_score/agentic_score/overall_score/overall_grade/penalty_raw`) a partir del
`ScoreResult`.

## 10. Decisiones y riesgos abiertos

1. **Tabla de pesos en módulo Python (no YAML externo)** — resuelto: `dict` con
   keys `enum` (type-checked contra `enums/scans.py`), `SCORING_VERSION` para
   congelar la curva; cualquier ajuste bumpea la versión y rompe los tests de
   frontera adrede (revisión consciente). Evita un loader/parse en runtime.
2. **Scoring es dominio puro, sin DB ni LLM** — congelado: `compute_score` recibe
   `list[Finding]` + primitivos y devuelve `ScoreResult`; el worker persiste. Es lo
   que mantiene "el LLM no escribe columnas calculadas" (06) verificable en
   aislamiento. Riesgo: si alguien mete I/O en el servicio, los tests puros
   dejarían de aislar — se documenta para que un revisor lo rechace.
3. **Anti-inflado por `(category, endpoint)`** — abierto: flag
   `collapse_by_category=False` por defecto. El demo usa conteo crudo (post-dedupe
   por `dedupe_key`, que ya corre antes); activar el colapso es una decisión de
   curva, no estructural. Si se activa, hay test que fija el comportamiento.
4. **`penalty_raw` persistido = el del web** — el leaderboard gov ordena por riesgo
   web/OWASP (driver del ranking, §6); el `penalty_raw` agéntico se calcula para el
   sub-score pero **no** se persiste (la columna `scans.penalty_raw` es una). Si 08
   pidiera desempatar también por agéntico, sería un cambio de columna en 06, no de
   este servicio. Documentado como límite.
5. **El cap-C es sobre el grado, no sobre el score** — `overall_score` numérico no
   se toca con cobertura parcial; solo `overall_grade` baja a C (y la etiqueta sale
   de `scans.status='partial'`, que setea el worker). Riesgo de confusión visual
   (un sitio "85 pero grado C"): el badge "cobertura parcial" lo explica en 09/13.
6. **`agentic_status` lo decide 03/05, no el scoring** — el servicio **confía** en
   el estado que recibe. Si la detección agéntica clasifica mal (`tested` con
   sondeo recortado), el scoring promediaría un agéntico engañoso; el límite del
   avanzado a 2–3 turnos (spec §9.7, [05-agent-team](../05-agent-team/spec.md)) lo
   acota, pero la corrección del estado **no** es responsabilidad de esta feature.
