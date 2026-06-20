---
status: done
owner: Vic
created: 2026-06-17
completed: 2026-06-17
---

# ActivationPolicy folded into extraction_gate.config

> **HECHO 2026-06-17** (6 etapas, hard cutover). Backend 1432 tests verde (4 fallas
> pre-existentes ajenas: integration/llm + script_transport); FE tsc 0 + vitest 8/8.
> Tab "Políticas" disuelto; activación editada en el drawer de extraction_gate.
> Pendiente operativo: re-seed dev.

## Objetivo
Mover la `ActivationPolicy` de version-level (`pipeline_versions.activation_policy`) a la
config de **una fase** — `extraction_gate` — replicando el mecanismo del move de completeness.
Resultado: desaparece la última policy version-level; el tab "Políticas" se disuelve (o pasa
a ser el drawer de `extraction_gate`); un único patrón "todo en config de fase".

## Por qué funciona sin duplicar `field_thresholds`
Los consumidores **NO** leen la columna version-level — leen `scratch["policies"]["activation"]`,
que el intérprete **siembra**. Hoy lo siembra de `version.activation_policy`. Solo cambia
**de dónde** lo siembra. La policy sigue siendo **una sola** (sembrada una vez en scratch),
así que `field_thresholds` (lo leen `extraction_gate` Y los gate-items L1/L2 de `approval`)
sigue teniendo fuente única. La duplicación solo ocurriría con un *scatter* entre fases — que
NO hacemos.

## Consumidores (todos vía `scratch["policies"]["activation"]`)
- `extraction_gate` (pause_phases): `field_thresholds`, `on_low_confidence`.
- `_activation_policy` → `_approval_gate`/`_staged_review` (approval): `mode`,
  `blocking_rule_severities`, `sample_rate`, `stages`.
- `_stage_gate_items` (BUILD_STAGE_GATE_ITEMS): `field_thresholds` (L1/L2 reviewer items).
- `analysis_phases._qa_sample_rate` (analyze/deliver): `qa_sample_rate`.
- `derive_capabilities` (`capabilities._activation_dict`): QA ⇐ qa_sample_rate, HUMAN_REVIEW ⇐ stages.

## ⚠️ Catch estructural (no lo tenía completeness)
Completeness era **1:1** (solo `await_documents`). ActivationPolicy **no**: `approval` y
`deliver` la consumen y **pueden existir sin `extraction_gate`**. Si se aloja en
`extraction_gate` y esa fase está ausente, esos campos pierden hogar. Comportamiento natural:
seed = None ⇒ `ActivationPolicy()` por defecto (mode=mandatory, sin stages, sample_rate=0,
qa=0) = aprobación obligatoria simple, sin QA. Sano como default, pero significa: **para
configurar mode/stages/QA hace falta una fase `extraction_gate`**. Decisión D3 abajo.

## Mecanismo (espejo del move de completeness)
**Backend**
1. `phase_configs.py` · `ExtractionGateConfig`: añadir `activation: ActivationPolicy | None = None`
   (nested, reusa la validación pydantic de ActivationPolicy). La completeness usó campos
   planos; aquí conviene anidar el modelo entero.
2. `phase_configs.py` · `activation_dict_from_version(version)` (como `completeness_dict_from_version`):
   busca la fase `extraction_gate`, devuelve su `config.activation` (dict snake) o None;
   robusto a `PhaseSpec`/dict. (Fallback a `version.activation_policy` solo si NO hard-cutover.)
3. `pipeline_interpreter.py` seed (~L155): `"activation": activation_dict_from_version(version)`.
   **Consumidores no cambian.**
4. `capabilities.py` · `_activation_dict(version)`: leer de `extraction_gate.config.activation`
   (no de `version.activation_policy`).
5. `capability_macros.py` · `apply_capability`: hoy parchea `activation_policy` (QA →
   `qa_sample_rate`, HUMAN_REVIEW → `stages`). Tras el move debe **fusionar el patch dentro de
   `extraction_gate.config.activation`** del recipe — y si no hay fase `extraction_gate`,
   insertarla (los macros QA/HUMAN_REVIEW que parchean activation pasan a garantizar el gate).
   `MacroResult` deja de cargar `activation_policy` (va en `phases`).
