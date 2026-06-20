# Golden de paridad — pipeline legacy `standard@v1`

Snapshot del comportamiento observable del motor legacy de extracción
(`run_extraction_pipeline`, `src/workflows/presentation/workflows/pipeline.py`,
**ya borrado**) grabado ANTES del cutover E1 (plan `product/plans/re-architecture/re-architecture.md`,
decisión D4 — cutover directo). Tras el cutover, estos fixtures son el lado
"esperado" de la suite de regresión del intérprete:
`tests/workflows/application/pipelines/test_standard_v1_regression.py`.

## Archivos

| Archivo | Contenido |
|---|---|
| `canned_results.json` | Resultados enlatados por activity: las 4 lambdas (`invoke_lambda` keyed por nombre lógico `extract_text` / `classify_pages` / `extract_fields` / `validate_extraction`), `read_classified_refs` y `persist_classified_documents`. Shapes realistas tomados de los fixtures reales de `vnext-tools/events/` (doble_ci.pdf: 2 cédulas, 1 por página) — incluyen `mapped_output` con bbox + confidences reales, un leaf `inferred`, un leaf nulo y un leaf de baja confianza (0.55). |
| `activity_sequence.json` | Secuencia ORDENADA de fingerprints de cada `workflow.execute_activity` que ejecutó el legacy con esos canned results. Fingerprints sin ids volátiles: las lambdas llevan `function_name` completo (incluye sufijo `STAGE`, `dev` en el entorno de test) + keys del payload; `mark_document_status` lleva las keys de `field_confidence` y cuáles son `source="bbox"`. |
| `final_state.json` | `DocumentProcessingOutput.model_dump(mode="json")` del run — output final campo a campo (`job_id`, `extract_text_source`, `classify_pages_source`, `extract_fields`, `validate_extraction`). |

## Cómo se grabó

Grabador: `test_record_golden.py` (borrado junto con el legacy en el cutover).
Ejecutó `run_extraction_pipeline` fuera de un worker Temporal monkeypatcheando
`temporalio.workflow` (`execute_activity`/`wait_condition`/`now`/`info`/
`logger`) con los canned results de arriba, en el entorno docker estándar
(`STAGE=dev`). Antes del borrado, `test_golden_fixtures__match_live_legacy_run`
verificó byte a byte que estos JSON describen fielmente al motor eliminado.

**Estos fixtures ya no se pueden regenerar** (el motor que describen no
existe): son la definición congelada de la paridad `standard@v1`. No editarlos
a mano. Si una evolución deliberada del intérprete cambia la orquestación,
la suite de regresión debe actualizarse de forma explícita y justificada —
nunca "re-grabando" el golden desde el propio intérprete sin revisión.

## Qué garantiza hoy

`test_standard_v1_regression.py` replays los `canned_results.json` a través de
`execute_pipeline` (el intérprete, único motor tras E1) con la receta REAL
`standard_extraction_phases()` de `src/workflows/domain/recipes.py` y asserta:

- misma secuencia ORDENADA de fingerprints que `activity_sequence.json`
  (39 entradas, campo a campo),
- output final == `final_state.json` campo a campo,
- fingerprints de `mark_document_status` idénticos — la paridad de
  `field_confidence` (keys pobladas + fuentes bbox) queda congelada.

## Evolución deliberada E4 — extract_fields por documento

El handler `extract_fields` pasó de UNA invocación Lambda batch (todo el set
vía el `source_uri` de classify_pages) a **una invocación por documento
clasificado** (diseño E4 §5): una activity nueva
`split_classified_documents` parte el output de classify_pages en un JSON S3
por documento (`{"documents": [doc]}` — refs, nunca payloads, por el límite
de 2 MiB) y la Lambda se invoca N veces concurrentes (`asyncio.gather`,
orden de schedule estable por `document_index`) con el MISMO contrato de
payload (`source_uri` + `job_id` + `inline_response`). Un documento que
falla ya no mata el run: se falla individualmente y el resto continúa.

Los fixtures se actualizaron en consecuencia (cambio justificado, revisado):

- `activity_sequence.json`: 37 → 39 entradas. La entrada única
  `["invoke_lambda", "vnext-tools-extract_fields-dev", ...]` se reemplazó por
  `["split_classified_documents", <classify_uri>]` + 2 invocaciones (una por
  cédula de doble_ci.pdf). El resto de la secuencia es idéntico.
- `canned_results.json`: `invoke_lambda.extract_fields` pasó de la respuesta
  batch a un dict keyed por el `source_uri` per-doc (los slices que devuelve
  el canned nuevo `split_classified_documents`). Cada respuesta per-doc se
  DERIVÓ partiendo la respuesta batch congelada por `document_index`, con
  `document_index: 0` en su entry — la Lambda real re-indexa un payload de
  1 doc desde 0 (enumerate en `_extract_documents_in_parallel`), y el handler
  re-mapea al índice original al fusionar. `process_time` per-doc = batch/2
  (mitades IEEE exactas: la suma reproduce el float original).
- `final_state.json`: **sin cambios**. La fusión per-doc reproduce byte a
  byte el artefacto batch (`{status, extractions, errors, metadata}`) — esa
  es exactamente la paridad que E4 debía conservar.

Script de derivación: una transformación pura de los JSON congelados (sin
AWS ni motor), aplicada una sola vez; ver docstring de
`test_standard_v1_regression.py`.

Nota de harness: el golden se grabó corriendo el motor directo, por lo que NO
contiene `load_pipeline_version` (activity del `PipelineInterpreterWorkflow.run`
que carga la receta sellada); la suite de regresión también corre
`execute_pipeline` directo, así que las secuencias se comparan 1:1 sin ajustes.

Los `function_name` grabados embeben el stage (`dev`): la suite solo es válida
en el entorno docker estándar de test (`STAGE=dev` en `backend/.env`).
