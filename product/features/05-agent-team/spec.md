---
feature: agent-team
type: spec
status: pending
coverage: 0
audited: 2026-06-20
sources: spec.md §6; spec-gaps.md §1 (§1.2, §1.3, §1.4)
---

# Owliver — Equipo de agentes Agno + parsers + worker

> El cerebro de Owliver es un **Agno Team** en modo `coordinate`: un orquestador Opus delega `{url, level}` a dos subagentes Sonnet (OWASP y superficie agéntica), cada uno decide **qué** tools correr según el nivel, y **las tool-functions parsean su salida cruda a `list[Finding]` en Python puro**. La tesis arquitectónica de fondo es: *saca al LLM del camino de datos.* Parsing, deduplicación y scoring son Python determinista; el `response_model` estructurado se reserva exclusivamente para Opus al redactar el resumen ejecutivo (<2k tokens). Este subspec define el diseño del Team, las tool-functions parser, los parsers priorizados, la política de timeouts/fallo parcial, el budget de Opus y el flujo del worker.

## 1. Diseño del Agno Team

El equipo es un `Team` en modo `coordinate` con tres modelos:

- **Orquestador** — `Claude("opus")`. Coordina a los dos subagentes en paralelo sobre `{url}` a nivel `{level}`. **No** selecciona tools ni construye findings: el merge, la deduplicación y el scoring son Python determinista (ver [07-scoring](../07-scoring/spec.md)). Opus solo redacta el resumen ejecutivo en lenguaje llano sobre un resumen compacto.
- **Subagente OWASP** — `Claude("sonnet")`, nombre `"OWASP Scanner"`. Decide **solo** qué tools correr según el `{level}`; **no** redacta ni reconstruye findings (las tools ya devuelven `Finding[]` parseado; los acumula en el contexto).
- **Subagente agéntico** — `Claude("sonnet")`, nombre `"Agentic Surface Auditor"`. Detecta chatbots/inputs de prompt y los prueba según el nivel, mapeando a OWASP-LLM Top 10. Las tools devuelven `Finding[]` + inventario ya parseados; no los reconstruye. El detalle de la superficie agéntica (puente de ataque, LLM-juez, canary) vive en [03-agentic-surface](../03-agentic-surface/spec.md).

### 1.1 Pseudocódigo de referencia

