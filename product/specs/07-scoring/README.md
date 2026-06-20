---
feature: scoring
type: spec
status: pending
coverage: 0
audited: 2026-06-20
sources: spec.md §9 (§9.1–§9.5); spec-gaps.md §6.7–§6.8, §6.13, §2.6
---

# Owliver — Modelo de scoring (doble score, grados A–F)

> Owliver convierte los findings deduplicados de un scan en un **doble sub-score 0–100** (web/OWASP + agéntico/LLM), los combina en un `overall_score`, y lo proyecta a un **grado A–F estilo Mozilla Observatory** (con escalón **E** en la zona poblada). El scoring es una **fórmula determinista en Python**, nunca el LLM. Tres decisiones de diseño lo hacen confiable: (1) `penalty_raw` se persiste **sin cap** para ordenar y desempatar el leaderboard cuando decenas de `.gob.mx` colapsan a F; (2) la **cobertura parcial** (un scanner base que crashea/expira/es bloqueado) capa el grado en C en vez de premiar al sitio que rompe la herramienta; (3) `agentic_status` tiene **tres estados** — `no_surface`, `tested`, `detected_not_tested` — para que "tiene chatbot pero no lo auditamos" deje de inflar el overall como si la IA no existiera.

## 1. Principios

- **Determinismo.** El score es una fórmula en Python pura. El LLM (Opus) **nunca** calcula el score; solo redacta la narrativa "Owliver te explica" y el top-3 a partir de un resumen compacto. La deduplicación por `dedupe_key` ocurre **antes** de calcular cualquier penalty (ver [06-data-model](../06-data-model/README.md) para `dedupe_key` y el modelo de `findings`).
- **No premiar el silencio.** Un sitio que produce 0 findings porque rompió el scanner, o porque tiene un chatbot que no pudimos sondear, **no** puede salir mejor que uno que se auditó completo. Las reglas de cobertura parcial (§4) y de `agentic_status` (§5) existen para cerrar exactamente esos huecos.
- **El doble score es el diferenciador.** Separar web/OWASP de agéntico/LLM es lo que produce la narrativa visual única del demo (§6) y debe preservarse en datos, reporte y leaderboard.

## 2. Fórmula base: penalty y sub-score

El cálculo parte de los findings deduplicados de cada `source`. Cada finding aporta una penalización igual al **peso de su severidad × el factor de su confianza**:

```
Peso por severidad:  critical=40  high=20  medium=8  low=3  info=0
Factor de confianza: alta=1.0  media=0.7  baja=0.4

penalty_raw(sub) = Σ (peso_severidad × factor_confianza)   sobre findings deduplicados del source
                   (SIN cap — se persiste en scans.penalty_raw para orden/desempate)
sub_score        = max(0, 100 − min(100, penalty_raw))     (con cap, para mostrar 0–100)

web_score     = sub_score sobre findings source="owasp"
agentic_score = sub_score sobre findings source="agentic"
```

Notas normativas:

- **`info=0`** no afecta el score. Los findings `info` se muestran en la capa técnica del reporte con un conteo aparte; no entran en `penalty_raw` ni mueven el grado. (Esto incluye los findings-meta que el propio escaneo emite, p. ej. "tool X no completó" o "cobertura incompleta" de §4.)
- **`penalty_raw` se persiste sin clamp** en la columna `scans.penalty_raw` (ver [06-data-model](../06-data-model/README.md)). El cap `min(100, penalty_raw)` aplica **solo** al `sub_score` que se muestra 0–100; nunca a la columna persistida que ordena el leaderboard.
- **Anti-inflado por duplicados (opcional).** Para no inflar `penalty_raw` por hallazgos repetidos del mismo problema, se puede contar **solo el peor finding por `(category, endpoint)`**. Esto es independiente de la deduplicación por `dedupe_key`, que ocurre siempre antes.

## 3. `overall_score` y `agentic_status`

`overall_score` pondera 60% web / 40% agéntico **únicamente** cuando el agéntico se pudo probar de verdad. El estado del agéntico se persiste en `scans.agentic_status` (ver [06-data-model](../06-data-model/README.md)) y decide cómo se combina:

```
overall_score = round(0.6 × web_score + 0.4 × agentic_score)   si agentic_status = tested
overall_score = web_score                                      si agentic_status = no_surface
# detected_not_tested → overall = web_score PERO con badge "IA detectada, sin auditar";
#                       nunca se reporta como sitio sin riesgo agéntico.
```

## 4. Cobertura parcial (fallo de scanner)

Un scan donde una tool base crashea, expira (timeout) o es bloqueada por el WAF produce 0 findings de esa tool. Sin una regla explícita, eso **premiaría** al sitio que rompe el scanner — el incentivo invertido: los sitios más hostiles/protegidos saldrían con A falsa. Para cerrarlo se persiste el estado por herramienta en `scans.coverage` (jsonb, `[{tool, status: ok|failed|timeout}]`; ver [06-data-model](../06-data-model/README.md)):

