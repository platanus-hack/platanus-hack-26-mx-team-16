---
feature: data-model
type: spec
status: implemented
coverage: 95
audited: 2026-06-16
---

# Mini-spec · Sustantivo del caso por workflow (`case_noun`)

> **Estado:** decisión zanjada con Vic (2026-06-12) · implementación pendiente.
> **Decisión:** NO se renombra `WorkflowCase` (ni código, ni BD, ni wire público `/v1/cases`,
> ni eventos `case.*`). El nombre visible del caso pasa a ser **configurable por workflow**:
> el workflow «Pedidos» muestra "Pedidos", «Fondos Garantía» muestra "Expedientes", etc.
> `case` queda como término técnico estable; la palabra del usuario la pone su dominio.

## 1. Por qué

Ningún sustantivo global gana: contra los 5 casos cliente, «Caso» es neutro pero genérico,
«Expediente» sobrepromete en straight-through (`per_upload` de 1 doc), «Solicitud»/«Trámite»
solo encajan en algunos. La entidad correcta tiene nombre POR DOMINIO. Renombrar la entidad
global costaría un rename tipo `processing_job` + ruptura del wire público, para terminar
igual de genérico.

## 2. Modelo

Columna nueva en `workflows` (JSONB, nullable):

```json
case_noun: {
  "es": { "one": "Pedido",  "other": "Pedidos"  },
  "en": { "one": "Order",   "other": "Orders"   }
}
```

- `null` ⇒ la UI usa el default i18n actual («Caso/Casos», "Case/Cases").
- Plurales SIEMPRE explícitos (nada de pluralización automática).
- Validación: si viene, ambos locales con `one`+`other` no vacíos (≤30 chars).
- Capitalización: se guarda capitalizado como se mostrará (la UI no transforma).

## 3. Backend (alcance v1)

1. Migración: `ALTER TABLE workflows ADD COLUMN case_noun JSONB NULL`.
2. `Workflow` (domain) + builder + `WorkflowPresenter` ⇒ expone `caseNoun` (o null).
3. `PUT /v1/workflows/{id}` acepta `case_noun` (guard `manage`); validación pydantic.
4. **Plantillas** (`template_slug`): cada plantilla siembra su noun
   (pedidos→Pedido/Order, circulares→Oficio/Court order, fondos→Expediente/Dossier…).
5. **Duplicar workflow**: añadir `case_noun` a `_COPIED_CONFIG_FIELDS` (duplicate.py).
6. **Export/import bundle**: incluir `case_noun` en la config del workflow (no-secreto).
7. NO cambia: rutas, permisos (`operate`), eventos, M2M, webhooks, nombres de entidad.

## 4. Frontend (alcance v1)

Helper único:

```ts
// devuelve el sustantivo del workflow o el fallback i18n
caseNoun(workflow, locale, count): string
```

Superficies que lo usan (hoy hardcodean el namespace `Cases`/`WorkflowNav`):
- Ítem «Casos» del sidebar del workflow (grupo Operación).
- Título y empty state de la lista de casos.
- Breadcrumb del detalle (`…/{workflow}/Casos/{caso}`).
- Textos de selección/bulk («N seleccionados», diálogo de borrado).
- Tab labels del detalle del caso donde diga «Caso».

Los textos alrededor (verbos, descripciones) siguen en i18n; solo el sustantivo se inyecta.
Cuidado con género en es («{noun} eliminado/a»): v1 esquiva frases con concordancia o las
reescribe neutras («Se eliminó: {nombre}»).

## 5. Fuera de alcance v1

- UI de edición del noun (v1: solo plantilla + API; el editor visual llega después).
- Noun en emails/webhooks/exports de output (el wire se queda en `case`).
- Género gramatical explícito (si duele, se añade `gender: "m|f"` después).

## 6. Pruebas

- Presenter con/sin noun; validación de shape; duplicate copia; bundle round-trip.
- FE: helper con fallback + render del sidebar/lista con noun de plantilla.
