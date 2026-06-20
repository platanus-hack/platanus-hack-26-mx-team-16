---
feature: extraction
type: spec
status: implemented
coverage: 90
audited: 2026-06-16
---

# Lambda `extract_fields` — Nuevo formato de salida (repo `vnext-tools`)

> Este spec cubre **exclusivamente** los cambios en la lambda `extract_fields` del repo `vnext-tools`.
> Para el plan del lado consumidor (workflow Temporal, entidades, persistencia, API, frontend) ver `specs/doxiq_enriched_extraction.md`.

## 1. Contexto

La lambda `extract_fields` recibe un documento clasificado (`document_type` + `pages[]` con bloques OCR y sus bboxes) y usa un LLM para producir valores estructurados conforme al JSON Schema definido en `document_type.fields`.

Hoy emite `extraction.extracted_values` como un dict plano `{campo: valor}` (strings). Esto **pierde el vínculo con las coordenadas OCR**, impidiendo que el backend resuelva bounding boxes para pintar overlays en el PDF viewer.

## 2. Objetivos del cambio

1. **Renombrar** `extracted_values` → `output`.
2. **Añadir** una nueva clave hermana `mapped_output` que mantiene la misma estructura del árbol, pero con cada hoja escalar envuelta en un objeto enriquecido `{value, source_text, page_number, bbox, inferred}`. El `bbox` se resuelve en la lambda (post-procesado sobre los bloques OCR recibidos como input). Ver §6 para semántica y §13 para el algoritmo.
3. Actualizar la lambda vecina `validate_extraction` para que lea `output[field]` en lugar de `extracted_values[field]`.
4. Actualizar fixtures en `events/*.json` y tests.

## 3. Shape actual (producción)

```json
{
  "status": "success",
  "extraction": {
    "document_type": { /* ... */ },
    "extracted_values": {
      "nombres": "SEBASTIAN",
      "apellidos": "FLORES LLUSCO",
      "numero_cedula": "0352652-LA",
      "fecha_nacimiento": "22/02/1947",
      "sexo": null
    },
    "document_index": 0
  },
  "metadata": { /* ... */ }
}
```

## 4. Shape nuevo

La lambda devuelve **dos estructuras en paralelo** bajo `extraction`:

| Clave | Propósito |
|-------|-----------|
| `output` | Dict con la misma forma del árbol declarado en `document_type.fields`, con **valores planos** en las hojas. Es el consumo principal para `validate_extraction` y para cualquier lógica de negocio que solo necesite el valor final. |
| `mapped_output` | Misma estructura del árbol, pero cada **hoja escalar** es un objeto enriquecido `{value, source_text, page_number, bbox, inferred}` con el bbox OCR ya resuelto por la lambda. El backend solo consume — no calcula. |

**Invariante**: `output` y `mapped_output` deben ser consistentes. Para cada path `P` que llega a una hoja escalar:
`output[P] == mapped_output[P].value`

### 4.1 Ejemplo plano (schema actual del ejemplo de cédula)

```json
{
  "status": "success",
  "extraction": {
    "document_type": { /* ... */ },

    "output": {
      "nombres": "SEBASTIAN",
      "apellidos": "FLORES LLUSCO",
      "numero_cedula": "0352652-LA",
      "fecha_nacimiento": "4 de Febrero de 1947",
      "sexo": null
    },

    "mapped_output": {
      "nombres": {
        "value": "SEBASTIAN",
        "source_text": "SEBASTIAN",
        "page_number": 1,
        "bbox": [{
          "page_number": 1,
          "polygon": [{"x":0.12,"y":0.40},{"x":0.28,"y":0.40},{"x":0.28,"y":0.44},{"x":0.12,"y":0.44}],
          "matched_text": "SEBASTIAN",
          "confidence": 0.95
        }],
        "inferred": false
      },
      "apellidos": {
        "value": "FLORES LLUSCO",
        "source_text": "FLORES LLUSCO",
        "page_number": 1,
        "bbox": [{
          "page_number": 1,
          "polygon": [{"x":0.12,"y":0.45},{"x":0.38,"y":0.45},{"x":0.38,"y":0.49},{"x":0.12,"y":0.49}],
          "matched_text": "FLORES LLUSCO",
          "confidence": 0.93
        }],
        "inferred": false
      },
      "numero_cedula": {
        "value": "0352652-LA",
        "source_text": "0352652-LA",
        "page_number": 1,
        "bbox": [{
          "page_number": 1,
          "polygon": [{"x":0.55,"y":0.20},{"x":0.75,"y":0.20},{"x":0.75,"y":0.24},{"x":0.55,"y":0.24}],
          "matched_text": "0352652-LA",
          "confidence": 0.97
        }],
        "inferred": false
      },
      "fecha_nacimiento": {
        "value": "4 de Febrero de 1947",
        "source_text": "22/02/1947",
        "page_number": 1,
        "bbox": [{
          "page_number": 1,
          "polygon": [{"x":0.30,"y":0.55},{"x":0.48,"y":0.55},{"x":0.48,"y":0.59},{"x":0.30,"y":0.59}],
          "matched_text": "22/02/1947",
          "confidence": 0.89
        }],
        "inferred": true
      },
      "sexo": {
        "value": null,
        "source_text": null,
        "page_number": null,
        "bbox": [],
        "inferred": false
      }
    },

    "document_index": 0
  },
  "metadata": { /* ... */ }
}
```

