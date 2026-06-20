---
feature: pipeline
type: plan
status: implemented
coverage: 90
audited: 2026-06-16
---

# Propuesta · Configuración por fase del pipeline (`PhaseSpec.config` tipado)

> **Estado:** propuesta para revisión con Vic · **implementación pendiente**.
> **No re-litiga** decisiones ya zanjadas: pipeline 1:1 propiedad del workflow + sellado inmutable
> (ADR `docs/adr/0002`), capacidades derivadas del pipeline (ADR `docs/adr/0003`), tools
> workflow-scoped 1:1 (migración `c9d0e1f2a3b4`), y la gramática de tokens
> **`@` adentro · `#` afuera · `{{}}` runtime** (`product/plans/tools/rule-tools.md`).
> **Extiende** el modelo de fases: hoy cada fase ya lleva un `config: dict`; aquí se propone
> **tiparlo, validarlo y completar los knobs** que el negocio necesita por fase.
>
> **Ubicación:** este archivo vive en `plans/proposal/` (singular), junto a `pipeline.md`,
> `rule-tools.md`, `unified-workflow.md`, `arquitectura.html`… (consolidado desde `plans/proposals/`
> plural, donde se creó originalmente — ver D-F, resuelto).

---

## 1. Objetivo

Que tanto **capacidades** como **fases** del pipeline tengan valores configurables, declarativos y
versionados, p. ej.:

- `extract_text` → qué **extractor** corre la extracción.
- `classify_pages` → qué **algoritmo** clasifica y soporte de **clasificador custom por tenant**.
- `extract_fields` → qué **document_types** aplican y qué **campos/metadatos** (p. ej. `ocr_confidence`,
  `bounding_boxes`) entran en los eventos.
- `await_documents` → qué documentos se esperan, con qué **cardinalidad**, y si se **auto-avanza** o
  requiere pase manual.
- `enrich` → qué **tools** corren y con qué **argumentos**, soportando no solo HTTP sino **scripts
  Python y JS/TS**.
- `approval` → **quién** aprueba, **cuántas** aprobaciones se requieren, escalamiento.
- **policies** → qué políticas existen y en qué fases se configuran.

Todo ello respetando el contrato de **determinismo de Temporal**: la config se **sella con la versión**
del pipeline; editarla produce una **nueva versión** (no muta runs en vuelo).

---

## 2. Cómo funciona hoy (estado actual del motor)

### 2.1 Representación de una fase

`backend/src/workflows/domain/models/pipeline.py`:

```python
class PhaseSpec(BaseModel):
    id: str                         # id único de la fase dentro del pipeline
    kind: PhaseKind                 # enum (ingest, extract_text, classify_pages, …)
    config: dict = Field(default_factory=dict)   # ← config por fase (HOY: dict libre)
    when: str | None = None         # predicado declarativo (p. ej. "gate.review > 0")

class PipelineVersion(BaseModel):
    uuid: UUID
    pipeline_id: UUID
    version: int                       # inmutable, append-only
    phases: list[PhaseSpec]
    output_schema: dict | None
    activation_policy: dict | None     # política case-level (sellada con la versión)
    completeness_policy: dict | None   # case-level; D-A: a plegar en await_documents.config; columna a dropear en el squash
    created_at: datetime | None = None
```

### 2.2 Persistencia

`backend/src/common/database/models/pipeline.py`:

- `pipelines` (1:1 con `workflows`, ADR 0002): contenedor (`workflow_id` UNIQUE, `slug`, `kind`,
  `status`, `current_version`). **Sin config por fase.**
- `pipeline_versions`: **`phases` JSONB** (la lista ordenada de `PhaseSpec` con su `config`),
  `output_schema` JSONB, `activation_policy` JSONB, `completeness_policy` JSONB. **Inmutable,
  append-only**; cada edición = fila nueva (`version` n+1).
- Round-trip sin pérdida: escritura `p.model_dump(mode="json")` en
  `infrastructure/repositories/sql_pipeline.py`; lectura `PhaseSpec.model_validate(p)` en
  `infrastructure/builders/pipeline.py` (invocado por el repo); export/import en
  `application/workflows/import_export/`.

`backend/src/common/database/models/tool_definition.py` (tools 1:1 por workflow):
`{workflow_id, name, display_name, description, transport ("HTTP"), connection_account_id,
input_schema, output_schema, config JSONB, enabled}`.

### 2.3 Ejecución (intérprete)

`backend/src/workflows/application/pipelines/runtime.py` → `execute_pipeline`:

```python
for phase in phases:
    if state.terminated: break
    if not evaluate_when(phase.when, state): continue        # predicado declarativo
    handler = PHASE_LIBRARY.get(phase.kind.value)            # registro @register_phase
    await handler(ctx, phase, state)                         # recibe phase.config
```

Cada handler lee su config **ad-hoc** con `phase.config.get("clave", default_hardcodeado)`. Las
políticas se siembran en `state.scratch["policies"]` al inicio del run y las leen los handlers de
caso (p. ej. `pause_phases`, `gate_phases`, `analysis_phases`). El catálogo de schemas que consume el
editor vive aparte en `domain/services/phase_catalog.py` (`GET /v1/pipelines/phase-catalog`).

### 2.4 Capacidades (ADR 0003)

`derive_capabilities(version)` infiere capacidades del set de `kind`s presentes;
`apply_capability(...)` inserta fases + andamiaje de política de forma idempotente
(`POST /v1/workflows/{workflow_id}/pipeline/capabilities`). Una capacidad = uno o más `PhaseSpec` +
parches a políticas.

---

## 3. Catálogo completo de fases (15)

