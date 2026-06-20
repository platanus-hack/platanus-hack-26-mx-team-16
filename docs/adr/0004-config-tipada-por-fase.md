# 0004 — Config tipada por fase del pipeline (`PhaseConfig` por `kind`)

- **Estado:** accepted (decidido con Vic; decisiones D-A…D-J zanjadas 2026-06-14)
- **Fecha:** 2026-06-14
- **Decisores:** Vic
- **Origen:** `product/plans/pipeline/phases-config.md`. Prerequisitos: ADR 0002 (pipeline 1:1
  sellado e inmutable) y ADR 0003 (capacidades derivadas del pipeline). Detona: cada
  handler de fase lee su `config` ad-hoc con `phase.config.get("clave", default)`
  disperso; el `phase_catalog` que consume el editor mantiene una tabla declarativa
  **aparte** que puede driftear de lo que el handler realmente lee.

## Contexto y problema

`PhaseSpec.config` es un `dict` libre sellado dentro de `pipeline_versions.phases`
(JSONB, inmutable con la versión — ADR 0002). Tres consumidores leen ese dict de forma
**independiente** y por tanto **driftean**:

1. **Handlers** (`extraction_phases`, `pause_phases`, `gate_phases`, …): `config.get(...)`
   con defaults hardcodeados, repartidos por todo el código.
2. **Validación al publicar/importar** (`pipeline_admin._validate_recipe`, `importer`):
   solo validaba `PhaseSpec` + scope + extractor; una clave de config con typo o un tipo
   inválido pasaba el publish y **explotaba en runtime** (o se ignoraba en silencio).
3. **`phase_catalog`**: una tabla declarativa hecha a mano por `kind`. Ya había drift real
   — p. ej. el catálogo atribuía `assignee_mode`/`audience`/`payload` a `await_documents`
   (que no lee config) cuando esas claves son de `await_clarification`/`human_review`.

## Drivers

- **Una sola fuente de verdad del schema de config**, no tres copias que driftean.
- **Validate-on-write:** una config inválida debe ser un **422 al publicar**, no un fallo
  de Temporal en producción.
- **Determinismo intacto (ADR 0002):** la config se sigue sellando como JSON; tipar no
  puede cambiar la forma sellada ni los bytes de un run ya grabado (golden byte-idéntico).
- **Aditividad:** F0 no cambia comportamiento; solo introduce la estructura sobre la que
  F1–F5 cuelgan los knobs nuevos.

## Opciones consideradas

- **A — Status quo (`dict` + `.get()` disperso + tabla de catálogo a mano).** Drift
  perpetuo entre handler, validación y editor. Rechazada.
- **B — Tipar `PhaseSpec.config` como unión discriminada por `kind`.** Pydantic
  materializaría defaults al re-serializar ⇒ rompería el golden byte-idéntico y obligaría
  a re-grabar fixtures sin beneficio. Rechazada.
- **C — Un modelo `PhaseConfig` por `kind`, pero `PhaseSpec.config` sigue siendo `dict`.**
  Los modelos **validan** y **tipan la lectura**; el publish persiste el JSON entrante tal
  cual (sin re-serializar ⇒ sin materializar defaults). El catálogo se **genera** de los
  modelos. **Elegida.**

## Decisión

1. **Un modelo Pydantic por `kind`** en `domain/models/phase_configs.py` (junto a
   `policies.py`/`pipeline.py`: dominio puro, sin framework ni infra — así
   `domain/services/phase_catalog.py` puede derivar de ellos sin violar la regla de
   dependencias). Base común `PhaseConfig` con `extra="forbid"` (rechaza claves
   desconocidas) y `populate_by_name=True` (acepta nombre y alias, p. ej. `lambda_` ↔
   `"lambda"`). Registro `PHASE_CONFIG_MODELS: {kind.value → modelo}` cubre las **15** fases
   (las sin knobs hoy mapean a un modelo vacío ⇒ `extra=forbid` igual rechaza basura).
2. **Defaults == comportamiento de hoy.** Cada campo usa el default *efectivo* cuando la
   clave está ausente (lo que devolvía `config.get(clave, default)`), de modo que una
   versión ya sellada **sin** la clave reproduce su comportamiento al parsearse. (Riesgo
   §10.6 del plan: cambiar un default rompería runs sellados — el arranque distinto va como
   default de editor o backfill, nunca como default del modelo.)
3. **`PhaseSpec.config` sigue siendo `dict`.** La validación **NO re-serializa** ni muta
   `config`; el publish persiste el JSON entrante tal cual (condición del golden
   byte-idéntico). `model_dump(by_alias=True, exclude_unset=True)` solo se usaría al
   re-generar desde el modelo.
4. **Validate-on-write** (`validate_phase_configs`) en publish (`pipeline.invalid_phase_config`,
   tras el check de `extractor` para preservar el contrato `pipeline.invalid_extractor`) e
   import (lanza `InvalidPhaseConfigError(ValueError)` ⇒ el importer lo reporta como el
   resto).
5. **Validate-on-read:** los handlers parsean su modelo (`Model.model_validate(phase.config
   or {})`) en vez de `.get()` sueltos. **Excepción `enrich`:** conserva su validación
   explícita de `on_failure` porque levanta un `ApplicationError` no-retryable
   (`ENRICH_CONFIG_ERROR_TYPE`) que un `Literal` de Pydantic preemptaría con otro error;
   su modelo tipado sigue alimentando publish + catálogo.
6. **`phase_catalog` generado de los modelos** por introspección de `model_fields` →
   `{campo(alias): {type, enum?, default?}}`. Misma forma de wire que el editor ya consumía;
   el enum de `extractor` sale en vivo de `DocumentExtractorType`. Se corrige el drift del
   catálogo de paso.

### Gotcha clave (sellado en el código)

`BaseEnum` **no** es subclase de `str`. Hoy `extract_text` pasa el **string crudo**
(`config.get("extractor", DEFAULT_EXTRACTOR)`) al payload de la Lambda. El handler tipado
debe pasar `cfg.extractor.value` (string), no el miembro enum, o el fingerprint del golden
cambiaría. Igual para cualquier valor enum que viaje a una activity.

## Consecuencias

- **+** Schema único: editor, validación y handlers no pueden driftear.
- **+** Errores de config se atrapan al publicar (422), no en runtime.
- **+** Base para F1–F5: cada knob nuevo es un campo en el modelo del `kind`, expuesto
  automáticamente en el catálogo/editor.
- **−** `extra="forbid"` en validate-on-read asume que toda config sellada pasó por publish;
  válido en pre-release (sin runs en producción). Un backfill futuro debe respetarlo.
- **−** Cambiar el default de un campo tipado es semánticamente equivalente a cambiar el
  comportamiento de versiones selladas sin esa clave — debe tratarse como tal.

## Verificación

Golden `standard_v1` byte-idéntico (extracción) + suite de pipelines/import-export/catálogo
verde; tests nuevos en `tests/workflows/domain/models/test_phase_configs.py` (defaults,
coerción de enums, `extra=forbid`, `validate_phase_configs`) y el 422
`pipeline.invalid_phase_config` en `test_pipeline_admin_endpoints.py`.