## 5. Reglas de anidación

`mapped_output` refleja la misma forma que `output`. Solo las **hojas escalares** (string / number / boolean / null) se envuelven.

> **Nota**: los ejemplos §5.1–5.3 muestran las hojas abreviadas como `{value, source_text, page_number}` por legibilidad. El shape real es el enriquecido `{value, source_text, page_number, bbox, inferred}` — ver §4.1 para un ejemplo completo y §6 para semántica de cada campo.

| Caso | Comportamiento |
|------|----------------|
| Hoja escalar | Se envuelve en `{value, source_text, page_number}`. |
| Objeto anidado | Se mantiene el nombre de propiedad y se recurre. **No** se envuelve el objeto entero. |
| Array de objetos | Mismo índice en ambas estructuras. Cada elemento-objeto se recurre. El array en sí **no** se envuelve. |
| Array de primitivos | Mismo índice en ambas estructuras. Cada elemento-primitivo se envuelve como hoja. |
| Array vacío | `[]` en ambas estructuras. |
| Rama `null` | Si una rama entera se resuelve a `null` (p.ej. `direccion: null`), ambas estructuras llevan `null` en esa posición. **No** se envuelve. |
| Valor escalar ausente | `value: null`, `source_text: null`, `page_number: null`. |

### 5.1 Ejemplo con objeto anidado

Schema:
```json
{
  "type": "object",
  "properties": {
    "titular": {
      "type": "object",
      "properties": {
        "nombres":   { "type": "string" },
        "apellidos": { "type": "string" }
      }
    },
    "direccion": {
      "type": "object",
      "properties": {
        "ciudad":        { "type": "string" },
        "codigo_postal": { "type": "string" }
      }
    }
  }
}
```

Output:
```json
{
  "output": {
    "titular":   { "nombres": "SEBASTIAN", "apellidos": "FLORES LLUSCO" },
    "direccion": { "ciudad": "La Paz",     "codigo_postal": null }
  },
  "mapped_output": {
    "titular": {
      "nombres":   { "value": "SEBASTIAN",     "source_text": "SEBASTIAN",     "page_number": 1 },
      "apellidos": { "value": "FLORES LLUSCO", "source_text": "FLORES LLUSCO", "page_number": 1 }
    },
    "direccion": {
      "ciudad":        { "value": "La Paz", "source_text": "La Paz", "page_number": 2 },
      "codigo_postal": { "value": null,     "source_text": null,     "page_number": null }
    }
  }
}
```

### 5.2 Ejemplo con array de objetos

Schema:
```json
{
  "type": "object",
  "properties": {
    "beneficiarios": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "nombre":     { "type": "string" },
          "porcentaje": { "type": "number" }
        }
      }
    }
  }
}
```

