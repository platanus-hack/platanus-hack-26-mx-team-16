# 0002 — Pipeline propiedad del workflow (1:1) con entry points por sub-segmento

- **Estado:** accepted (decidido en revisión punto a punto; implementación pendiente)
- **Fecha:** 2026-06-11
- **Decisores:** Vic
- **Origen:** pregunta de Vic sobre `PipelineInterpreterWorkflow` («¿la receta no sería mejor
  relacionada y configurable directamente por workflow?»); detonante técnico: BUG 3 crítico del
  review adversarial de E6. Plan de implementación en `product/plans/pipeline/pipeline.md`.

## Contexto y problema

Desde E1, `Pipeline` es **tenant-scoped** (`tenant_id` + `slug` único por tenant,
`domain/models/pipeline.py`). Los workflows lo referencian vía `workflows.pipeline_id`
con *fallback* por slug al `standard-extraction` del tenant
(`application/pipelines/resolver.py`). La cardinalidad real resultante es
**N workflows → 1 pipeline compartido**: el onboarder siembra recetas canónicas por tenant
(`standard-extraction`, `field-re-extraction`) y los puntos de entrada especiales resuelven
recetas compartidas propias (`data-analysis` para `POST /v1/cases/{id}/data`,
`field-re-extraction` para re-extracción).

**Problema:** compartir por referencia convierte cada edición en un riesgo sistémico. El BUG 3
del review adversarial de E6 fue exactamente eso: importar un bundle avanzaba `current_version`
del pipeline compartido y **reescribía la receta de todos los workflows hermanos**. El fix de E6
(re-scope per-workflow al importar) ya empujaba el sistema hacia ownership por workflow. Además,
el editor visual de E6 presenta "el pipeline" como configuración *del workflow* — el modelo
mental del usuario ya es 1:1.

## Drivers

- **Aislamiento de edición**: editar el pipeline de un workflow JAMÁS puede afectar a otro.
- **Modelo mental simple**: lo que el usuario ve/edita en el detalle del workflow ES todo lo
  que ese workflow ejecuta.
- **Menos superficie**: eliminar la pregunta «¿qué receta corre esto?» (resolver con fallbacks,
  slugs canónicos, `_is_shared_pipeline`).
- **Reproducibilidad intacta**: conservar `PipelineVersion` inmutable + sellado por run
  (contrato de determinismo de Temporal).

## Opciones consideradas

1. **Mantener tenant-scoped compartido** con el re-scope-on-import de E6 como mitigación.
   Rechazada: el footgun sigue vivo para cualquier ruta de edición nueva.
2. **Varios pipelines nombrados por workflow** (main / reextract / data). Rechazada: más
   flexible pero reintroduce la resolución de recetas y ensucia la UI.
3. **1:1 estricto + sub-segmentos por entry point** (elegida).

## Decisión

1. **Ownership 1:1**: `pipelines.workflow_id` FK **NOT NULL + UNIQUE**. Muere la unicidad
   `(tenant_id, slug)`; el `slug` queda informativo (display + export/import), único por
   workflow. `tenant_id` se conserva como denormalización para authz. `PipelineVersion` no
   cambia.
2. **Copy-on-create**: al crear un workflow se clona la plantilla por defecto de `recipes.py`
   (según `workflow_type`) como pipeline propio v1. El onboarder deja de sembrar pipelines
   tenant-level.
3. **Entry points = sub-segmentos del único pipeline** (`select_phases(version, entry)`):
   `ingest` → todas las fases · `reextract` → **solo** la fase `extract` (paridad con la receta
   `field-re-extraction` actual) · `data` → desde la primera `analyze` en adelante. Workflow sin
   `analyze` que recibe `POST /v1/cases/{id}/data` ⇒ **409** error de configuración. Las recetas
   compartidas de sistema desaparecen.
4. **Reúso = «Duplicar workflow»** (deep-copy vía maquinaria export/import E6): copia doctypes +
   reglas + pipeline/policies + KB refs por slug; **excluye** documentos/casos, sources/
   destinations (secretos ⇒ `requiresConfiguration`) y miembros.
5. **API**: se retiran `POST/GET /v1/pipelines` tenant-level; reemplazo
   `GET|POST /v1/workflows/{id}/pipeline[/versions]` (+ `POST /v1/workflows/{id}/duplicate`).
   `phase-catalog` se mantiene. Repo: se eliminan `find_by_slug` y `list_by_tenant`; se añade
   `find_by_workflow`.
6. **UI**: el editor de fases (E6) se embebe como tab «Pipeline» en el detalle del workflow —
   **visible para todos los roles (read-only)**, editar/publicar gateado por la acción `manage`
   (matriz E5). La ruta standalone `/pipelines` se **borra** (sin redirect).
7. **Migración**: nueva migración forward con backfill (clonar compartidos → un clon por
   workflow; crear pipeline propio para workflows sin binding; borrar huérfanos), **squash antes
   del merge** de `feat/re-arch`.

## Consecuencias

- (+) El escenario del BUG 3 se vuelve **estructuralmente imposible**: no existen pipelines
  compartidos editables.
- (+) Resolver e importer se simplifican (sin fallbacks ni detección de compartidos).
- (+) El golden `standard_v1` pasa a vigilar la **plantilla** de copy-on-create (gate de paridad
  en la implementación).
- (−) Mejoras a una receta «estándar» ya no se propagan a workflows existentes: cada workflow
  evoluciona su copia (aceptado: es el comportamiento deseado — aislamiento sobre catálogo,
  coherente con D6 amendada para doc-types).
- (−) Migración + rewire de 5 consumidores (`re_extractor`, `m2m data`, `ingest`, `dispatcher`,
  `importer`) — acotado, dev-only, sin prod.
- Secuencia, pruebas y archivos: `product/plans/pipeline/pipeline.md` §5–§8.
