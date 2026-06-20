---
feature: tools
type: plan
status: pending
coverage: 20
audited: 2026-06-16
backlog: true
---

# Mini-spec · Referencias a tools en reglas — `#tool.<slug>.path`

> **Estado:** diseño zanjado con Vic (2026-06-11) · **implementación pendiente** (sin compromiso de fecha).
> Extiende el lenguaje de tokens de reglas; no toca el motor de pipelines (ADR 0002 ya implementado).
> **Actualización 2026-06-12 (decisión #0, IMPLEMENTADA):** las tools dejan de ser org-level.

## 1. Decisiones zanjadas

| # | Decisión | Resolución |
|---|---|---|
| 0 | **Scoping (2026-06-12)** | **Workflow-scoped 1:1** (antes org-level). `tool_definitions.workflow_id` NOT NULL + unique `(workflow_id, name)`; la credencial sigue en la `ConnectionAccount` org (patrón Conexiones). Endpoints bajo `/v1/workflows/{id}/tools` (guard `manage`/`view`); UI en el sidebar del workflow (grupo Configuración); `/tools` global **eliminado sin redirect** (mismo trato que `/pipelines`). Reuso = «Duplicar workflow» copia las tools (paso 4 del duplicador, fuera del bundle). `tool_lookup` resuelve por `(name, workflow_id, tenant_id)`. **Ya implementado** (migración `c9d0e1f2a3b4`). |
| 1 | Prefijo para tools | **`#`** (no `@`): `@` mira **adentro** (datos del expediente), `#` mira **afuera** (conocimiento y servicios). |
| 2 | Gramática del namespace `#` | **`#kb.<slug>`** (KB) y **`#tool.<slug>.path`** (tools) canónicos; `#<slug>` **plano queda como alias legacy** de `#kb.<slug>` (el compilador normaliza; cero ruptura de reglas/bundles existentes). |
| 3 | Slugs reservados en `#` | `kb` y `tool` (guard al crear KBs — espejo del guard de `rule` en `@`). |
| 4 | Semántica de resolución | **Lazy**: el tool corre **solo si una regla activa lo referencia** (no como `enrich`, que corre siempre en su fase). |
| 5 | Mecánica | Reusa `tool_lookup` (HMAC Svix, allowlist, jsonschema in/out, on_failure) — cero maquinaria HTTP nueva. |
| 6 | Provenance | La respuesta se persiste como doc `TOOL` (igual que enrich) ⇒ auditoría/citations gratis. La **referencia** lee la respuesta; el doc es el snapshot. |
| 7 | Dedup | Mismo tool+args dentro de un run de análisis ⇒ **una sola llamada** (cache por run). |
| 8 | Args | Los define la **config del tool/conexión** (templates `@slug.path`/`{{tokens}}`, como enrich hoy: `args: {"q": "@oficio.numero"}`). Sin args inline en el token (v1). |
| 9 | `when` | **No** puede usar `#tool.` en v1 (un predicado que dispara HTTP es sorpresa; `when` se evalúa sobre datos del caso). |
| 10 | Proyecciones (case-output) | `#tool.` **no** entra a `project_schema` en v1 — solo reglas. (El output ya puede leer el doc TOOL vía x-source si hace falta.) |

## 2. Gramática resultante

| Token | Ámbito | Resolución |
|---|---|---|
| `@slug.path` | dato del expediente (doc real/virtual/TOOL archivado) | determinista, existente |
| `@rule.<slug>` | resultado de otra regla (`rule` reservado) | existente |
| `#kb.<slug>` | knowledge base (alias legacy: `#<slug>` plano) | contexto LLM, existente |
| `#tool.<slug>.path` | **respuesta de una tool HTTP firmada** | **NUEVO** · lazy, on-demand |
| `{{system_var}}` | runtime (`{{now}}`, …) | existente |

Mnemónico: **`@` adentro · `#` afuera · `{{}}` runtime**.

Ejemplo: regla *«NIT activo en DIAN»* → `#tool.dian.estado == "ACTIVO"` con el tool `dian` configurado
con `args: {"nit": "@proveedor.nit"}`.

## 2.bis Argumentos — campos extraídos como inputs del tool

Lo que se referencia con `#tool.<slug>` **no es la conexión cruda sino un *tool binding***: una
invocación configurada (conexión + endpoint + mapeo de args). El mecanismo de render **ya existe** en
`tool_lookup` (lo usa enrich): los args son templates con la misma sintaxis de las reglas.

```jsonc
// tool binding "dian" (config del workflow)
{
  "slug": "dian",
  "connection": "dian-api",
  "url": "https://api.example.gov.co/rut/{nit}",   // {placeholders} en URL
  "args": { "nit": "@proveedor.nit" },             // ← campo EXTRAÍDO del doc 'proveedor'
  "schema_out": { "...": "..." },
  "on_failure": "continue"
}
```

Flujo del dato: `extract` llena `mapped_extraction` del doc `proveedor` → `analyze` ve la dep
`#tool.dian` → `tool_lookup` renderiza `@proveedor.nit` **contra los documentos del caso** (mismo
resolutor de las reglas; también acepta `{{tokens}}`) → llamada firmada → la regla lee
`#tool.dian.estado`.

- **Mismo servicio, otros args** ⇒ otro binding con otro slug (`dian_cliente` con
  `args: {"nit": "@cliente.nit"}` → `#tool.dian_cliente.estado`). Args inline en el token
  (`#tool.dian(nit=@cliente.nit)`) quedan **fuera de v1** — gramática y compilador mucho más simples.
- **Arg requerido null** (la extracción no encontró el campo) ⇒ se trata como fallo del tool
  (aplica `on_failure`; no se hace la llamada con datos incompletos).
- **Arg ambiguo** (varios docs del mismo tipo ⇒ el path resuelve a lista) ⇒ `tool_args_ambiguous`
  (error de config del binding), salvo que el `schema_in` del tool acepte array.
  *(Ambos defaults propuestos — validar al implementar.)*

## 3. Mecánica (flujo)

1. **Compilación**: el compilador de reglas extrae dependencias `#tool.<slug>` (nuevo extractor hermano
   de `_DOC_REF_RE` — NO se toca el regex de doc-refs). Guard: slug de tool inexistente en las
   conexiones del workflow ⇒ error de compilación (igual que doc-type slug inválido).
2. **Análisis**: antes de evaluar, `analyze` resuelve el cierre de deps tool de las reglas **activas**
   (las `when=false` no disparan nada): por cada dep, activity `tool_lookup` (firma, allowlist,
   jsonschema, timeout) → respuesta validada → snapshot doc `TOOL` → cache del run.
3. **Evaluación**: el token resuelve contra la respuesta cacheada (`.path` con la misma semántica de
   paths que `@`).
4. **Fallo del tool**: hereda el `on_failure` de la config del tool —
   `fail` ⇒ la regla evalúa a **FAIL** con `error.code="tool_unavailable"` ·
   `continue` ⇒ el token resuelve **null + warning** (la regla decide) ·
   `review` ⇒ HumanTask sin pausar (como enrich) + token null.

## 4. Guards y compat

- Crear KB con slug `kb` o `tool` ⇒ 422 (espejo del guard de `rule`).
- `#<slug>` plano se normaliza a `#kb.<slug>` al compilar; export/import de bundles preserva el texto
  original de la regla (la normalización es interna, no reescribe prompts).
- Ojo `_DOC_REF_RE`: el fix E5 de frontera izquierda (emails/@handles) aplica igual al extractor de
  `#` (no matchear `foo#bar`).

## 5. Pruebas (cuando se implemente)

- Compilador: extracción de deps `#tool.` · alias plano→`#kb.` · slug reservado · tool inexistente ⇒
  error de compilación · email/#hash en prompt NO matchea (frontera).
- Análisis: lazy (regla `when=false` ⇒ cero llamadas) · dedup (2 reglas, mismo tool ⇒ 1 llamada) ·
  on_failure fail/continue/review · snapshot TOOL persistido con provenance.
- E2E: regla con `#tool.` contra sink firmado local (patrón de los sinks E2E existentes).

## 6. Archivos (estimado)

`infrastructure/services/rules/kinds/_shared/refs.py` (extractor nuevo) · compilador/validador de
reglas (deps + guards) · `analyze` (resolución del cierre de deps, reusa
`presentation/workflows/activities/tool_lookup.py`) · guard de slug en creación de KB ·
`product/plans/re-architecture/mockups/arquitectura.html` §8 (ya actualizado con la sintaxis propuesta).