| Fase (`id`) | `kind` | Scope | Qué hace |
|---|---|---|---|
| `ingest` | `INGEST` | document | Sella el input; checkpoint DISPATCHED |
| `extract_text` | `EXTRACT_TEXT` | document | OCR/extracción de texto (lambda) |
| `classify_pages` | `CLASSIFY_PAGES` | document | Split + clasificación de páginas; fan-out opcional |
| `extract_fields` | `EXTRACT_FIELDS` | document | Extracción de campos por document_type |
| `assess` | `ASSESS` | document | Confianza capa-2 (LLM puntúa campos vs evidencia) |
| `validate_extraction` | `VALIDATE_EXTRACTION` | document | Validación por documento; **persiste textos, marca docs** (`PERSIST_DOCUMENT_TEXTS`/`MARK_DOCUMENT_STATUS`), emite `DOCUMENT_PERSISTED` |
| `finalize` | `FINALIZE` | document | Estado terminal + webhook `document.extracted` (`dispatch_webhook`) + señalización/cierre de caso |
| `await_documents` | `AWAIT_DOCUMENTS` | case | Espera completitud del expediente (policy + señales) |
| `confidence_gate` | `CONFIDENCE_GATE` | case | Evalúa ActivationPolicy → flags clarify/review |
| `await_clarification` | `AWAIT_CLARIFICATION` | case | Abre tarea de aclaración y espera |
| `enrich` | `ENRICH` | case | Enriquecimiento vía tools firmadas (eager) |
| `human_review` | `HUMAN_REVIEW` | case | Revisión (L1/L2) o aprobación (gate humano) |
| `analyze` | `ANALYZE` | case | Workflow hijo de análisis de reglas |
| `output` | `OUTPUT` | case | Proyección x-source + síntesis LLM vs `output_schema` |
| `deliver` | `DELIVER` | case | Emite `case.output.ready` / `case.failed` al outbox |

---

## 4. Principios de diseño

1. **La config se sella con la versión.** Vive en `PhaseSpec.config` (JSONB dentro de
   `pipeline_versions.phases`), inmutable. Editar config = **publicar nueva versión**. Nunca muta runs
   sellados. (Idéntico contrato que ADR 0002.)
2. **Una sola fuente de verdad de schema.** Se introducen **modelos Pydantic tipados por `kind`**
   (`ExtractTextConfig`, `ClassifyPagesConfig`, …). De esos modelos se **genera** el `phase_catalog`
   (JSON Schema) que consume el editor → el formulario del editor y la validación del backend nunca
   divergen.
3. **Validate-on-write y validate-on-read.** Al **publicar/importar** una versión se valida cada
   `config` contra su modelo (422 con el mismo patrón del publish). En el handler se parsea con el
   modelo tipado (cero `.get()` dispersos). **La validación NO re-serializa**: el publish persiste el
   JSON entrante tal cual (**sin re-serializar**; `model_dump(by_alias=True, exclude_unset=True)` solo al re-generar desde el modelo) para **no materializar
   defaults** ni romper claves con alias (p. ej. `lambda`) en `phases` — condición necesaria para el
   golden byte-idéntico de F0 (§9).
4. **Lo dinámico/tenant se referencia por slug y se resuelve en activities.** Cualquier cosa cuyo
   valor concreto cambia fuera del sellado (clasificador custom del tenant, credencial/endpoint de una
   tool, fuente de un script) se guarda como **referencia por slug/id** en la config sellada; la
   **resolución real** ocurre dentro de una **activity** (no en el código del workflow), preservando el
   determinismo.
5. **Capacidad ⇒ config por defecto.** `apply_capability` siembra la fase **con su `config` por
   defecto** ya válido (extiende los macros de ADR 0003).
6. **Compatibilidad de tokens.** Los argumentos de tools/scripts usan la gramática vigente
   (`@slug.path`, `{{system_var}}`); no se inventa sintaxis nueva (alineado con `rule-tools.md`).

---

## 5. Mapeo fase × configuración (HOY vs PROPUESTA)

> Leyenda estado: ✅ existe · 🟡 parcial (legible pero no en schema/editor) · 🆕 nuevo.

### Document scope

| Fase | Config HOY | Config PROPUESTA (nuevo/expuesto) | Estado |
|---|---|---|---|
| `ingest` | — | — (sin config) | — |
| `extract_text` | `extractor`, `timeout_seconds` (🟡), `lambda`/`lambda_alias` | exponer `extractor` (enum + `auto`) y `timeout_seconds` en schema; **`per_type_overrides`**: extractor distinto por document_type | ✅/🆕 |
| `classify_pages` | `fan_out`, `fan_out_types`, `fan_out_max_children`, `lambda`/`lambda_alias` | **`classifier`**: `"default"` \| `<slug-registry>` (algoritmo pluggable + **clasificador custom por tenant**) | 🟡/🆕 |
| `extract_fields` | `lambda`/`lambda_alias` | **`document_types`** (subconjunto a extraer); **`emit`**: `include_ocr_confidence`, `include_bounding_boxes`, `fields: "all"\|[…]` | 🆕 |
| `assess` | — | `provider` (override LLM capa-2), `min_confidence` | 🆕 |
| `validate_extraction` | — | `rule_severities` (qué severidades bloquean a nivel doc) | 🆕 |
| `finalize` | `dispatch_webhook` | **`webhook_projection`** (qué campos/metadatos viajan en `document.extracted`) | 🆕 |

### Case scope

| Fase | Config HOY | Config PROPUESTA (nuevo/expuesto) | Estado |
|---|---|---|---|
| `await_documents` | `CompletenessPolicy` (version-level): `required_types`, `auto_ready` | mover/exponer **`completeness`** en la config de la fase: `required_types: {slug: int}` (cardinalidad mínima), **`advance`**: `"auto"\|"manual"` (= `auto_ready`; default `manual` = `auto_ready=False` actual) | 🟡→🆕 |
| `confidence_gate` | `ActivationPolicy` (version-level): `field_thresholds`, `on_low_confidence`, `blocking_rule_severities` | exponer estos campos **bajo la fase** en el editor (almacenamiento: ver §7/D-A). *(`sample_rate` lo consume `human_review`, no esta fase.)* | 🟡 |
| `await_clarification` | — | `audience`, `timeout`/escalamiento | 🆕 |
| `enrich` | bindings de tools (`tool`, `args`, `on_failure`) — **solo HTTP** | **`tools: [{tool, args, on_failure}]`** explícito + **transportes Python y JS/TS** (ver §6.4) | 🟡/🆕 |
| `human_review` | `kind: review\|approval`, `trigger`; `ActivationPolicy.stages` (L1/L2, `mode`); `audience` (RBAC libre); claim/lock | **`approvers`** (roles/usuarios/audience), **`approvals_required: N`** (quórum N-de-M), **`distinct_approvers`**, **`timeout`/escalamiento** | ✅/🆕 |
| `analyze` | — | `providers` (parser/reviewer/critic/synthesizer/assess override), `rule_set` | 🆕 |
| `output` | `output_schema` (version-level) | `synthesizer_provider`, `projection` | 🟡/🆕 |
| `deliver` | destinos del workflow | `channels` (qué destinos), `payload_projection` | 🆕 |