Output:
```json
{
  "output": {
    "beneficiarios": [
      { "nombre": "LAURA JIMENEZ",    "porcentaje": 60 },
      { "nombre": "FILOMENA CONDORI", "porcentaje": 40 }
    ]
  },
  "mapped_output": {
    "beneficiarios": [
      {
        "nombre":     { "value": "LAURA JIMENEZ", "source_text": "LAURA JIMENEZ", "page_number": 1 },
        "porcentaje": { "value": 60,              "source_text": "60%",           "page_number": 1 }
      },
      {
        "nombre":     { "value": "FILOMENA CONDORI", "source_text": "FILOMENA CONDORI", "page_number": 2 },
        "porcentaje": { "value": 40,                 "source_text": "40%",              "page_number": 2 }
      }
    ]
  }
}
```

### 5.3 Ejemplo con array de primitivos

Schema:
```json
{
  "type": "object",
  "properties": {
    "telefonos": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

Output:
```json
{
  "output": {
    "telefonos": ["70012345", "22480000"]
  },
  "mapped_output": {
    "telefonos": [
      { "value": "70012345", "source_text": "70012345",        "page_number": 1 },
      { "value": "22480000", "source_text": "Tel.: 2248-0000", "page_number": 1 }
    ]
  }
}
```

## 6. Semántica de los campos de la hoja

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `value` | `string \| number \| boolean \| null` | sí | Valor final ya normalizado/casteado al tipo declarado en el JSON Schema. Idéntico al valor correspondiente en `output`. |
| `source_text` | `string \| null` | sí | Fragmento **textual verbatim** copiado del OCR del que se derivó `value`. Debe existir como sub-cadena de `page.text` en la página indicada. `null` si el valor se dedujo sin anclaje textual (o si `value` es `null`). |
| `page_number` | `int \| null` | sí | Número de página 1-based (el mismo valor de `pages[].page_number` recibido como input) donde aparece `source_text`. `null` si `source_text` es `null`. |
| `bbox` | `list[BBoxHit]` | sí | Lista de bboxes resueltos por el post-procesado (§13) contra los bloques OCR. **Siempre es una lista** (nunca `null`): `[]` si no hay match; típicamente un solo elemento; múltiples solo si el span cruza páginas (caso raro). Shape de `BBoxHit` en §6.2. |
| `inferred` | `boolean` | sí | `true` si la lambda normalizó/reformateó el valor respecto al OCR. Derivado: `inferred = value is not None AND (source_text is None OR source_text.strip() != str(value).strip())`. |

### 6.1 Reglas para `source_text`

- **Debe ser copia literal** del OCR: sin reformateo, sin normalización de mayúsculas, sin quitar signos. El post-procesado lo usa como clave de búsqueda en `page.text`.
- Preferir el span **más corto y único** que contiene la información. Para "LAURA VERONICA" (dos tokens OCR), devolver el string completo `"LAURA VERONICA"`, no cada token por separado.
- Si el valor cubre texto no contiguo o cruza páginas, devolver el fragmento principal en la página principal. El edge case cross-page se maneja emitiendo múltiples entradas en `bbox[]`.
- Antes de emitir, la lambda valida que `source_text` esté contenido en `page.text` de `page_number`. Si no lo está, log warning y emitir `source_text: null, page_number: null, bbox: [], inferred: (según regla)` (el LLM se inventó el span).

### 6.2 Shape de `BBoxHit`

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `page_number` | `int` | sí | Página 1-based donde aparece el bbox. Debe existir en `pages[].page_number` del input. |
| `polygon` | `list[{x: float, y: float}]` (len = 4) | sí | Cuatro puntos normalizados 0..1, formando el polígono envolvente (convex hull de los tokens OCR matcheados). |
| `matched_text` | `string` | sí | Fragmento efectivamente localizado en `page.text`. Puede diferir de `source_text` si hubo matching fuzzy. |
| `confidence` | `float \| null` | sí | Promedio de `block.confidence` de los tokens OCR matcheados. `null` si los tokens no traen confidence. |

## 7. Impacto en la lambda `validate_extraction`

`validate_extraction` consume la salida de `extract_fields`. Hoy lee `extracted_values[field]` como string plano para inyectarlo en el template `{{field}}` del prompt de cada regla.

**Cambio requerido**: leer `output[field]` en lugar de `extracted_values[field]`. Es puramente un rename; el shape plano se preserva. **No** debe leer `mapped_output`.

## 8. Fixtures a actualizar

Todos en `events/`:

- `3_extract_fields_response.json` → nuevo shape (`output` + `mapped_output`).
- `4_validate_extraction.json` (input de la lambda siguiente) → refleja el rename a `output`.
- `4_validate_extraction_response.json` → `value_analyzed` sigue siendo el `value` final normalizado (no `source_text`).

## 9. Compatibilidad y rollout

- `output` plano cubre el 100% del contrato viejo (solo cambia el nombre de la clave), así que los consumidores que solo necesitan valores no pierden nada.
- El backend consumidor acepta tanto `extracted_values` como `output` durante la ventana de rollout mediante un shim on-read; `mapped_output` es opcional (si no existe, boxes quedan vacíos).
- **Orden sugerido**: primero desplegar esta lambda, después desplegar el backend que empieza a consumir `mapped_output`.

## 10. Criterios de aceptación

Un run de `extract_fields` se considera correcto si:

1. La respuesta contiene `extraction.output` y `extraction.mapped_output`.
2. `extraction.extracted_values` **ya no está presente** (si acordamos rename limpio; dejarlo solo durante la ventana de rollout si el equipo prefiere grace period).
3. `output` y `mapped_output` son estructuralmente iguales (mismas keys, misma longitud de arrays, mismos paths).
4. Para cada hoja escalar en `mapped_output`: `output[path] == mapped_output[path].value`.
5. Cuando `source_text != null`: es sub-cadena de `page.text` en `page_number`.
6. Cuando `value == null`: `source_text == null`, `page_number == null`, `bbox == []`, `inferred == false`.
7. `bbox` es **siempre una lista** (posiblemente vacía); nunca `null`.
8. Cuando `bbox != []`: para cada `BBoxHit`: `page_number` existe en `pages[]` del input; `polygon` tiene exactamente 4 puntos con `x, y ∈ [0, 1]`; `matched_text` es sub-cadena de `page.text` en `BBoxHit.page_number`.
9. Cuando `source_text == null` → `bbox == []`. (No se puede resolver geometría sin anclaje textual.)
10. `inferred == true` ⟺ `value != null` AND (`source_text == null` OR `source_text.strip() != str(value).strip()`).

## 11. Tests sugeridos

Cubrir mínimamente:

1. **Valor literal** (OCR = valor): `source_text == value`, `bbox` tiene 1 hit con `matched_text == source_text`, `inferred == false`.
2. **Valor normalizado** (OCR = `"04/02/2021"`, valor = `"4 de Febrero de 2021"`): `source_text` es el span OCR original, `bbox[0].matched_text == "04/02/2021"`, `inferred == true`.
3. **Valor ausente** (campo opcional no presente): `value=null`, `source_text=null`, `page_number=null`, `bbox=[]`, `inferred=false`.
4. **Multi-token** (nombre compuesto "LAURA VERONICA"): `source_text` es el span completo; `bbox[0].polygon` es el convex hull envolvente de los dos tokens.
5. **Multi-página**: dos documentos/secciones en páginas distintas; cada campo referencia la página correcta en `page_number` y `bbox[0].page_number`.
6. **Objeto anidado**: schema con `titular.nombres`; `mapped_output` mantiene la anidación y cada hoja trae su `bbox`.
7. **Array de objetos**: schema con `beneficiarios[]`; cada elemento se mapea por índice y sus hojas traen `bbox`.
8. **Array de primitivos**: schema con `telefonos[]`; cada elemento es una hoja envuelta con su `bbox`.
9. **Ambigüedad por label** (dos ocurrencias del mismo `source_text` en la página): el `bbox` de cada campo se resuelve al match más próximo por Y al label textual del campo (ver §13.3 paso 5).
10. **Fuzzy fallback** (OCR con typo o espaciado raro que rompe el literal match): literal falla, fuzzy `ratio ≥ 0.85` recupera el rango; `bbox[0].matched_text` refleja el fragmento real del OCR, no `source_text`.
11. **No match** (`source_text` existe pero ni literal ni fuzzy lo localizan en `page.text`): `bbox == []`; `source_text` y `page_number` se conservan.
12. **Confidence**: `bbox[0].confidence` es el promedio de `block.confidence` de los tokens matcheados; `null` si los bloques OCR no traen confidence.
13. **Inferred correcto**: verificar la fórmula contra casos variados (value=null, source_text=null, ambos idénticos, source_text normalizado-distinto).

## 12. Checklist de PR (`vnext-tools`)

- [ ] Ajustar prompt / schema de salida del LLM para emitir `output` y `mapped_output` con leaves `{value, source_text, page_number}` (el LLM **no** emite `bbox` ni `inferred` — los agrega el post-procesado).
- [ ] Renombrar `extracted_values` → `output` en `extract_fields`.
- [ ] Post-procesado: validar que cada `source_text` existe en `page.text` de `page_number`; si no, anular (`source_text: null, page_number: null`).
- [ ] **Nuevo: resolver bbox** en post-procesado — implementar `BoxResolver` siguiendo el algoritmo de §13. Enriquece cada leaf con `bbox: list[BBoxHit]`.
- [ ] **Nuevo: derivar `inferred`** en post-procesado según la fórmula de §6.
- [ ] Ajustar `validate_extraction` para leer `output[field]`.
- [ ] Actualizar fixtures en `events/3_extract_fields_response.json`, `events/4_validate_extraction.json`, `events/4_validate_extraction_response.json` con el shape enriquecido.
- [ ] Tests unitarios cubriendo los 13 casos de §11.
- [ ] Verificar invariantes de §10 en los tests.
- [ ] Logging: INFO cuando cae al fuzzy fallback; WARNING cuando `source_text != null` pero `bbox == []`.

## 13. Resolución de bbox (post-procesado)

Después de que el LLM emite `mapped_output` con leaves `{value, source_text, page_number}`, un paso de post-procesado **dentro de la misma lambda** enriquece cada leaf con `bbox` e `inferred`. Esto ocurre antes de escribir el JSON final a S3.

### 13.1 Input del resolver

Por cada leaf:

- La leaf tal como la emitió el LLM: `{value, source_text, page_number}`.
- Los bloques OCR del documento — ya disponibles en memoria porque son el mismo `pages[]` que la lambda recibió como input. Cada `page.blocks[]` trae `bbox` (4 puntos normalizados), `confidence`, y `text_segments[{start, end}]` que indexan contra `page.text`.
- El **path del field** (p.ej. `"titular.nombres"`, `"beneficiarios[0].nombre"`, `"telefonos[2]"`) — el último segmento alfabético se usa como label candidato para desambiguación.
- El **JSON Schema del documento** (`document_type.fields`) — se usa el `description` del field (si existe) como label candidato adicional.

### 13.2 Output

La leaf se enriquece en su sitio (mismo dict):

```jsonc
{
  "value": <typed>,
  "source_text": "...",
  "page_number": 1,
  "bbox": [/* list[BBoxHit]; [] si no hay match */],
  "inferred": true | false
}
```

### 13.3 Algoritmo paso a paso

Para cada leaf con `source_text != null` y `page_number != null`:

1. **Localizar la página**: `page = find(pages, pn == page_number)`. Si no existe → `bbox = []`, seguir con `inferred`.
2. **Normalización conservadora de `page.text`**: colapsar whitespace consecutivo a un solo espacio. Mantener un mapeo `normalized_offset → original_offset` para poder recuperar posteriormente los `text_segments` de los tokens OCR.
3. **Matching literal**: buscar `source_text` (con la misma normalización) en `page.text_normalized`. Retorna una lista de rangos `[start, end)` traducidos a offsets originales.
4. **Fallback fuzzy** (solo si literal retornó 0 matches):
   - Sliding window sobre `page.text_normalized` con ventanas de tamaño `len(source_text_normalized) ± 20%`, paso = 1 char.
   - Para cada ventana: `difflib.SequenceMatcher(None, source_text_normalized, window).ratio()`.
   - Retener ventanas con `ratio ≥ 0.85`, traducir a rangos originales.
5. **Desambiguación** (si quedan ≥ 2 candidatos):
   - Construir la lista de **labels candidatos** del field:
     - (a) El último segmento alfabético del path, sin underscores (p.ej. `titular.nombres` → `"nombres"`, `beneficiarios[0].nombre` → `"nombre"`).
     - (b) El `description` del field en el JSON Schema (si existe).
   - Para cada label candidato: buscar sus ocurrencias en `page.text` (normalizadas; case/acento-insensible). Para cada ocurrencia, calcular centro Y del bbox del token que la contiene.
   - Para cada match candidato: calcular centro Y del bbox agregado del match.
   - Elegir el match con menor distancia Y al label más cercano.
   - Si **ningún label aparece en el OCR** → fallback a primera ocurrencia en reading order (menor Y, desempate por menor X).
6. **Resolver los tokens del match elegido**: recorrer `page.blocks[]` con `block_type == "token"` y retener los que tocan el rango `[start, end)` vía sus `text_segments`.
7. **Unificar bbox**: polígono convex-hull de 4 puntos envolviendo los 4-point polygons de todos los tokens matcheados. Fórmula simple: `[min(x), min(y)], [max(x), min(y)], [max(x), max(y)], [min(x), max(y)]` sobre los vértices de los tokens.
8. **Confidence**: promedio aritmético de `block.confidence` de los tokens matcheados. `None` si alguno no trae confidence.
9. **matched_text**: `page.text[start:end]` (texto original, no normalizado).
10. Emitir `bbox = [{page_number, polygon, matched_text, confidence}]`.

Para leaves con `source_text == null` (valor ausente o inferido sin anclaje): `bbox = []` directamente, sin pasar por el algoritmo.

### 13.4 Cálculo de `inferred`

```python
def compute_inferred(value, source_text) -> bool:
    if value is None:
        return False
    if source_text is None:
        return True
    return source_text.strip() != str(value).strip()