```python
# Pseudocódigo de referencia
class Finding(BaseModel):           # salida estructurada estándar (sección 8)
    source: Literal["owasp", "agentic"]
    tool: str
    category: str                   # A01..A10 o LLM01..LLM10
    title: str
    severity: Literal["critical","high","medium","low","info"]
    cvss: float | None
    confidence: Literal["alta","media","baja"]
    description: str
    evidence: dict                  # payload, req/resp snippet, screenshot ref (URL relativa)
    affected_url: str | None
    endpoint: str | None
    param: str | None
    impact: str                     # lenguaje de negocio
    remediation: str
    references: list[str]

class AgenticResult(BaseModel):     # salida del subagente agéntico (§4) — congelado en finding.py (§15)
    type: str                       # chatbot | prompt_input | search_ai
    vendor: str | None              # Intercom, Drift… o None (superficie genérica)
    location_url: str
    inferred_model: str | None      # best-effort; NULL si "modelo no expuesto" (§4)
    agentic_status: Literal["no_surface","detected_not_tested","tested"]  # §9.1
    findings: list[Finding]         # hallazgos de los probes (source="agentic", canary/leak/jailbreak)

# ── Las tool-functions PARSEAN en Python y devuelven list[Finding] ya construido.
#    El parser determinista vive DENTRO de la función, nunca en el LLM.
def run_nuclei(url: str, level: str) -> list[Finding]:
    raw = run_subprocess(["nuclei", "-jsonl", "-duc", ...], timeout=90)  # §5 tabla
    return parse_nuclei(raw)        # JSONL → Finding[], mapeo OWASP por dict estático
# idem run_zap, run_testssl, run_security_headers, ... (cada tool tiene su dueño)

owasp_agent = Agent(
    name="OWASP Scanner", model=Claude("sonnet"),
    tools=[run_nuclei, run_zap, run_testssl, run_security_headers, run_whatweb,
           run_nikto, run_katana, run_ffuf, run_sqlmap, run_subfinder, hexstrike_mcp],
    instructions="Decide SOLO qué tools correr según el {level}. "
                 "NO redactes ni reconstruyas findings: las tools ya "
                 "devuelven Finding[] parseado; acumúlalos en el contexto.")
    # ⚠️ SIN response_model=list[Finding]: tools + structured output conviven mal
    #    en Agno/Claude (issues #2612/#2433/#2847) → el LLM re-teclea y trunca.

agentic_agent = Agent(
    name="Agentic Surface Auditor", model=Claude("sonnet"),
    tools=[crawl_site, classify_dom_llm, fingerprint_vendors,
           run_promptfoo, run_garak],
    instructions="Detecta chatbots/inputs de prompt y pruébalos según el nivel. "
                 "Mapea a OWASP-LLM Top 10. Las tools devuelven Finding[] + "
                 "inventario ya parseados; no los reconstruyas.")
    # ⚠️ Tampoco usa response_model para sintetizar findings.
    # ⚠️ El runner agéntico lo POSEE 03-agentic-surface: CAMINO A = puente
    #    Playwright-native (make_detect_surface / make_probe_agentic), siempre.
    #    run_garak/run_promptfoo son fallback opt-in CAMINO B, NUNCA sobre .gob.mx.

orchestrator = Team(
    mode="coordinate", model=Claude("opus"),
    members=[owasp_agent, agentic_agent],
    instructions="Coordina ambos subagentes EN PARALELO sobre {url} a nivel "
                 "{level}. El merge, la deduplicación y el scoring son Python "
                 "determinista (§9), NO tarea del LLM. Opus solo redacta el "
                 "resumen ejecutivo en lenguaje llano sobre un resumen compacto.")
```

La lista de tools del subagente OWASP **no es exhaustiva ni fija**: incluye explícitamente `run_security_headers` y `run_subfinder` (corrección de la consolidación) junto a `run_nuclei`, `run_zap`, `run_testssl`, `run_whatweb`, `run_nikto`, `run_katana`, `run_ffuf`, `run_sqlmap` y `hexstrike_mcp`. La asignación tool → nivel y la mecánica de invocación (Docker, helper `run_tool`, watchdog, redes y directorio compartido) están definidas en [04-scanning-engine](../04-scanning-engine/spec.md); aquí se asume que cada tool-function ya tiene un mecanismo de ejecución que le entrega salida cruda.

> **Nota B5 — modo `coordinate`.** "En paralelo" en este modo significa que el **coordinador LLM** dirige el fan-out hacia los miembros; no es un `asyncio.gather` literal escrito por nosotros. Los miembros se modelan como Agents lanzados concurrentemente bajo la coordinación de Opus. El orquestador delega `{url, level}` y cada subagente elige sus propias tools; el orquestador no selecciona tools ni construye findings.

## 2. Parsing fuera del LLM (decisión clave)

Las tool-functions (`run_nuclei`, `run_zap`, `run_testssl`, …) ejecutan el scanner **y** parsean su salida cruda a `list[Finding]` en **Python puro**; el parser determinista vive en la función. Los agentes Sonnet **NO** usan `response_model=list[Finding]`: solo deciden **qué** tools correr por nivel y acumulan los `Finding` en el contexto de sesión. El scoring y la deduplicación se calculan en Python (ver [07-scoring](../07-scoring/spec.md)). El `response_model` estructurado se reserva para Opus, exclusivamente para el resumen ejecutivo en texto. Verificar con un smoke-test que Agno detecta correctamente el structured-output de Claude **antes** del demo.

### 2.1 Por qué el parsing sale del LLM