---

## 6. Especificación por fase (las que pediste)

> **Base común `PhaseConfig`** (de la que heredan todos los modelos por `kind`):
> ```python
> class PhaseConfig(BaseModel):
>     # extra="forbid" ⇒ publish/import rechaza claves desconocidas (422).
>     # populate_by_name ⇒ valida aceptando tanto el nombre del campo como su alias.
>     model_config = ConfigDict(extra="forbid", populate_by_name=True)
> ```
> **Serialización:** el publish persiste el JSON entrante tal cual; al re-generar desde el modelo se
> usa `model_dump(mode="json", by_alias=True, exclude_unset=True)` para **no materializar defaults**
> ni romper claves con alias (p. ej. `lambda`) — condición del golden byte-idéntico (§4.3).

> **Alcance de §6:** §6.1–§6.6 detallan las fases con los knobs más sustantivos; §6.7–§6.12 cubren las
> 6 restantes (`assess`, `validate_extraction`, `await_clarification`, `analyze`, `output`, `deliver`)
> — las 15 fases quedan tipadas (D-J, §11). §6.13 lista las políticas existentes.

### 6.1 `extract_text` — selección de extractor

- **Hoy:** `phase.config.get("extractor", DEFAULT_EXTRACTOR)` (default `textract_layout`);
  `timeout_seconds` legible pero fuera del schema. Extractores disponibles
  (`DocumentExtractorType`): `textract`, `textract_layout`, `documentai`, `documentai_layout`,
  `textractor(_layout)`, `mistral_ocr`, `vlm` (Gemini visión), `asr` (Gemini audio), `auto`.
- **Propuesta:**
  ```python
  class ExtractTextConfig(PhaseConfig):
      extractor: DocumentExtractorType = DocumentExtractorType.TEXTRACT_LAYOUT  # = default actual; preserva runs sellados sin la clave
      timeout_seconds: int | None = None
      per_type_overrides: dict[str, DocumentExtractorType] = {}   # doc_type_slug → extractor
      lambda_: str | None = Field(default=None, alias="lambda")    # clave JSON sellada = "lambda"
      lambda_alias: str | None = None                              # override avanzado
  ```
- **Default sellado:** el modelo usa `TEXTRACT_LAYOUT` (el `DEFAULT_EXTRACTOR` de hoy) para que una
  versión ya sellada **sin** la clave `extractor` reproduzca su comportamiento al parsearse. Si se
  quiere `AUTO` como arranque, va como **default del editor para pipelines nuevos** (no del modelo) o
  vía backfill explícito de las versiones existentes (ver Riesgo §10.6).
- **Dónde se usa:** `extraction_phases.extract_text` (parsea `ExtractTextConfig`). **Orden:**
  `extract_text` corre **antes** de `classify_pages`, así que en la 1ª pasada el `document_type` aún
  no se conoce ⇒ `per_type_overrides` **solo surte efecto en re-extracción** (o cuando el tipo viene
  dado en el upload). **Fallback explícito:** sin tipo conocido —o con tipo presente pero **no
  mapeado** en `per_type_overrides`— se usa el `extractor` de nivel superior (el override es no-op).

### 6.2 `classify_pages` — algoritmo + clasificador custom por tenant

- **Hoy:** **un solo** algoritmo (lambda base `vnext-tools-classify_pages`, resuelta con sufijo de
  stage). `fan_out`/`fan_out_types`/`fan_out_max_children` configurables. **No** hay selección de
  algoritmo ni clasificador por tenant.
- **Propuesta:**
  ```python
  class ClassifyPagesConfig(PhaseConfig):
      classifier: str = "default"           # "default" | "<slug del registry de clasificadores>"
      fan_out: Literal["child_cases"] | None = None
      fan_out_types: list[str] = []
      fan_out_max_children: int = 100
  ```
  - **Registry de clasificadores** (nuevo, tenant-scoped): tabla `classifiers`
    `{tenant_id, slug, kind (lambda|prompt|tool), config JSONB, enabled}`. `classifier="<slug>"`
    referencia una entrada; la **resolución** (qué lambda/prompt corre) ocurre en una **activity**
    (`resolve_classifier`), no en el workflow → determinismo intacto.
    - **Contrato por `kind`** (propuesto, lo consume `resolve_classifier`): `lambda` → `{function, alias?}`;
      `prompt` → `{provider, prompt_template, output_schema}`; `tool` → `{tool_slug, transport}`.
  - "Clasificación custom por encargo" = alta de una fila en `classifiers` para ese tenant + set
    `classifier` en la config de su pipeline (nueva versión).
- **Dónde se usa:** `extraction_phases.classify_pages` resuelve `classifier` vía activity y dispara el
  motor correspondiente. *Ver D-C (RESUELTO §11): registry dedicado tenant-scoped, resuelto en la activity `resolve_classifier`.*

### 6.3 `extract_fields` — document_types y campos en eventos

- **Hoy:** lambda por documento; cada entrada del artifact es `{output, mapped_output}` (+
  `document_index`). **Los `bounding_boxes` SÍ se calculan y persisten**: cada `MappedLeaf` lleva `bbox`,
  y la **confianza** existe como `BBoxHit.confidence` (por bbox) + la confianza **por campo** que deriva
  `compute_field_confidence` (`leaf_confidence` = min de las bbox) y se persiste en
  `WorkflowDocument.field_confidence`. **No** hay un `ocr_confidence` a nivel de hoja. Se consumen aguas
  abajo (`collect_extraction_pages`, `extraction_pages.py`). Lo que falta hoy: (a) **no** se proyectan
  a eventos/webhook y (b) **no** hay filtro de `document_types` ni control de qué metadatos se exponen
  a nivel fase.
