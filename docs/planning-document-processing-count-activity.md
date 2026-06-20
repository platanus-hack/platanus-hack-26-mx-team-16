# Planning: Count Activity en DocumentProcessingWorkflow

## Objetivo

Agregar una nueva actividad Temporal `create_process_record` que, al finalizar la clasificación de páginas en el `DocumentSetProcessingWorkflow`, cuente el total de páginas procesadas y lo registre como un `ProcessRecord` en la tabla de usage.

---

## Contexto

El pipeline completo (OCR → classify → persist → extract → validate) actualmente no registra el consumo de páginas en `process_records`. Esto impide el cálculo de cuotas mensuales por tenant y la visualización de uso en el frontend.

El módulo `usage` ya tiene todo lo necesario: el domain model `ProcessRecord`, el use case `CreateProcessRecord` (que además verifica cuotas), y el repositorio SQL. Solo falta conectarlo al workflow mediante una actividad Temporal.

---

## Punto de inserción en el pipeline

```
OCR → classify_pages → persist_classified_documents → [NUEVO] → extract_fields → validate → finalize
```

La actividad se ejecuta **después de `persist_classified_documents`** (paso 3) porque en ese punto ya se conoce la lista de documentos con sus rangos de páginas y el `tenant_id` del job.

---

## Qué hay que hacer

### 1. Extender `DocumentProcessingInput`

Agregar el campo `workflow_slug` al input del workflow. Actualmente solo existe `workflow_id` (UUID), pero el use case `CreateProcessRecord` necesita el slug string. El caller ya conoce el slug al momento del dispatch.

### 2. Agregar helper `_count_pages` en el workflow

Función que suma los rangos de páginas de los documentos clasificados para obtener el total de páginas del procesamiento. Debe vivir junto a `_count_fields` y `_count_validations` en `document_set_processing.py`.

### 3. Crear la actividad `CreateProcessRecordActivity`

Nueva clase en `src/common/infrastructure/temporal/activities/` (en `common/` porque es cross-cutting al dominio `usage`, no específica de `workflows`).

Responsabilidades:

- Recibir `tenant_id`, `workflow_slug`, `document_digest` (el `object_key` S3), `page_count` y opcionalmente `analysis_run_id`
- Cargar el `Tenant` desde DB (necesario para el use case)
- Delegar a `CreateProcessRecord` para la inserción y verificación de cuota
- Si el tenant no existe, loggear y retornar sin error (el documento ya fue procesado)

### 4. Agregar la constante del activity name en el workflow

Registrar `CREATE_PROCESS_RECORD_ACTIVITY = "create_process_record"` junto a las demás constantes de actividades en `document_set_processing.py`.

### 5. Llamar la actividad en `pipeline.py`

Después del bloque de `persist_classified_documents`, invocar la nueva actividad cuando `data.persist` sea `True` y `data.tenant_id` y `data.workflow_slug` no sean `None`.

### 6. Registrar la actividad en `run_worker.py`

Instanciar `CreateProcessRecordActivity` con el `session_maker` y agregar el método al listado de `activities` del `Worker`.

### 7. Verificar los callers del workflow

Buscar todos los puntos donde se construye `DocumentProcessingInput` para asegurar que pasen el nuevo campo `workflow_slug`.

---

## Tests

### Unit tests — `_count_pages`

En `tests/workflows/presentation/workflows/test_document_processing.py`:

- Suma correcta de múltiples rangos de páginas
- Ignora documentos con `page_range=None`
- Página única (rango `from == to`)

### Integration tests — `CreateProcessRecordActivity`

En `tests/workflows/presentation/workflows/activities/test_create_process_record.py`, siguiendo el patrón de `test_persist_classified_documents.py`:

- Crea el `ProcessRecord` con el `page_count` correcto
- El registro queda con `tenant_id` y `workflow_slug` correctos
- Si el tenant no existe, retorna vacío sin lanzar excepción

---

## Archivos involucrados

| Acción | Archivo |
|---|---|
| Modificar | `src/common/domain/entities/workflows/document_processing.py` |
| Modificar | `src/workflows/presentation/workflows/document_set_processing.py` |
| Modificar | `src/workflows/presentation/workflows/pipeline.py` |
| Modificar | `run_worker.py` |
| Crear | `src/common/infrastructure/temporal/activities/create_process_record.py` |
| Crear | `tests/workflows/presentation/workflows/activities/test_create_process_record.py` |

---

## Decisiones pendientes

| Pregunta | Opciones | Recomendación |
|---|---|---|
| ¿Qué hacer si el tenant supera su cuota al registrar? | Fallar la activity / loggear y continuar | Loggear y continuar — el documento ya fue procesado |
| ¿Qué usar como `document_digest`? | Hash MD5/SHA del file / `object_key` S3 | `object_key` S3 para MVP — es único sin leer el archivo |
| ¿Registrar también en jobs `PARTIAL`? | Solo `COMPLETED` / siempre | Siempre — el conteo ocurre antes de extract, independiente del resultado |