`response_model=list[Finding]` sobre agentes con ~9 tools es zona de bug en Agno/Claude. Hay issues abiertos (Agno #2612, #2433, #2847) sobre que tools + structured output conviven mal, y sobre detección incorrecta del soporte de structured-output en modelos Claude (cae a un parsing menos fiable). Pedirle a Sonnet que "devuelva SOLO `Finding[]`" sintetizando JSONL crudo significa que **el LLM re-teclea findings, alucina o pierde campos (`cvss`, `evidence`) y trunca** cuando hay decenas de hallazgos. Si esto falla, el escaneo base —lo que **nunca** se recorta— no produce `Finding[]` válidos y no hay demo. La decisión es por tanto **sacar el parsing del LLM por completo**: las tool-functions devuelven `list[Finding]` ya parseado, el agente Agno **solo orquesta cuáles tools correr por nivel**, los `Finding` se acumulan en un objeto de sesión/contexto (no vía `response_model`), y el structured output (Opus) queda reservado al resumen ejecutivo en texto.

Esto tiene un corolario operativo: como las tools devuelven `Finding[]` deterministas, **todo el manejo de fallo parcial, dedup y scoring ocurre en Python**, sin pasar por el LLM (ver §4 y §5).

### 2.2 Parsers priorizados (1 persona full-time)

Hay ~8 formatos heterogéneos que no caben en el presupuesto de tiempo: Nuclei JSONL, ZAP JSON/XML jerárquico, testssl JSON, nikto (texto/CSV sin severidad), sqlmap (texto + sesión), whatweb JSON, garak `report.jsonl` y promptfoo results JSON. Mapear `severity` / `category` (A01–A10 / LLM01–LLM10) / `cvss` / `evidence` / `remediation` desde cada uno es lo que da valor del producto, y ninguna tool lo regala. Por eso se priorizan **3 parsers de alta densidad y buen JSON**, que garantizan nivel básico + ranking gov, cada uno con dueño:

| Parser | Entrada | Mapeo / notas |
|---|---|---|
| **Nuclei** | JSONL (`-jsonl`) | `info.severity` → severity; `classification.cvss-score` → cvss; `cwe` → category. Casi 1:1 |
| **testssl** | JSON (`-oJ`) | Hallazgos TLS/SSL → severity + A02/A05 vía dict |
| **security-headers / Observatory** | JSON (con grade) | Headers ausentes → Finding + A05 |

**ZAP baseline** es el 4º parser. **nikto/sqlmap** → parser best-effort (1 `Finding` genérico, severity media, sin OWASP fino) o se cortan. El **mapeo a categoría OWASP (`A01–A10` / `LLM01–LLM10`) es un dict/YAML estático curado** (template-id / probe → categoría); **nunca** se le pide al LLM. El estimado optimista de "2-5h para 4 parsers" se reemplaza por **1 persona full-time** dedicada a parsers, con recorte agresivo a los 3 priorizados + ZAP baseline.

## 3. Budget de tokens de Opus en la síntesis

"Opus solo en síntesis" se acota en tamaño: un avanzado genera cientos de findings; pasarle todo el `evidence` jsonb sería un prompt de miles de tokens, caro, lento y poco fiable para deduplicar. Por eso:

- El **scoring y el dedup** son fórmula / `dedupe_key` en Python, **antes** de tocar el LLM. Opus **no** calcula scores ni deduplica (ver [07-scoring](../07-scoring/spec.md)).
- A Opus se le pasa solo un **resumen compacto**: top-N por severidad (`title` + `severity` + `category` + `impact`, **sin** el `evidence` completo) para redactar "Owliver te explica" + los top-3 riesgos.
- Objetivo: Opus procesa **<2k tokens** por scan.

## 4. Timeouts, fallo parcial y budget

Timeout duro por tool en `subprocess.run(timeout=)` / `run_tool` (valores en la tabla de [04-scanning-engine](../04-scanning-engine/spec.md); de referencia: nuclei 90s, testssl 60s, ZAP baseline 120s, ZAP active 240s, sqlmap 120s, garak 180s) + **budget global de scan ~8 min**. Cada tool corre en `try/except`: si falla, expira o la bloquea un WAF → se emite un **Finding-meta** `"tool X no completó"` (`confidence=baja`, registrado también en `scans.coverage`) y el flujo **CONTINÚA** — nunca se propaga la excepción ni se pierden los findings ya listos. Como las tools devuelven `Finding[]` deterministas, todo el manejo de fallo parcial ocurre en Python, sin pasar por el LLM. Un scan colgado se puede cancelar (flag Redis chequeada entre tools).

El `Finding`-meta de cobertura y los enums (`status`, `confidence`, `coverage` shape) están definidos en [06-data-model](../06-data-model/spec.md); aquí se especifica únicamente la política de continuación: aislar cada tool, degradar a meta-finding y seguir.

## 5. Flujo del worker

1. Recoge job de Redis (SAQ) → marca `scan.status=running`, publica evento `agent_status` (con `seq` monótono) al canal `scan:{id}:events`.
2. Lanza `orchestrator.run(url, level)` — el orquestador **delega `{url, level}`** y corre los 2 subagentes en paralelo (los miembros se modelan como Agents lanzados concurrentemente bajo la coordinación del LLM en modo `coordinate`, ver Nota B5 en §1.1; no es un `asyncio.gather` literal nuestro). **Cada subagente elige sus propias tools** según el nivel; el orquestador no selecciona tools ni construye findings.
3. Cada tool corre con su **timeout duro** y dentro del **budget global ~8 min**; al agotarse el budget un **watchdog aborta las tools restantes** (además del cancel manual chequeado entre tools, §4), garantizando el cierre del scan. Su salida cruda se parsea a `Finding[]` **en Python dentro de la tool**. Si una tool falla/expira → Finding-meta de cobertura y se continúa (fallo parcial). Cada paso publica eventos tipados (`tool_start` / `tool_end` / `finding`) a Redis pub/sub para el live view.
4. **Merge + dedup + scoring en Python** (ver [07-scoring](../07-scoring/spec.md)): dedup por `dedupe_key`, cálculo de `web_score`, `agentic_score`, `agentic_status`, `overall_score`, `overall_grade` y `penalty_raw`. Opus genera el **resumen ejecutivo** sobre el resumen compacto (<2k tokens), no sobre el evidence crudo.
5. Persiste `scans` (+ `coverage`, `tools_status`) + `findings` + `agentic_surface` + `scan_events` en Postgres → `status=done` (o `partial` si faltó ≥1 scanner base). Evidencia/screenshots quedan en `/data/scans/{scan_id}/` y se referencian por URL relativa en `evidence`.

El detalle del watchdog y la cancelación a nivel de proceso pertenece a [04-scanning-engine](../04-scanning-engine/spec.md); el detalle del live-view (replay de `scan_events`, `seq` monótono, canales pub/sub) pertenece a la spec de observabilidad/live-view. Aquí el worker es el coordinador que pega todo: lanza el Team, recoge `Finding[]` deterministas, delega scoring a Python y síntesis a Opus, y persiste.

## 6. Resumen de contratos que este subspec produce y consume

- **Produce:** `Finding[]` ya parseado y deterministas por tool-function; el resumen ejecutivo de Opus (texto, <2k tokens); los `Finding`-meta de cobertura ante fallo parcial.
- **Consume:** las shapes `Finding` / `AgenticResult` y enums de [06-data-model](../06-data-model/spec.md); la mecánica de invocación de scanners (Docker, `run_tool`, watchdog, redes, dir compartido) de [04-scanning-engine](../04-scanning-engine/spec.md); el puente de ataque agéntico, LLM-juez y canary de [03-agentic-surface](../03-agentic-surface/spec.md).
- **Delega:** dedup, scoring y grading a [07-scoring](../07-scoring/spec.md) (Python determinista; el LLM nunca lo calcula).