- **Propuesta:**
  ```python
  class FieldEmitConfig(BaseModel):
      include_ocr_confidence: bool = False     # proyecta la confianza ya derivada (field_confidence / BBoxHit.confidence)
      include_bounding_boxes: bool = False
      fields: Literal["all"] | list[str] = "all"

  class ExtractFieldsConfig(PhaseConfig):
      document_types: list[str] | None = None   # None = todos los del expediente
      emit: FieldEmitConfig = FieldEmitConfig()
  ```
  - `mapped_output` se persiste **siempre completo** (bbox y confianza por bbox/campo sin cambios);
    `emit` es un **filtro de proyección** a eventos — **no borra** nada del artifact ni cambia qué se
    calcula.
  - **Precedencia `emit` vs `webhook_projection`:** `extract_fields.emit` acota **qué metadatos se
    proyectan** al evento de extracción (hoy `validate_extraction` emite `DOCUMENT_PERSISTED`, no
    `STEP_COMPLETED`; exponer ahí bbox/confianza es trabajo **nuevo** de F2); `finalize.webhook_projection`
    **selecciona de eso** qué entra en el webhook `document.extracted`. Una `webhook_projection` que
    referencie un campo no proyectado por `emit` es **error de publish (422)**, no un no-op silencioso.
- **Dónde se usa:** `extraction_phases.extract_fields` (proyección por `emit`) +
  `finalize` (proyección del webhook). *Ver D-B (RESUELTO §11): defaults `include_*` en `false`
  (opt-in) por tamaño de payload.*

### 6.4 `enrich` — tools (HTTP + Python + JS/TS) y argumentos

- **Hoy:** enrich corre **una** tool firmada (un binding por fase) **siempre** en su fase (eager), vía
  `tool_lookup` (HMAC/allowlist/jsonschema/`on_failure`). Args templados (`@slug.path`, `{{tokens}}`,
  `{placeholders}` en URL). **Solo transporte HTTP** (`ToolTransport.HTTP`). La lista multi-tool
  (`tools: [...]`) es parte de la propuesta.
- **Propuesta de config de la fase:**
  ```python
  class EnrichToolBinding(BaseModel):
      tool: str                              # slug de la tool (workflow-scoped)
      args: dict[str, str] = {}              # templates @slug.path / {{system_var}}
      on_failure: Literal["fail","continue","review"] = "review"   # mismo nombre y default que hoy (enrich_phases.py:85); ver D-G

  class EnrichConfig(PhaseConfig):
      tools: list[EnrichToolBinding] = []
  ```
- **Transportes no-HTTP (el build grande):** extender el enum
  `ToolTransport = {HTTP, PYTHON, JS}` y añadir dispatch en el connector
  (`infrastructure/services/tools/connector.py`). El **código** del script se guarda en
  `tool_definitions.config` (inline o por referencia a object storage) + `runtime`/`entrypoint`.
  La **ejecución** ocurre en un **runner aislado** (D-D: contenedor sandbox in-cluster —
  gVisor/Firecracker) con **sin red salvo allowlist**, límites de CPU/tiempo/memoria y sin acceso a
  secretos fuera de los inyectados. Mismo render de args y mismo `on_failure`.
  Beneficia a `enrich` (eager), que ya pasa por `tool_lookup`. *(Nota: hoy **no** existe resolución
  lazy de tools desde reglas — el namespace `#` cubre `#kb.<slug>` (KB; alias legacy `#<slug>`) y
  reserva el sub-slug `#tool.<slug>.path` para tools (propuesto en `rule-tools.md`); un token de tool en
  reglas queda fuera de este alcance y del principio §4.6.)*
- **Dónde se usa:** `enrich_phases` (eager).
  *D-D **resuelto**: ejecución en contenedor sandbox in-cluster (gVisor/Firecracker) — requiere
  **ADR + revisión de seguridad** propio.*

### 6.5 `await_documents` — documentos esperados, cardinalidad, auto/manual

- **Hoy:** la config real está en `CompletenessPolicy` (version-level): `required_types: {slug: int}`
  (cardinalidad mínima por tipo, validador exige ≥1) y `auto_ready: bool`. El handler espera señales
  `case_docs_changed`/`case_ready`; `auto_ready=True` ⇒ avanza al cumplirse; `False` ⇒ exige señal
  `case_ready` (con override `force`).
- **Propuesta:** exponer/mover a la config de la fase:
  ```python
  class AwaitDocumentsConfig(PhaseConfig):
      required_types: dict[str, int] = {}            # doc_type_slug → cardinalidad mínima
      advance: Literal["auto","manual"] = "manual"   # = auto_ready
  ```
- **Dónde se usa:** `pause_phases.await_documents`. *Ver D-A (RESUELTO §11): `completeness` se pliega en
  `await_documents.config`; la columna version-level se dropea en el squash.* `force` es un override
  runtime out-of-band (payload de la señal `case_ready`), **no** un campo de config; sin cambios bajo
  `advance="manual"`.

### 6.6 `human_review` (approval) — quién y cuántos

- **Hoy:** `kind: review|approval`, `trigger`; etapas L1/L2 vía `ActivationPolicy.stages`
  (`ReviewStage{stage, mode: mandatory|by_exception}`); `audience` libre (RBAC externo); **claim/lock**
  (`HumanTask.claimed_by`): reclamar/resolver una tarea ya tomada por otro actor devuelve **409**
  (`HumanTaskClaimConflictError`); el **lock a nivel caso** (`CaseLockedError`, guarda
  corrección/verify mientras el APPROVAL abierto está tomado por otro) devuelve **423**. Aprobación es
  **single** (approve/reject); **no** hay quórum ni recuento.
