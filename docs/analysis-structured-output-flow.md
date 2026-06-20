# Salida estructurada enriquecida (`workflow.output`) — estado y plan

## Terminología (código real vs. tu descripción)
- `workflow.output` → en código es **`Workflow.output_schema`** (JSONB) + `synthesis_template` + `synthesis_enabled`.
- `analysis_rules` → **`WorkflowRule`** (+ `WorkflowRuleCompilation` = "compiladas").
- `analysis_results` → **`WorkflowRuleResult`** (`output`, `reasoning`, `citations`, `document_refs`, `status`, `kind`).
- salida final → **`WorkflowAnalysisRunSummary.output`** (validada contra `output_schema_snapshot`).

## Pipeline actual (existe y está cableado)
1. `DocumentSetProcessingWorkflow` (Temporal): OCR → `extraction` → `mapped_extraction` → `validation` por `WorkflowDocument`.
2. `WorkflowAnalysisRunWorkflow`: evalúa reglas compiladas (LLM por `kind`) → persiste `WorkflowRuleResult`.
3. `complete_run` → `VerdictAggregator` (capa **determinística**: verdict, signals, confidence, blocking_failures) → crea `WorkflowAnalysisRunSummary` con `narrative_status = PENDING` (si `synthesis_enabled`) o `SKIPPED`.
4. `SynthesisRunner` → `SynthesizerAgent`: LLM constreñido por `output_schema`, valida con `jsonschema`, persiste `summary.output`. Idempotente por `input_hash`; re-síntesis con `force`; `resynthesizer`, `regenerate_on_run_complete`, `webhook_dispatcher`.

## Lo que YA funciona
- ✅ La salida estructurada **se genera y persiste** (`summary.output`), validada contra el schema.
- ✅ Gating (`synthesis_enabled`), estados (`PENDING/RUNNING/COMPLETED/FAILED/SKIPPED`), idempotencia (`input_hash`), re-síntesis, webhooks.
- ✅ Schema por defecto (`DEFAULT_OUTPUT_SCHEMA`) cuando el workflow no define `output_schema`.

## Lo que FALTA / es débil (núcleo del objetivo)
1. **El synthesizer NO ve los documentos.** `synthesizer._build_user_prompt` recibe solo `verdict + blocking_failures + rule_results` (agrupados por kind). **No incluye `mapped_extraction`/`extraction`.** ⇒ La "salida enriquecida que combina datos extraídos + resultados" hoy razona solo sobre outputs de reglas, no sobre los campos del documento. Este es el gap principal.
2. **`input_hash` no incluye `mapped_extraction`** (`synthesis_runner.py:76`). Si cambia la extracción pero no los rule_results, la caché no se invalida y no se re-sintetiza.
3. **Sin proyección determinística.** Todo se delega al LLM. Campos que son copia directa (`@doctype.field`) deberían poblarse desde `mapped_extraction` sin LLM (más barato, sin alucinación).
4. **`output_schema` no se deriva de `document_types.fields`** — es manual o el default genérico.
5. **`StaticLLMRunner` es el default del agente.** Verificar que el worker en producción inyecta `build_synthesizer_agent()` (Agno) y no el stub.
6. **`document_refs`/`citations` no se proyectan** al `summary.output` para trazabilidad output ↔ documento fuente.

## Propuestas
- **A. Enriquecer `SynthesizerInput`** con `documents: [{document_id, doc_type, mapped_extraction, validation}]`. Cargar `WorkflowDocument`s en `SynthesisRunner.execute()` (repo filtrado por tenant) y añadirlos al user prompt. Cambios: `synthesizer.py`, `synthesis_runner.py`, `complete_run`/`summarizer`.
- **B. Incluir hash de `mapped_extraction`** en `compute_input_hash` para invalidación correcta.
- **C. Capa híbrida (recomendado):** resolución determinística primero — resolver `@doctype.field` directamente desde `mapped_extraction` para poblar el schema, y usar LLM solo para campos narrativos/derivados. Reduce costo y alucinación.
- **D. Builder de `output_schema`** derivado de `document_types.fields` como fallback en vez del default genérico.
- **E. Verificar wiring del agente real** en `bootstrap.py` / worker.
- **F. Proyectar citations/document_refs** dentro de `summary.output` (trazabilidad).

## Edge cases a considerar
- Reglas `FAILED/ERRORED/SKIPPED` y `scope.on_empty=SKIPPED`: cómo se representan/omiten en el output.
- `mapped_extraction = null` (mapeo falló) pero `extraction` OK → fallback a `extraction`.
- **Multi-documento:** ¿el output es por run (agregado) o por documento? `scope ALL_DOCUMENTS` vs per-doc. Definir si el schema es 1 objeto agregado o array por documento.
- **Tamaño de prompt:** muchos docs × `mapped_extraction` grande puede exceder el context window → truncado/selección por relevancia/document_refs.
- LLM devuelve JSON que **valida pero inventa datos** no anclados a `extraction` (riesgo real sin proyección determinística — propuesta C).
- Coherencia: el verdict es final; evitar que el LLM emita un verdict distinto dentro de `output`.
- Concurrencia/idempotencia: `force`, `regenerate_on_run_complete` y re-runs pisándose; respetar `input_hash`.
- Tenancy: filtrar `WorkflowDocument` por `tenant_id` al cargarlos.
- `output_schema` cambia entre runs: `output_schema_snapshot` lo cubre solo a nivel de run.