```

Aplicar a cada leaf independientemente de si hubo match de bbox o no.

### 13.5 Cross-page (edge case)

Si la leaf tiene un único `page_number` pero el span está repartido (p.ej. anverso + reverso de una cédula):

- **v1 (recomendado)**: la lambda solo resuelve en la `page_number` indicada. Si parte del span no aparece ahí, el fuzzy ratio caerá y terminará sin match o con match parcial. `bbox` será `[]` o con un solo hit.
- **v2 (futuro)**: permitir que `BoxResolver` busque el span en todas las páginas del documento y emita un `BBoxHit` por página. Requiere cambiar el schema del LLM para que `page_number` pueda ser `list[int]`.

Implementar v1 para este PR.

### 13.6 Label aliases (extensión opcional)

Los labels OCR a veces no coinciden con los nombres de campo. Ejemplos: `numero_cedula` aparece como "N°" o "CI" en el OCR; `fecha_nacimiento` como "F. Nac.". Si el label no se encuentra, se cae al fallback de reading order (paso 5).

**Propuesta (no bloquea este PR)**: permitir un array opcional `labels: list[str]` en cada property del JSON Schema:

```jsonc
"numero_cedula": {
  "type": "string",
  "description": "Número de cédula",
  "labels": ["N°", "CI", "Cédula", "Número"]
}
```

El `BoxResolver` los añade a la lista de candidatos de §13.3 paso 5. Si no se definen, funciona con los defaults.

### 13.7 Normalización

- **Whitespace**: siempre colapsar espacios múltiples a uno solo (en `page.text` y en `source_text` de igual forma).
- **Case y acentos**:
  - En el matching **literal** (paso 3): NO aplicar case/accent folding — preservar fidelidad para códigos como `"0352652-LA"`, matrículas, etc.
  - En la búsqueda de **labels** (paso 5): SÍ aplicar case folding y strip de acentos (labels son siempre alfabéticos).
  - En el **fuzzy fallback** (paso 4): aplicar case folding antes del ratio, pero conservar el offset original para devolver `matched_text` sin modificar.
- **Puntuación**: no eliminar (preservar guiones, puntos, comas — son parte de códigos y fechas).

### 13.8 Performance y logging

- Complejidad peor caso: `O(campos × len(page.text))` para literal, `O(campos × len(page.text) × ventana)` para fuzzy. Aceptable para documentos típicos (decenas de campos, miles de caracteres).
- Log **INFO** cada vez que una leaf cae al fuzzy fallback (incluir field path, `source_text`, ratio obtenido). Métrica útil para tunear el umbral `0.85`.
- Log **WARNING** cuando una leaf tiene `source_text != null` pero termina con `bbox == []`. Señal de que el OCR o el LLM divergen demasiado.
- Log **DEBUG** el número de candidatos antes y después de la desambiguación por label.