- **Propuesta:**
  ```python
  class ApproverSpec(BaseModel):
      roles: list[str] = []                   # roles permitidos (matriz rol×acción, E5)
      users: list[str] = []                   # user_ids específicos
      audience: str | None = None             # audience RBAC (igual que hoy)

  # Duration = str ISO-8601 (p. ej. "PT48H"); forma de wire estable para el sellado/golden.

  class HumanReviewConfig(PhaseConfig):        # sigue la recomendación de D-H (kind = HUMAN_REVIEW; cubre review y approval)
      kind: Literal["review","approval"] = "approval"
      approvers: ApproverSpec = ApproverSpec() # default vacío ⇒ el parse de runs sellados no rompe (§10.6)
      approvals_required: int = 1             # quórum N-de-M (por gate; ver D-E)
      distinct_approvers: bool = True         # N personas distintas
      timeout: str | None = None              # Duration ISO-8601; None ⇒ espera indefinida; si se fija, al expirar **auto-rechaza** (fail-safe, D-I)
      stages: list[ReviewStage] = []          # solo kind="review" (L1/L2); ReviewStage de domain/models/policies.py
  ```
  - Requiere **recuento de votos**: el handler abre tarea(s) y acumula aprobaciones hasta `N`
    (estado en el run); integra la **matriz rol×acción** (E5) para autorizar al aprobador. **Rechazo
    (D-I):** cada reject **descuenta del quórum**; el gate falla cuando los rechazos hacen **imposible**
    alcanzar `N` aprobaciones de la audiencia permitida (no termina al primer reject).
  - **Validadores (publish):** `approvers` debe fijar ≥1 de `roles`/`users`/`audience` (422), análogo al
    `required_types ≥1` de completeness; el `audience` libre de configs selladas hoy se mapea a
    `approvers.audience` en el backfill de F4. `stages` solo aplica con `kind="review"`;
    `approvals_required`/`distinct_approvers` solo con `kind="approval"` (campos cruzados ⇒ 422).
- **Dónde se usa:** `pause_phases` (gate de aprobación/revisión). *Ver D-E (RESUELTO §11): quórum **por
  gate** (N aprobadores distintos de la audiencia permitida), etapas L1/L2 **secuenciales**, `timeout`
  opcional.* *Ver D-I (RESUELTO §11): al expirar `timeout` el gate **auto-rechaza** (fail-safe); un
  rechazo individual **descuenta del quórum** (falla cuando `N` se vuelve inalcanzable).*

### 6.7 `assess` — proveedor de la confianza capa-2

- **Hoy:** corre **después** de `extract_fields`; por cada documento con campos lanza **una** activity
  `assess_document` (un LLM capa-2 que puntúa cada campo contra el texto OCR y persiste
  `extract_confidence` + `signals` + `needs_clarification`). Es **label-only**: un fallo loggea y sigue,
  nunca tumba el doc ni el run. **No lee `phase.config`**; timeout/retry/proveedor están hardcodeados
  (`_ASSESS_TIMEOUT=90s`, `_ASSESS_RETRY_POLICY=2`; `assess_phases.py:47-48`). El proveedor se resuelve
  en la activity vía `default_llm_runner("assess")` (env `ANALYSIS_ASSESS_PROVIDER`, default →
  `openai:gpt-4o-mini`).
- **Propuesta** (todos los campos **net-new**; defaults = comportamiento actual):
  ```python
  class AssessConfig(PhaseConfig):
      provider: str | None = None         # override LLM capa-2 ("provider:model"); None ⇒ env ANALYSIS_ASSESS_PROVIDER
      min_confidence: float | None = None # None ⇒ flag solo por `signals` (hoy); si se fija, umbral sobre extract_confidence
      timeout: str | None = "PT90S"       # Duration ISO-8601; = _ASSESS_TIMEOUT actual
      max_attempts: int = 2               # = _ASSESS_RETRY_POLICY actual
  ```
  - `provider` se resuelve **dentro de** `assess_document` (nunca en el workflow). *Abierto:* si
    `min_confidence` se cablea de verdad aquí o queda no-op — hoy el flag es por `signals`, y el umbral
    numérico (0.6) vive en `confidence_gate`, no en assess.
- **Dónde se usa:** `assess_phases.assess`.

### 6.8 `validate_extraction` — severidades que bloquean

- **Hoy:** invoca la lambda `vnext-tools-validate_extraction-<stage>` (resuelta por
  `resolve_lambda_function`, timeout 5 min) para todos los survivors; devuelve `validations` (con
  `validation_results`: `status`+`severity`) y `errors` (solo si la lambda **lanzó excepción**). Un doc
  se marca **FAILED solo** si su índice está en `errors`; las severidades por regla **se persisten y
  cuentan, pero nunca bloquean** pass/fail. (También persiste textos y marca docs — §3 —, fuera de esta
  config.)
- **Propuesta:**
  ```python
  class ValidateExtractionConfig(PhaseConfig):
      lambda_function: str | None = Field(default=None, alias="lambda")  # pin explícito; None ⇒ default de catálogo
      lambda_alias: str | None = None      # sufijo alias/version sobre el default; ignorado si lambda_function
      timeout: str | None = "PT5M"         # Duration ISO-8601; = timedelta(minutes=5) actual
      rule_severities: list[str] = []      # net-new (§5); [] ⇒ hoy (nada bloquea salvo error de lambda)
  ```
  - **Severidades:** el enum de validación de extracción es **`info|low|medium|high|critical`**
    (vnext-tools), **distinto** del `WorkflowRuleSeverity` de reglas de negocio
    (`BLOCKER|MAJOR|MINOR|INFO`). *Abierto:* (a) si `rule_severities` gatea solo `status="failed"` o
    también `warning`/`missing_data`; (b) si un fail por severidad rutea a `_fail_document` (FAILED duro)
    o a un outcome más suave; (c) confirmar el set de valores antes de sellar.
- **Dónde se usa:** `extraction_phases.validate_extraction`.

### 6.9 `await_clarification` — audiencia y (futuro) escalamiento

- **Hoy:** abre una HumanTask de aclaración y **bloquea indefinidamente** hasta la señal `task_resolved`.
  Dos rutas: la rica (con gate items) corre `open_clarification_task`, pasa el caso a
  `NEEDS_CLARIFICATION`, dispara webhook `case.needs_clarification` best-effort, espera y vuelve a
  `PROCESSING`; la fallback (`_open_and_wait`) abre una HumanTask `CLARIFICATION` genérica. **No hay
  timeout/escalamiento en Temporal** (espera no acotada). Lee de config: `audience`, `expires_in_hours`
  (solo sella `HumanTask.expires_at`, **sin** timer), `assignee_mode` (default `EXTERNAL_CALLBACK`),
  `payload` (solo ruta fallback).