6. **Purga version-level** `activation_policy` (mismos archivos que completeness): columna en el
   squash; ORM `common/database/models/pipeline.py`; dominio `workflows/domain/models/pipeline.py`;
   `LoadPipelineVersionOutput` (pipeline_run.py); repos `sql_pipeline.py`/`builders/pipeline.py`;
   `load_pipeline_version.py`; `exporter.py`/`importer.py` (`activationPolicy`); `pipeline_admin.py`
   (`CreatePipelineVersionRequest.activation_policy`, present, apply_capability publish);
   `creator.py` (`template.activation_policy`); `recipes.py` (`PipelineTemplate.activation_policy`
   + `STANDARD_CASE_ACTIVATION_POLICY` → mover dentro de `extraction_gate.config.activation` de
   `standard_case_phases()`).
7. `policies.py` · `validate_policies`/`normalize_policies`: quedan **sin uso** version-level
   (la activation se valida como parte de `ExtractionGateConfig` vía `validate_phase_configs`).
   Eliminarlas (como pasó con la mitad completeness). `ActivationPolicy` el modelo SE QUEDA.
8. (D3) Regla de presencia opcional en `validate_phase_configs`: si se configura
   `extraction_gate.config.activation` con stages/qa/sample, exigir coherencia; o aceptar
   defaults cuando `extraction_gate` ausente.

**Frontend**
9. `PoliciesPanel` (hoy solo-activation) → se monta en el **drawer de `extraction_gate`**
   (lee/escribe `phase.config.activation`), o el tab se queda pero apuntando a esa config (D2).
10. `pipelines.ts`/`pipeline-editor-store.ts`/`pipeline-editor.tsx`/`pipeline-diff.ts`: quitar
    `activationPolicy` version-level (tipos, store, payload, diff) — espejo de completeness.
11. `phase-config-form.tsx`: el editor de `extraction_gate` incluye el sub-editor de activation
    (reusar `PoliciesPanel` como sub-componente del drawer).

**Tests/golden/fixtures**: mismo patrón que el move de completeness (test_policies, test_capabilities,
test_capability_macros, test_creator, test_bundle_*, test_pipeline_admin_endpoints, test_ready,
fixtures pedidos/circular → activation dentro de extraction_gate.config).

## Mapa de archivos (≈ idéntico al move de completeness + macros)
Backend: phase_configs.py, pipeline_interpreter.py, capabilities.py, capability_macros.py,
policies.py, recipes.py, creator.py, sql_pipeline.py, builders/pipeline.py, load_pipeline_version.py,
exporter.py, importer.py, pipeline_admin.py, common/database/models/pipeline.py,
workflows/domain/models/pipeline.py, common/domain/entities/workflows/pipeline_run.py, squash
migration, fixtures/*.json. FE: pipelines.ts, pipeline-editor-store.ts, pipeline-editor.tsx,
pipeline-diff.ts(+test), policies-panel.tsx, phase-config-form.tsx, version-history.tsx.

## Secuencia (staged)
1. `ExtractionGateConfig.activation` + `activation_dict_from_version` + seed (additivo, con fallback).
2. capabilities + capability_macros (patch dentro de extraction_gate.config + auto-add gate).
3. recipes/template/fixtures → activation dentro de extraction_gate.config.
4. FE: PoliciesPanel al drawer + purga FE de activationPolicy version-level.
5. Hard cutover: drop columna + entidad/repos/presenter/endpoint/export-import + `validate/normalize_policies`.
6. Tests + golden + tsc + re-seed dev.

## Decisiones (cerradas con Vic 2026-06-17)
- **D1 · Host:** `extraction_gate` (la entrada del flujo de revisión).
- **D2 · Tab "Políticas":** se **DISUELVE** — el `PoliciesPanel` se monta en el drawer de
  `extraction_gate` (`phase-config-form`); el tab `?tab=policies` se elimina del editor.
- **D3 · Gate ausente:** **auto-add del gate en los macros** — los macros QA/HUMAN_REVIEW que
  parchean activation garantizan que exista una fase `extraction_gate` (la insertan si falta).
  Sin gate ⇒ activation None ⇒ `ActivationPolicy()` por defecto (sin regla de error).
- **D4 · Cutover:** **hard cutover** — drop de la columna `activation_policy` + entidad/repos/
  presenter/endpoint/export-import + `validate/normalize_policies`. Re-seed dev. Igual que completeness.

## Pendiente: pasar a implementación por etapas (la secuencia de arriba) cuando Vic dé el OK.