- Si faltó **≥1 scanner base** (cualquier tool con `status` distinto de `ok`):
  - `scans.status='partial'`.
  - Se emite un finding `info` **"cobertura incompleta"** (no afecta el score, sí informa al lector).
  - El **grado se capa en C** — **nunca A/B con cobertura parcial**, independientemente del score numérico (ver §5.2).
  - El reporte y el leaderboard muestran la etiqueta **"cobertura parcial"**.

La regla "no premiar el silencio" aquí es la que hace que un sitio que tira ZAP/Nuclei/testssl no pueda colarse al tope del ranking.

## 5. Grados A–F

### 5.1 Escala (con E)

```
Grado:  A ≥90 · B ≥80 · C ≥70 · D ≥60 · E ≥40 · F <40
```

El escalón **E** (40–59) abre resolución en la zona poblada del leaderboard gov, donde caen muchos `.gob.mx` reales; sin él, los saltos D→F apelmazan demasiados sitios en F. El grado se deriva del `overall_score`.

### 5.2 Caps que sobreescriben el grado numérico

Dos condiciones bajan el grado por debajo de lo que diría el score crudo:

- **Cobertura parcial.** Cuando `scans.status='partial'`, el grado se capa en **C** independientemente del `overall_score` (ver §4). Nunca se muestra A con cobertura parcial.
- **`detected_not_tested`.** No es un cap numérico sobre el grado, pero acompaña la fila con el badge **"IA detectada, sin auditar"** (ver §3): el `overall` sigue siendo `web_score`, pero el sitio **nunca** se presenta como libre de riesgo agéntico.

## 6. Orden del leaderboard y desempate

El cap `min(100, penalty_raw)` colapsa a **0/F** a cualquier sitio con ~3 criticals (`penalty_raw ≥ 100`). En un universo de 30–50 `.gob.mx` reales, eso deja a la mayoría empatada en 0/F y el orden "peores primero" queda indefinido — el leaderboard, que es la **primera pantalla del pitch**, se vería roto.

Por eso el leaderboard **no ordena por `overall_score`**, sino por:

```
(overall_grade ASC, penalty_raw DESC)
```

— peores primero, con desempate por penalización cruda. La fila muestra `penalty_raw` (o el conteo ponderado) para que el contraste entre dos sitios ambos en F sea visible. La columna de grado se llama **`overall_grade`** en todas partes (datos, orden y UI); úsese ese nombre exacto.

> §9.4 de spec.md es la **autoridad de orden**: cualquier otra referencia al orden del leaderboard (overview, ranking) debe citar `(overall_grade ASC, penalty_raw DESC)`.

La construcción de la consulta del ranking gov, los filtros (país MX) y la UI del leaderboard pertenecen a [08-ranking-watchlists](../08-ranking-watchlists/README.md) y a [13-frontend](../13-frontend/README.md); aquí solo se fija el criterio de orden y desempate que esas vistas consumen.

## 7. Por qué el doble score importa

Un `.gob.mx` puede salir **B en Web** pero **F en Agéntico** — por ejemplo, su chatbot filtra el system-prompt vía un Crescendo corto. Esa disociación es la narrativa visual potente y única del demo: el sitio "se ve bien" por fuera y se cae en su superficie de IA.

Los **tres estados** de `agentic_status` son lo que mantiene esa narrativa honesta. Antes, un `agentic_score = N/A` mezclaba dos casos muy distintos:

- **(a) sin chatbot** → N/A legítimo, `no_surface`, `overall = web_score`.
- **(b) hay chatbot pero el testing falló o se recortó** → antes también caía en N/A, lo que escondía un riesgo real sin auditar y hacía colapsar el `overall` a `web_score` **como si la IA no existiera** — justo en el diferenciador del producto, una falsa sensación de seguridad y un overall inflado.

Con `detected_not_tested`, ese segundo caso aparece como **riesgo declarado** ("IA detectada, sin auditar"): ni se promedia ni se premia con 100, y nunca se reporta como sitio falsamente limpio.

| `agentic_status` | Significado | Efecto en `overall` |
|---|---|---|
| `no_surface` | No se detectó chatbot/superficie agéntica | `overall = web_score` (no penaliza) |
| `detected_not_tested` | Hay superficie pero no se pudo probar (testing falló/se recortó) | **No** se promedia y **no** se premia con 100: badge "IA detectada, sin auditar" en reporte + leaderboard |
| `tested` | Superficie detectada y sondeada → `agentic_score` válido | entra al promedio ponderado |

La detección y sondeo de la superficie agéntica (de dónde salen estos estados) los produce el equipo de agentes y los scanners agénticos — ver [05-agent-team](../05-agent-team/README.md) y spec.md (overview, §6–§8). El alcance del avanzado se limita a 2–3 turnos con un solo objetivo (system-prompt leak vía Crescendo corto), lo que en la práctica produce `tested` cuando la superficie existe y es sondeable.