- **Propuesta:**
  ```python
  class AwaitClarificationConfig(PhaseConfig):
      audience: str | None = None           # RBAC en endpoints (no en el workflow); = hoy
      expires_in_hours: float | None = None # sella expires_at (metadata; NO crea timer); = hoy
      assignee_mode: HumanTaskAssigneeMode = HumanTaskAssigneeMode.EXTERNAL_CALLBACK
      payload: dict[str, Any] = {}          # solo ruta fallback
      resolution_timeout: str | None = None # net-new; None ⇒ espera indefinida (= hoy y = human_review)
      on_timeout: Literal["escalate","auto_resolve","fail"] | None = None  # net-new; solo si resolution_timeout
  ```
  - *Abierto:* el escalamiento por timeout es **net-new** (igual que en `human_review`, hoy sin timer);
    definir qué hace `on_timeout` y si `resolution_timeout` reusa `expires_in_hours` o es independiente.
    Default `None`/`None` = espera no acotada actual.
- **Dónde se usa:** `pause_phases.await_clarification`.

### 6.10 `analyze` — proveedores LLM y rule set

- **Hoy:** salta si no hay caso; si no, pasa el caso a `ANALYZING`, mintea `run_id` (`workflow.uuid4()`),
  crea el run (`create_analysis_run`, idempotente, schedule_to_close 15 min serializa runs concurrentes
  del mismo caso) y lanza el **child workflow** `WorkflowAnalysisRunWorkflow` (`ABANDON`). **No lee config
  ni elige proveedores/reglas**: los roles LLM (`parser`/`evaluator`/`synthesizer`; `critic` declarado
  pero **no invocado**) se resuelven **dentro de las activities del child** vía `default_llm_runner(role)`
  leyendo env `ANALYSIS_*_PROVIDER` (default → `openai:gpt-4o-mini`); las reglas = **todas las activas**
  del workflow (no existe "rule set" nombrado hoy).
- **Propuesta** (todos **net-new**):
  ```python
  class AnalyzeConfig(PhaseConfig):
      parser_provider: str | None = None        # None ⇒ env ANALYSIS_PARSER_PROVIDER
      reviewer_provider: str | None = None      # rol "evaluator" (= ANALYSIS_REVIEWER_PROVIDER)
      critic_provider: str | None = None        # rol declarado pero inerte (sin call site hoy)
      synthesizer_provider: str | None = None   # narrativa del run
      rule_set: str | None = None               # ref por slug; None ⇒ todas las reglas activas
      child_workflow_timeout: str | None = None # None ⇒ sin tope (hoy)
      active_run_wait_timeout: str | None = "PT15M"  # = ACTIVE_RUN_WAIT_TIMEOUT actual
  ```
  - Los overrides de proveedor y el `rule_set` se **resuelven en las activities del child**
    (`evaluate_rule_combination`, `complete_analysis_run`, `load_analysis_run_plan`), nunca en código de
    workflow. `None` preserva el default env-global de hoy; fijar un valor mueve la resolución a
    **per-pipeline**. *Abierto:* (a) hoy los proveedores son **env/proceso-global**, no per-tenant —
    sellarlos per-pipeline es el feature, no un bug; (b) `critic` queda inerte hasta que exista call
    site; (c) `rule_set` introduce un concepto nuevo (selección nombrada) a resolver en
    `load_analysis_run_plan`. El override del rol `assess` vive en `AssessConfig` (§6.7), no aquí.
- **Dónde se usa:** `analysis_phases.analyze` (+ activities del child).

### 6.11 `output` — proveedor de síntesis y proyección

- **Hoy:** salta para runs sin caso; si no, invoca `build_case_output` (timeout 5 min) y guarda un
  artifact `case_output` compacto. Todo el trabajo real (outputs por doc, **proyección determinista
  x-source** sobre `output_schema`, y la **síntesis LLM** acotada a `output_schema`) ocurre **dentro de
  la activity** → `SynthesisRunner.execute`. **No lee `phase.config`**: el agente sintetizador es
  singleton de proceso (`default_llm_runner("synthesizer")`) y
  `output_schema`/`synthesis_template`/`synthesis_enabled` viven a **nivel versión** (workflow).
- **Propuesta:**
  ```python
  class OutputConfig(PhaseConfig):
      synthesizer_provider: str | None = None  # net-new; None ⇒ ANALYSIS_SYNTHESIZER_PROVIDER (resuelto en build_case_output)
      synthesis_timeout: str | None = "PT5M"   # = timedelta(minutes=5) actual
  ```
  - `output_schema`/`synthesis_template`/`synthesis_enabled`/`synthesis_uses_documents` **siguen
    version-level** (no se duplican aquí). `synthesizer_provider` se resuelve **por slug dentro de**
    `build_case_output`. *Abierto:* (a) si `synthesizer_provider` es un slug de `ConnectionAccount`
    (resuelto a creds+model) o un string `"provider:model"`; (b) los knobs de proyección
    (`projection_strict`, `projection_resolved_wins`) hoy **no son toggleables** (comportamiento fijo):
    se difieren hasta que exista un toggle real.
- **Dónde se usa:** `analysis_phases.output` (+ `build_case_output`).

### 6.12 `deliver` — canales y proyección de payload

- **Hoy:** emite **un** evento `case.output.ready` (`CASE_OUTPUT_READY`) vía `dispatch_case_event`,
  registra el artifact `delivery`, pasa el caso a `COMPLETED` y hace **muestreo QA fire-and-forget**
  (`_maybe_open_qa_audit`, determinista por `case_id` sobre `ActivationPolicy.qa_sample_rate`). **No lee
  `phase.config`** ni elige destinos: la selección ocurre **dentro de la activity**
  (`list_enabled_for_event(workflow_id, tenant_id, event_type)` filtra destinos enabled cuyo
  `subscribed_events` incluye el evento).
- **Propuesta:**
  ```python
  class DeliverConfig(PhaseConfig):
      channels: list[str] | None = None       # net-new (§5); allowlist de destinos; None ⇒ todos los enabled+suscritos (hoy)
      payload_projection: str | None = None   # net-new (§5); slug de proyección/plantilla; None ⇒ envelope estándar
      qa_sample_rate: float | None = None      # override opcional de ActivationPolicy.qa_sample_rate; None ⇒ usa la policy sellada
      dispatch_timeout: str | None = "PT60S"   # = 60s actual
      qa_audit_timeout: str | None = "PT30S"   # = 30s actual
  ```
  - `channels` y `payload_projection` se **resuelven dentro de** `dispatch_case_event` (nunca en el
    workflow). *Abierto:* (a) si `channels` **intersecta** o **reemplaza** el filtro `subscribed_events`
    (default `None` preserva "todos los enabled+suscritos"); (b) el mecanismo de `payload_projection`
    (plantilla vs allowlist de campos) no tiene precedente; (c) si `qa_sample_rate` debe ser overridable
    por fase o quedar solo en `ActivationPolicy`. Solo emite `CASE_OUTPUT_READY`; `case.failed` sale de
    los paths de fallo de `analyze`/`output`, fuera de esta fase.
- **Dónde se usa:** `analysis_phases.deliver`.

### 6.13 Policies existentes y en qué fases se configuran

| Política | Campos | Fases consumidoras |
|---|---|---|
| **ActivationPolicy** | `field_thresholds`, `on_low_confidence` (`clarify`/`review`), `blocking_rule_severities` | `confidence_gate` |
| | `stages` (L1/L2), `mode` (`mandatory`/`by_exception`), `sample_rate` | `human_review` |
| | `qa_sample_rate` | `deliver` (`analysis_phases`): muestreo a cola staff de QA tras COMPLETED (post-`deliver`) — no es una fase aparte |
| **CompletenessPolicy** | `required_types`, `auto_ready` | `await_documents` |
| **Tool `on_failure`** (no es policy formal) | `fail`/`continue`/`review` (default `review`) | `enrich` |

---

## 7. Dónde y cómo se guarda (almacenamiento)

| Qué | Dónde | Forma | Sellado |
|---|---|---|---|
| Config por fase | `pipeline_versions.phases[].config` | JSONB; tipado por `PhaseConfig` según `kind` | **Sí** (con la versión) |
| `output_schema` | `pipeline_versions.output_schema` | JSONB | Sí |
| `ActivationPolicy` (case-level) | `pipeline_versions.activation_policy` | JSONB tipado | Sí |
| `CompletenessPolicy` (case-level) | `pipeline_versions.completeness_policy` → **vestigial** (D-A): se pliega en `await_documents.config` | JSONB | a dropear en el squash |
| Tools (HTTP hoy; Python/JS = F5, sandbox in-cluster D-D) | `tool_definitions` (1:1 workflow) | `config` JSONB + `transport`; script inline o ref a object storage | Por slug desde la fase |
| Clasificador custom | `classifiers` (nuevo, tenant-scoped) | fila por slug; `config` JSONB | Por slug desde `classify_pages.config` |

**Recomendación de ubicación de políticas (D-A):** **híbrido** —
- `CompletenessPolicy` → **plegar** dentro de `await_documents.config` (único consumidor; queda
  coherente "cada fase posee su config"). La columna version-level
  `pipeline_versions.completeness_policy` (§2.1) queda **vestigial**: se deja de escribir y se dropea en
  el squash de migraciones de `feat/re-arch`; los runs se leen desde `phases[await_documents].config`.
- `ActivationPolicy` → **mantener** como objeto version-level (lo comparten `confidence_gate` +
  `human_review` + QA), pero el **editor lo muestra bajo cada fase consumidora**. Almacenamiento
  estable; solo cambia tipado + asociación de UX.

Como `feat/re-arch` está **sin commitear / pre-release**, los cambios de forma del JSON (plegar
completeness, re-grabar fixtures/golden) son **baratos ahora** — es la ventana correcta.

---

## 8. Dónde se usa en el pipeline (puntos de consumo)

1. **Entrada del handler:** cada handler parsea su `PhaseConfig` tipado al inicio (reemplaza los
   `phase.config.get(...)` dispersos). Punto único: `runtime.execute_pipeline` ya pasa `phase` al
   handler; el cambio es **parsear** en vez de leer claves sueltas.
2. **Resolución por slug en activities:** clasificador custom (`resolve_classifier`), tools
   (`tool_lookup`), scripts (runner aislado) → **fuera** del código del workflow (no determinista ⇒
   activity).
3. **Proyección de eventos:** `extract_fields` retiene metadatos según `emit`; `finalize`/`deliver`
   proyectan el payload de webhook/salida.
4. **Políticas:** `confidence_gate`, `human_review`, `await_documents` leen sus objetos sellados
   (hoy vía `state.scratch["policies"]`).
5. **Catálogo del editor:** `GET /v1/pipelines/phase-catalog` se **genera** desde los modelos
   `PhaseConfig` (JSON Schema) → formularios del editor sin divergencia.

---

## 9. Plan de implementación (cada fase deja la suite verde)

| Fase | Contenido | Gate / riesgo |
|---|---|---|
| **F0 · Fundación tipada** | Modelos `PhaseConfig` por `kind` (`application/pipelines/phase_configs.py`); validate-on-write en publish/import; refactor de handlers a parseo tipado; generar `phase_catalog` desde los modelos. **Sin cambio de comportamiento.** | **Golden `standard_v1` byte-idéntico** (validar **sin** re-serializar — §4.3); suite verde. ADR. |
| **F1 · Exponer knobs existentes** | `extract_text` (extractor+timeout+`per_type_overrides`), `classify_pages` fan-out (ya), `confidence_gate` thresholds, `await_documents` completeness + `advance`. Formularios del editor desde schema. | Tests por fase; re-grabar fixtures si cambia forma. |
| **F1b · Knobs de las 6 fases restantes** (D-J) | `assess`/`validate_extraction`/`await_clarification`/`analyze`/`output`/`deliver`: overrides de proveedor LLM, timeouts, `lambda` pins, `audience`, `channels` (defaults = comportamiento actual). | Bajo riesgo (defaults no-op); las **semánticas abiertas** (gating por `rule_severities`, `channels` intersect/replace, `payload_projection`, escalamiento de clarification) se cierran en implementación (notas *Abierto* §6.7–§6.12). |
| **F2 · Proyección de campos** | `extract_fields.emit` (proyección/filtro de `bounding_boxes`, confianza por bbox/campo, subset, `document_types`; los datos ya viven en `mapped_output`/`field_confidence`) + proyección al evento `DOCUMENT_PERSISTED` (nuevo) + `finalize.webhook_projection`. | Cambio de evento/webhook + **golden re-grabado**. |
| **F3 · Clasificador pluggable + custom tenant** | Registry `classifiers` + migración; `classify_pages.classifier` + activity `resolve_classifier`. | Migración up/down; test default vs custom. |
| **F4 · Quórum de aprobación** | `human_review` `approvals_required`/`distinct_approvers`/`approvers`/`timeout`; recuento de votos; integración matriz rol×acción. | ADR; tests de quórum/escala. |
| **F5 · Tools de script (Python/JS-TS)** *(stretch, seguridad alta)* | `ToolTransport.{PYTHON,JS}` + dispatch en connector + runner sandbox in-cluster (D-D) + almacenamiento de script. | **ADR + revisión de seguridad** dedicados. |

> **Orden respetando memoria:** no editar backend con flujos E2E vivos; squash de migraciones antes
> del merge de `feat/re-arch`; cada fase re-graba golden si toca forma JSON.

---

## 10. Riesgos

1. **Determinismo:** la config se sella; toda resolución dinámica va en activities. Editar = nueva
   versión (nunca muta runs sellados).
2. **Migraciones de JSON sellado:** plegar completeness, añadir `emit`, etc. cambian la forma de
   `phases`/policies → re-grabar fixtures (`circular_judicial.json`, `pedidos_multicanal.json`) y
   golden. Barato pre-release; caro post-release.
3. **Seguridad de scripts (F5):** ejecutar código no confiable es el mayor riesgo — aislamiento, sin
   red salvo allowlist, límites de recursos, sin acceso a secretos. Requiere ADR + revisión.
4. **Compat del `phase_catalog`:** el editor depende del schema; generarlo desde los modelos evita
   divergencia, pero cambios de schema deben versionarse para el editor.
5. **Quórum (F4):** introduce estado de votos en el run; cuidar idempotencia y reanudación de Temporal.
6. **Cambio de default al tipar (sellado):** dar a un campo tipado un default distinto del hardcoded de
   hoy (p. ej. `extractor`) cambiaría el comportamiento de versiones **ya selladas** sin esa clave al
   parsearlas. Mitigación: el default del modelo = default actual; cualquier cambio de arranque va como
   default de editor (pipelines nuevos) o backfill explícito. Aplica a **todo** `PhaseConfig`.

---

## 11. Decisiones (resueltas con Vic · 2026-06-14)

| # | Decisión | Resolución |
|---|---|---|
| **D-A** | Ubicación de políticas: ¿plegar en la fase o version-level? | **RESUELTO — Híbrido:** completeness → `await_documents.config` (columna version-level queda vestigial, se dropea en el squash); activation se mantiene version-level (compartida), expuesta por fase en el editor. |
| **D-B** | `extract_fields`: defaults de `include_ocr_confidence`/`include_bounding_boxes` | **RESUELTO — `false` (opt-in):** el dato ya se persiste en `mapped_output`; `emit` solo controla su exposición a eventos/webhook. |
| **D-C** | Clasificador custom: ¿registry dedicado (`classifiers`) o reusar tools/lambda? | **RESUELTO — Registry dedicado** tenant-scoped, referenciado por slug; resuelto en activity `resolve_classifier`. |
| **D-D** | Sustrato de scripts (F5): lambda-por-lenguaje vs contenedor sandbox vs servicio externo | **RESUELTO — Contenedor sandbox in-cluster** (gVisor/Firecracker), **no** lambda-por-lenguaje; ADR + revisión de seguridad dedicados. |
| **D-E** | Semántica de quórum: por etapa vs global, escalamiento por timeout | **RESUELTO — Por gate, N aprobadores distintos** de la audiencia permitida; etapas L1/L2 secuenciales; `timeout` opcional. |
| **D-F** | Ubicación del doc: `plans/proposals/` (plural) vs `plans/proposal/` (singular, canónico) | **RESUELTO:** movido a `plans/proposal/` junto a `pipeline.md`/`rule-tools.md`. |
| **D-G** | `enrich`: ¿renombrar el campo de binding `on_failure` → `on_error`? | **RESUELTO — Mantener `on_failure`** (idéntico al código vivo `enrich_phases.py`); renombrar obligaría a migrar JSON sellado sin beneficio. |
| **D-H** | Nombre del modelo de `HUMAN_REVIEW`: ¿`ApprovalConfig` o `HumanReviewConfig`? | **RESUELTO — `HumanReviewConfig`** (aplicado §6.6): el `kind` es `HUMAN_REVIEW` y el modelo cubre review **y** approval (principio 2: un modelo por `kind`). |

### Decisiones nuevas (resueltas con Vic · 2026-06-14)

| # | Decisión | Resolución |
|---|---|---|
| **D-I** | `human_review`/`approval`: comportamiento al expirar `timeout` y semántica de rechazo. | **RESUELTO — `timeout` ⇒ auto-rechazo (fail-safe)** al expirar (`None` = espera indefinida); **rechazo cuenta contra el quórum** (el gate falla cuando `N` aprobaciones se vuelven inalcanzables, no al primer reject). |
| **D-J** | Alcance de §6: ¿especificar ahora las 6 fases 🆕 restantes o diferirlas? | **RESUELTO — Especificar ahora** (§6.7–§6.12): `assess`, `validate_extraction`, `await_clarification`, `analyze`, `output`, `deliver`. |

---

## 12. Archivos estimados

**Backend:** `application/pipelines/phase_configs.py` *(nuevo, modelos tipados)* ·
`domain/services/phase_catalog.py` *(existente; generar desde modelos)* ·
`application/pipelines/{extraction_phases,pause_phases,enrich_phases,analysis_phases}.py`
*(parseo tipado)* · `domain/models/pipeline.py` *(opcional: `config` tipado por kind)* ·
`domain/models/policies.py` · `application/workflows/import_export/{importer,exporter}.py`
*(validate-on-write)* · `infrastructure/services/tools/connector.py` *(transportes Python/JS)* ·
`common/domain/enums/tools.py` *(`ToolTransport`)* · `classifiers` model+repo+migración *(F3)* ·
`human_review`/`pause_phases` *(quórum F4)* · ADRs (config tipada, scripts, quórum).

**Frontend:** editor de pipeline (`presentation/pipelines/pipeline-editor.tsx`) — formularios por fase
generados desde el `phase-catalog`; UI de tools (transporte + script); UI de policies bajo fase.

**Fixtures/tests:** `backend/fixtures/templates/*.json` + golden `test_standard_v1_regression.py`
re-grabados cuando cambie la forma.
