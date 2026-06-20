# LlamitAI — Mapeo de Flujos del Frontend

> Documentacin generada para servir como base de pruebas e2e con Cypress.
> Fecha: 2026-03-24 | URL base: `http://localhost:8080`

---

## Arquitectura de Navegacin

| Ruta | Componente | Descripcin |
|------|-----------|-------------|
| `/` | `DynamicLanding` | Landing page con grid de industrias |
| `/admin` | `Admin` | Panel CRUD de industrias y procesos |
| `/workflows/:industry` | `IndustryProcesses` | Lista de procesos de una industria |
| `/workflows/:industry/:process` | `DynamicWorkflow` > `WorkflowRunner` | Runner de workflow (list  builder  run) |

---

## Bloque 1: Landing Page (`/`)

### Flujo 1.1 — Carga de industrias
1. Se muestra loader mientras se obtienen industrias de `GET /admin/industries`
2. Si falla, reintenta hasta 3 veces con delay incremental (cold start del backend)
3. Muestra grid de cards con icono, nombre y descripcin de cada industria
4. Si falla tras 3 reintentos, muestra botn "Reintentar"

### Flujo 1.2 — Navegacin a industria
1. Clic en card de industria
2. Navega a `/workflows/{industry_slug}`

### Flujo 1.3 — Acceso a Admin
1. Clic en botn "Admin" (header) o "Nueva Industria" (body)
2. Navega a `/admin`

---

## Bloque 2: Seleccin de Proceso (`/workflows/:industry`)

### Flujo 2.1 — Carga de procesos
1. Se hace `Promise.all` de `fetchIndustries()` + `fetchProcesses(industry)`
2. Se resuelve metadatos de industria (nombre, icono) y lista de procesos
3. Muestra heading con nombre de industria y cards de procesos

### Flujo 2.2 — Sin procesos
1. Si `processes.length === 0`, muestra estado vaco
2. Botn "Nuevo Proceso" redirige a `/admin?industry={slug}`

### Flujo 2.3 — Navegacin a proceso
1. Clic en card de proceso
2. Navega a `/workflows/{industry}/{process_slug}`

### Flujo 2.4 — Botn "Volver al inicio"
1. Navega a `/`

---

## Bloque 3: Workflow Runner (`/workflows/:industry/:process`)

El `WorkflowRunner` tiene 3 vistas internas: **list**, **builder**, **run**.

### Flujo 3.1 — Vista List (estado vaco)
1. Se cargan workflows guardados en `localStorage` para el `workflowType`
2. Si no hay workflows: muestra estado vaco con botn "Crear mi primer workflow"
3. Si hay workflows: muestra cards con nombre, fecha, nro de documentos, status

### Flujo 3.2 — Vista List (con workflows)
1. Cada card muestra: nombre, fecha creacin/actualizacin, cantidad de doc types
2. Acciones por workflow:
   - **Editar** (icono Settings2): abre vista `builder` con el workflow cargado
   - **Ejecutar** (icono Play): abre vista `run`
   - **Eliminar** (icono Trash2): elimina de localStorage

### Flujo 3.3 — Vista Builder (crear/editar workflow)
1. **Nombre del workflow**: campo texto, pre-llenado con `default_workflow_name`
2. **Calidad de lectura OCR**: selector (Bsico  rpido / Mejorado / Avanzado)
   - Aplica solo cuando se usa Modelo 3
3. **Modelo de estructuracin**: selector (Modelo 1 / gemini-2.5-flash)
   - Modelo LLM para convertir texto extrado a JSON
4. **Documentos incluidos**:
   - Lista de doc types seleccionados con cantidad de campos
   - Cada doc type se puede expandir para editar su schema
   - Botn "Agregar documento": abre modal con catlogo + documento personalizado
   - Botn "Importar JSON": importa config completa de workflow
   - Cada doc type tiene botn "Editar schema" que expande el editor inline
5. **Schema Editor** (por documento):
   - Nombre del documento (title)
   - Lista de campos con: key, etiqueta, tipo (Texto/Nmero/Booleano/Fecha/Enum/Objeto/Array)
   - Toggle "Usar base de conocimientos" (KB) por campo
   - Detalles expandibles: descripcin, ejemplo, aliases, pista de extraccin, requerido
   - Campos anidados para tipos Object y Array
   - Botn "Agregar campo"
6. **Reglas de negocio** (ver Bloque 5 para detalle)
7. **Base de conocimiento** (ver Bloque 6 para detalle)
8. **Acciones finales**:
   - "Exportar JSON de ejemplo": descarga archivo JSON con la estructura del workflow
   - "Guardar workflow" (persiste en localStorage)
   - "Guardar y continuar" (guarda + abre vista `run`)
   - "Volver": regresa a vista list

#### 3.3.1 — Importar JSON de documentos y campos
1. Clic en "Importar JSON" (seccin Documentos incluidos) abre `ImportJsonModal`
2. Muestra ejemplo de formato esperado:
   ```json
   [{"Fondos": [{"key": "nombre_cliente", "nombre": "Cliente", "etiqueta": "Nombre del Cliente", "descripcion": "..."}]}]
   ```
3. Opciones de entrada:
   - **Pegar JSON**: textarea para pegar directamente
   - **Cargar desde archivo**: file picker (acepta `.json`)
   - **Copiar ejemplo**: copia al clipboard
4. Al importar:
   - Parsea JSON, valida que sea array
   - Por cada entrada: crea doc type con key sanitizado (lowercase + underscores)
   - Cada field se crea como tipo "string" con label de `etiqueta` o `nombre` o `key`
   - Se asigna `_fieldId` estable a cada campo
   - Los nuevos doc types se agregan a la lista (sin duplicar existentes)
5. Error: toast "Formato de JSON invlido"

#### 3.3.2 — Exportar JSON de ejemplo
1. Clic en "Exportar JSON de ejemplo" (footer del builder)
2. Genera un JSON de muestra con valores placeholder por tipo de campo:
   - string: `"(label)"`, number: `0`, boolean: `false`, date: `"YYYY-MM-DD"`
   - enum: primer valor del enum, object: recursivo, array: `[{recursivo}]`
3. Descarga archivo `{nombre_workflow}_schema_preview.json`
4. Toast: "JSON exportado — Se descarg el archivo con el preview de la extraccin."

#### 3.3.3 — Modelos configurables
1. **Calidad de lectura OCR** (aplica solo a Model 3):
   - `gemini-2.0-flash-001` — Bsico (rpido)
   - `gemini-2.5-flash` — Mejorado (balanceado)
   - `gemini-3-flash-preview` — Avanzado (alta precisin)
2. **Modelo de estructuracin** (convierte texto extrado a JSON):
   - `openai` — Modelo 1
   - `gemini-2.5-flash` — Modelo 2

#### 3.3.4 — KB por documento (en builder)
1. Al expandir un doc type para editar schema, si hay docs KB disponibles:
2. Se muestra seccin "Base de conocimiento para extraccin"
3. Chips de cada doc KB disponible: clic para toggle asociacin
4. Los KB asociados a un doc type se inyectan como contexto al extraer ESE documento especfico
5. Se persiste en `perDocKbIds[docKey]` del workflow

#### 3.3.5 — Modal "Agregar documento" (`AddDocModal`)
1. Se abre al hacer clic en "Agregar documento"
2. Muestra lista de doc types del catlogo que an no estn incluidos
3. Cada item tiene checkbox para seleccin mltiple
4. Seccin "Documento personalizado":
   - Campo "Nombre de tu documento" (texto libre)
   - Campo "Key interno" (opcional, se auto-genera si no se provee)
   - Enter en cualquier campo ejecuta la accin de agregar
5. Botn "Agregar (N)" agrega los seleccionados + el personalizado al workflow
6. Si todos los documentos del catlogo ya estn incluidos: muestra "Todos los documentos ya estn incluidos"

#### 3.3.6 — Schema Editor detallado (por documento)
1. **Ttulo del documento**: campo editable (ej. "Certificado Mdico")
2. **Cabecera de columnas**: Key | Etiqueta | Tipo | KB | detalles | eliminar
3. **FieldRow** (recursivo): cada campo tiene:
   - **Key**: input mono, auto-sanitiza a lowercase con underscores
   - **Etiqueta**: input texto libre
   - **Tipo**: selector (Texto/Nmero/Booleano/Fecha/Enum/Objeto/Array)
   - **KB toggle**: switch para inyectar contexto de Knowledge Base al extraer este campo
   - **Detalles** (colapsable, indicador de punto verde si hay datos):
     - Descripcin (texto)
     - Ejemplo de valor (texto)
     - Nombres alternativos (separados por coma)
     - Pista de ubicacin (texto libre para el LLM)
     - Valores permitidos (solo para tipo Enum, separados por coma)
     - Toggle "Campo requerido"
   - **Eliminar campo**: botn rojo (visible on hover)
4. **Campos anidados** (Object/Array):
   - Botn chevron para expandir/colapsar
   - Sub-campos con indentacin visual (border-left)
   - Botn "Agregar campo anidado"
   - Para tipo Array: se editan las properties del item schema
5. **Agregar campo**: botn dashed al fondo, crea `campo_N` con tipo String
6. **Hydrate IDs**: al montar, se asignan `_fieldId` estables a campos sin ID (para evitar remount al renombrar keys)

### Flujo 3.4 — Vista Run (ejecucin de workflow)

#### 3.4.1 — Gestin de Casos
1. **Crear caso**: genera `Caso N` con documentos vacos (status DRAFT) para cada doc type del workflow
2. **Sidebar de casos**: lista lateral con todos los casos del workflow
   - Cada caso muestra: nombre (editable inline), status badge, fecha
   - Botn eliminar (Trash2, visible on hover) por caso
   - Clic en caso cambia al caso activo (con check de cambios sin guardar)
3. **Renombrar caso**: el nombre del caso activo es un `<Input>` editable directamente en el header
4. **Eliminar caso**: botn Trash2 en sidebar, elimina de localStorage, auto-cambia al primer caso restante
5. **Guardar caso**:
   - Botn explcito "Guardar caso" (icono Save)
   - Auto-save tras editar campos extrados en DocumentDetailModal
   - **Indicador de estado de guardado**:
     - "Cambios sin guardar" (amarillo con AlertCircle) cuando hay cambios pendientes
     - "Guardando..." (spinner) durante persistencia
     - "Guardado" (verde con check) tras xito
6. **Modal cambios sin guardar** (al cambiar de caso con cambios pendientes):
   - Ttulo: "Cambios sin guardar"
   - Mensaje: "Tienes cambios sin guardar. Qu deseas hacer?"
   - Tres botones (vertical):
     1. "Guardar y cambiar" (primario)
     2. "Cambiar sin guardar" (borde)
     3. "Cancelar" (texto)

#### 3.4.2 — Subida de Documentos
1. **Seccin colapsable** "Documentos del caso" con ChevronDown/ChevronRight para expandir/colapsar el grid
2. Grid de cards `DocUploadCard` por cada doc type del workflow
3. Cada card tiene:
   - **Drag & drop** o **clic para seleccionar** archivo (imagen o PDF)
   - Toggle "Incluir en extraccin" (activado por defecto al subir)
   - Sin archivo: texto "Sube un archivo para habilitar extraccin"
   - Preview del archivo (thumbnail comprimido JPEG para imgenes, primera pgina para PDF)
   - Status badge: Vaco / Subido / Procesando / Extrado / Error
   - Overlay on hover (doc subido no extrado): botones "Reemplazar" + eliminar (X rojo)
   - Overlay on hover (doc extrado): botn "Ver detalles" (primario) + "Reemplazar" + eliminar
   - Badge "Excluido" si toggle de inclusin est desactivado (card con opacity reducida)
   - Botn "Dividir pginas" (solo para PDFs): abre `PageSplitterModal`
4. Upload: archivo se sube a `POST /files/upload`, se obtiene `fileId`; preview se genera localmente (imagen: compressImage 800x800, PDF: thumbnail primera pgina)
5. **Botones de seleccin masiva** (aparecen cuando hay docs subidos):
   - "Sel. todo" (icono CheckSquare): activa inclusin en todos los docs con archivo
   - "Desel. todo" (icono Square): desactiva inclusin en todos los docs con archivo

#### 3.4.3 — Extraccin OCR
1. Clic en "Extraer datos": abre modal `OcrModal`
2. **Modal de seleccin de proveedor OCR**:
   - Ttulo: "Selecciona modelo"
   - Muestra cantidad de docs elegibles: "N documento(s) seleccionado(s) para procesar"
   - Proveedores como radio buttons circulares: **Model 1**, **Model 2**, **Model 3**
   - Botones: "Cancelar" / "Iniciar extraccin"
3. Al seleccionar proveedor y confirmar:
   - Docs elegibles se marcan como `PROCESSING`
   - `POST /{industry}/{process}/extract` enva payload con fileIds, schemas, KB config
   - Backend retorna `job_id`
   - Se guarda `pendingJobId` en caso (sobrevive a refresh)
   - Polling cada 2s a `GET /{industry}/{process}/extract-status/{jobId}`
   - Al completar: docs pasan a `EXTRACTED` o `ERROR`
4. Botn "Cancelar": `POST /{industry}/{process}/extract-cancel/{jobId}`
5. Si se recarga pgina con `pendingJobId`, se reanuda polling automticamente

#### 3.4.4 — Vista Previa de Datos Extrados
1. Seccin colapsable "Vista previa de datos extrados"
2. Por cada doc extrado: campos clave-valor con formato inteligente
   - Objetos anidados, arrays de objetos, booleanos, etc.
   - Indicador de proveedor OCR usado y nivel de confianza
   - Badge KB si se us contexto de base de conocimiento

#### 3.4.5 — Detalle de Documento (Modal `DocumentDetailModal`)
1. Clic en "Ver detalles" sobre una card extrada
2. Abre modal a pantalla completa con dos paneles:
   - **Panel izquierdo — Preview del documento**:
     - **PDF**: visor con navegacin de pginas (< pgina N/M >), zoom in/out (25%-300%), canvas render via pdfjs
     - **Imagen**: visor con zoom in/out (25%-400%)
     - Carga el archivo desde backend via `GET /files/{fileId}` o desde base64
     - Estados: loading (spinner), error ("No se pudo renderizar"), success (canvas/img)
   - **Panel derecho — Datos extrados**:
     - Header con: doc type label, proveedor OCR, confianza, fecha de actualizacin
     - **Texto crudo OCR**: seccin colapsable `<details>` con summary "Texto crudo extrado (OCR)" que revela el texto raw en contenedor scrollable (max-h-48)
     - Toggle "Modo edicin" / "Solo lectura"
     - Cada campo muestra: label + valor formateado
     - **Tipos de renderizado**:
       - Texto/Nmero: inline
       - Booleano: "S" / "No"
       - Array de objetos: tabla con headers auto-detectados
       - Array simple: items separados por coma
       - Objeto anidado: key-value list con indentacin
       - Markdown table: renderizado como tabla HTML con export a CSV
       - Valor vaco: "No encontrado" (italics)
     - **Modo edicin** (por campo):
       - Booleano: select S/No
       - Array/Objeto: textarea JSON editable
       - Texto/Nmero: input text
     - Botn "Descargar" por campo: descarga como JSON o CSV (si es markdown table)
     - Botn "Guardar cambios": persiste y auto-save al caso
3. **Bloqueo de scroll**: mientras el modal est abierto, el body no hace scroll (`overflow: hidden`)
4. Cerrar:
   - Botn X
   - Tecla ESC: **dos pasos** — si est en modo edicin, primer ESC sale de edicin; segundo ESC cierra el modal
   - Clic en backdrop

#### 3.4.6 — Dividir Pginas de PDF (Modal `PageSplitterModal`)
1. Solo disponible para documentos PDF subidos (botn "Dividir pginas")
2. Al abrir:
   - Descarga el PDF desde `GET /files/{fileId}`
   - Renderiza thumbnail de cada pgina con pdfjs
   - Cada pgina se inicializa asignada al doc type actual
3. Grid de thumbnails con selector por pgina:
   - Dropdown por pgina: seleccionar doc type destino o "Omitir"
   - Las opciones son todos los doc types activos del workflow
4. Al confirmar "Dividir":
   - Agrupa pginas por doc type destino (excluye "Omitir")
   - Usa `pdf-lib` para crear un PDF nuevo por grupo
   - Sube cada PDF resultante a `POST /files/upload`
   - Genera thumbnail de primera pgina para cada nuevo PDF
   - Retorna `SplitResult[]` al padre que actualiza los docs del caso
5. Validacin: si todas las pginas estn en "Omitir", muestra error "Sin pginas asignadas"
6. Estados: loading (cargando pginas), splitting (procesando), error (toast)

#### 3.4.7 — Anlisis de Reglas de Negocio
1. Botn "Analizar" (solo si hay reglas de negocio definidas y docs extrados)
2. Si no hay reglas: toast "Sin reglas de negocio"
3. `POST /{industry}/{process}/analyze-stream` con reglas + datos extrados
4. Respuesta va **SSE (Server-Sent Events)**: resultados llegan en streaming
5. Se limpia el panel de resultados previos antes de empezar
6. Por cada regla evaluada (chunk SSE `data: {...}`):
   - `rule_id`: ID de la regla
   - `rule_name`: nombre de la regla
   - `is_passed`: boolean (pass/fail)
   - `reasoning`: texto explicativo
   - `structured_data`: datos estructurados opcionales
7. Toast "Anlisis completado" al finalizar
8. Auto-save del caso con resultados

#### 3.4.8 — Panel de Resultados de Anlisis (`AnalysisResultsPanel`)
1. Muestra cada regla evaluada como un `RuleResultCard` colapsable
2. Cada card tiene:
   - Icono: CheckCircle2 (verde/pass) o XCircle (rojo/fail)
   - Nombre de la regla + badge pass/fail
   - Botn expandir/colapsar (ChevronDown/Right)
3. Contenido expandido:
   - **Reasoning**: texto explicativo del LLM
   - **Datos estructurados** (si existen), renderizado segn tipo:
     - `two_lists`: dos columnas (ej. "Cubiertos" / "No cubiertos") con listas de items coloreadas verde/rojo
     - `items_status`: grid de items con badge pass/fail/warn + razn, por cada item
     - `metric`: valor destacado grande con unidad y label (ej. "85.5 % Cobertura")
     - `table`: tabla multi-columna con datos tabulares
4. **Tabla pivot agregada**: cuando 2+ reglas producen `items_status`, se genera automticamente una tabla cruzada:
   - Filas = items nicos (unin de todos los items de todas las reglas)
   - Columnas = reglas
   - Celdas = icono pass/fail/warn/ para cada combinacin

---

## Bloque 4: Panel de Administracin (`/admin`)

### Flujo 4.1 — Gestionar Industrias (panel izquierdo)
1. Lista de industrias con icono, nombre, slug
2. **Crear industria**: botn "Nueva"  formulario con nombre, slug, icono, descripcin
3. **Editar industria**: botn editar (visible on hover)  formulario pre-llenado
4. **Eliminar industria**: botn eliminar (visible on hover)
5. **Seleccionar industria**: clic en card  carga procesos en panel derecho

### Flujo 4.2 — Gestionar Procesos (panel derecho)
1. Sin industria seleccionada: muestra placeholder "Selecciona una industria"
2. Con industria seleccionada, sin procesos: estado vaco + "Nuevo proceso"
3. **Crear proceso**: formulario con:
   - Nombre, slug, icono, descripcin
   - Nombre de workflow por defecto
   - Seccin expandible "Configurar prompts":
     - Generic Prompt (fallback para extraccin)
     - Extraction Prompt (con placeholders `{schema_title}`, `{fields_desc}`, `{extracted_text}`)
4. **Editar proceso**: botn "Editar"  formulario pre-llenado (slug deshabilitado)
5. **Eliminar proceso**: botn eliminar
6. Acceso rpido: query param `?industry={slug}` pre-selecciona industria

---

## Industrias y Procesos Configurados

### Industria: Banca
| Slug | `banking` |
|------|-----------|
| Icono | `landmark` |
| Descripcin | Automatiza procesos bancarios y de riesgo. |

| Proceso | Slug | Ruta | Doc Types |
|---------|------|------|-----------|
| Microcrditos | `microcredits` | `/workflows/banking/microcredits` | 10 (Solicitud de crdito, Cdula de identidad, Comprobante de ingresos, Extracto bancario, Central de riesgos, Recibo de servicios, +4) |
| Retenciones | `fund-freezing` | `/workflows/banking/fund-freezing` | 3 |
| Fondos de Garantia | `fondos` | `/workflows/banking/fondos` | 0 |

### Industria: Seguros
| Slug | `insurance` |
|------|-------------|
| Icono | `shield` |
| Descripcin | Valida recetas, plizas y automatiza autorizaciones. |

| Proceso | Slug | Ruta | Doc Types |
|---------|------|------|-----------|
| Seguro de Salud | `health` | `/workflows/insurance/health` | 2 |

### Industria: Real State
| Slug | `real-state` |
|------|--------------|
| Icono | `building-2` |
| Descripcin | Analiza expedientes inmobiliarios y riesgos. |

| Proceso | Slug | Ruta | Doc Types |
|---------|------|------|-----------|
| Property Buy Report | `report-house-buying` | `/workflows/real-state/report-house-buying` | 9 |

### Industria: Transporte y Logistica
| Slug | `transport-logistics` |
|------|----------------------|
| Icono | `package` |
| Descripcin | Bills of Ladding, etc |

| Proceso | Slug | Ruta | Doc Types |
|---------|------|------|-----------|
| _(sin procesos configurados)_ | — | — | — |

---

## Bloque 5: Reglas de Negocio (detalle de `BusinessRulesSection`)

### Flujo 5.1 — Crear regla manualmente
1. Clic en "Agregar regla"
2. Se crea una regla vaca con nombre "Nueva Regla N" y se abre en modo edicin
3. Editor inline con:
   - **Nombre de regla**: input texto (ej. "Validacin de montos")
   - **Toggle Activa/Inactiva**: switch
   - **Lgica de la regla**: textarea con **autocompletado inteligente**:
     - Escribir `@` activa sugerencias de documentos del schema
     - Escribir `@DOC.` activa sugerencias de campos de ese documento
     - Escribir `{{` activa sugerencias de variables del sistema:
       - `{{today}}` — Fecha de hoy (YYYY-MM-DD)
       - `{{current_year}}` — Ao actual
       - `{{current_month}}` — Mes actual (1-12)
       - `{{current_day}}` — Da actual del mes (1-31)
     - Navegacin con ArrowUp/Down, seleccin con Enter/Tab, cancelar con Escape
   - **Base de conocimiento por regla**: chips seleccionables de docs KB disponibles
     - Toggle individual para asociar/desasociar un doc KB a esta regla
4. Botones: "Cancelar" (si regla vaca se elimina) / "Guardar regla"
5. **Validacin de referencias rotas**: si la lgica referencia un `@DOC.campo` que no existe en el schema actual, se muestra indicador de advertencia

### Flujo 5.2 — Editar regla existente
1. Clic en botn "Editar" (icono lpiz) de una regla en la lista
2. Se abre el mismo editor inline de 5.1 con datos pre-llenados
3. Guardar actualiza la regla en el array

### Flujo 5.3 — Eliminar regla
1. Clic en botn "Eliminar" (icono Trash2) en la lista
2. Se elimina inmediatamente (sin confirmacin)

### Flujo 5.4 — Toggle activa/inactiva (vista lista)
1. Cada regla en la lista tiene un switch Activa/Inactiva
2. Toggle directo sin abrir editor

### Flujo 5.5 — Importar reglas desde JSON
1. Clic en "Importar JSON" abre `ImportRulesModal`
2. Muestra ejemplo de formato esperado:
   ```json
   [{"rule_name": "...", "logica": "El @DOC.campo debe..."}]
   ```
3. Opciones de entrada:
   - **Pegar JSON**: textarea para pegar directamente
   - **Cargar desde archivo**: botn que abre file picker (acepta `.json`)
   - **Copiar ejemplo**: botn copia el JSON de ejemplo al clipboard
4. Al importar:
   - Parsea JSON, valida que sea array
   - Crea `BusinessRule` por cada item con `logica` no vaco
   - Nombre por defecto: "Regla importada" si `rule_name` vaco
   - Todas las reglas importadas se crean como activas
5. Error: toast "Formato de JSON invlido" si el JSON no parsea

### Flujo 5.6 — Sugerir reglas con IA
1. Clic en "Sugerir reglas" abre `SuggestRulesModal`
2. **Pre-requisito**: debe haber docs en la base de conocimiento (`kbIds.length > 0`)
   - Si no hay: muestra advertencia "Agrega documentos a la base de conocimiento primero" y botn deshabilitado
3. Muestra panel de **variables disponibles**: chips `@DOC.campo` agrupados por documento
   - Si hay una regla expandida: clic en variable la inserta en la posicin del cursor
   - Si no hay regla expandida: chips deshabilitados con tooltip
4. Campo **Instruccin** (opcional): textarea para guiar al modelo (ej. "Genera reglas para verificar medicamentos...")
5. Botn "Generar reglas": `POST /kb/suggest-rules` con `{kb_ids, doc_schema, hint}`
   - Muestra spinner "Generando..."
6. Resultado: lista de reglas sugeridas como cards seleccionables:
   - Cada card tiene: checkbox, nombre, preview de lgica
   - "Seleccionar todas" / "Deseleccionar todas"
   - Clic en card: expande para **editar nombre y lgica** antes de agregar
   - Textarea editable con refs para insercin de variables
7. Botn "Agregar N regla(s)": agrega las seleccionadas (con ediciones) al workflow

---

## Bloque 6: Base de Conocimiento (detalle de `KnowledgeBaseSection`)

### Flujo 6.1 — Subir documento KB
1. Clic en "Subir documento" abre file picker
2. Acepta: `.pdf`, `.txt`, `.md`, `.xlsx`, `.xls` (mltiples archivos)
3. Upload secuencial a `POST /kb/upload` con FormData
4. Soporta **cancelacin**: botn "Cancelar" durante la subida (usa `AbortController`)
   - Si se cancela: toast "Subida cancelada"
5. Al completar: doc se agrega a lista de adjuntos y se asocia al workflow
6. Toast: "N documento(s) procesado(s)"
7. Error: toast "Error al subir documento" con mensaje del servidor

### Flujo 6.2 — Documentos adjuntos al workflow
1. Lista de docs adjuntos con:
   - Nombre del archivo
   - Badge "RAG" o "texto completo" segn tamao
   - Cantidad de caracteres (ej. "45k chars")
   - Preview de texto (primeras lneas, 2 lneas mximo)
2. Botn "Desconectar" (icono AlertCircle): quita el doc del workflow sin eliminarlo
3. Botn "Eliminar" (icono Trash2): elimina permanentemente via `DELETE /kb/{kbId}`

### Flujo 6.3 — Documentos disponibles (no adjuntos)
1. Seccin "Disponibles" muestra docs KB que existen pero no estn asociados al workflow actual
2. Clic en el doc lo adjunta al workflow
3. Cada doc tiene botn "Eliminar" para eliminacin permanente

### Flujo 6.4 — Estado vaco
1. Si no hay docs adjuntos ni disponibles: placeholder "Sube un documento para agregar contexto al anlisis"

---

## Endpoints API Utilizados

| Mtodo | Endpoint | Uso |
|--------|----------|-----|
| GET | `/admin/industries` | Listar industrias |
| POST | `/admin/industries` | Crear industria |
| PUT | `/admin/industries/{slug}` | Actualizar industria |
| DELETE | `/admin/industries/{slug}` | Eliminar industria |
| GET | `/admin/industries/{slug}/processes` | Listar procesos de industria |
| GET | `/admin/processes/{industry}/{process}` | Obtener config de proceso |
| POST | `/admin/processes` | Crear proceso |
| PUT | `/admin/processes/{industry}/{process}` | Actualizar proceso |
| DELETE | `/admin/processes/{industry}/{process}` | Eliminar proceso |
| POST | `/files/upload` | Subir archivo (retorna `fileId`) |
| DELETE | `/files/{fileId}` | Eliminar archivo |
| POST | `/{industry}/{process}/extract` | Iniciar extraccin OCR (retorna `job_id`) |
| GET | `/{industry}/{process}/extract-status/{jobId}` | Consultar estado de extraccin |
| POST | `/{industry}/{process}/extract-cancel/{jobId}` | Cancelar extraccin |
| POST | `/{industry}/{process}/analyze-stream` | Analizar reglas de negocio (SSE) |
| GET | `/kb/` | Listar documentos de Knowledge Base |
| POST | `/kb/upload` | Subir documento KB (retorna `KbDocMeta`) |
| DELETE | `/kb/{kbId}` | Eliminar documento KB |
| POST | `/kb/suggest-rules` | Generar reglas sugeridas con IA |
| GET | `/files/{fileId}` | Descargar archivo por ID (usado por PDF viewer y splitter) |

---

## Tipos y Estados

### Estados de Caso (`CaseStatus`)
| Estado | Label | Significado |
|--------|-------|-------------|
| `DRAFT` | Borrador | Caso recin creado o sin docs subidos |
| `READY` | Listo | Al menos un documento subido |
| `EXTRACTED` | Extrado | Todos los documentos extrados |
| `ERROR` | Error | Al menos un documento con error |

### Estados de Documento (`DocStatus`)
| Estado | Label | Significado |
|--------|-------|-------------|
| `EMPTY` | Vaco | Sin archivo subido |
| `UPLOADED` | Subido | Archivo subido, pendiente extraccin |
| `PROCESSING` | Procesando | Extraccin en curso |
| `EXTRACTED` | Extrado | Datos extrados correctamente |
| `ERROR` | Error | Fallo en extraccin |

### Proveedores OCR (`OcrProvider`)
| Proveedor | Descripcin |
|-----------|-------------|
| Model 1 | Proveedor OCR 1 |
| Model 2 | Proveedor OCR 2 |
| Model 3 | Proveedor OCR 3 (usa Gemini, configurable con calidad Bsico/Mejorado/Avanzado) |

---

## Almacenamiento Local

- Los workflows se persisten en `localStorage` con namespace por `workflowType`
- Los casos (`WorkflowCase`) se guardan dentro del estado del workflow
- Los archivos se suben al backend (solo se almacena `fileId` localmente)
- Previews/thumbnails se guardan como base64 comprimido (JPEG) en localStorage
- Lmite de ~5MB por caso; si se excede, se muestra error "Almacenamiento lleno"

---

## Componentes Clave

| Componente | Ubicacin | Responsabilidad |
|------------|----------|-----------------|
| `DynamicLanding` | `pages/DynamicLanding.tsx` | Landing con grid de industrias |
| `IndustryProcesses` | `pages/workflows/IndustryProcesses.tsx` | Lista de procesos por industria |
| `DynamicWorkflow` | `pages/workflows/DynamicWorkflow.tsx` | Carga config y monta WorkflowRunner |
| `WorkflowRunner` | `components/WorkflowRunner.tsx` | Vistas list/builder/run |
| `RunView` | `components/workflow/RunView.tsx` | Ejecucin: upload, extract, analyze |
| `DocUploadCard` | (dentro de RunView) | Card de upload por doc type |
| `ExtractionPreview` | (dentro de RunView) | Vista previa de datos extrados |
| `SchemaEditor` | (dentro de WorkflowRunner) | Editor de schema por doc type |
| `FieldRow` | (dentro de WorkflowRunner) | Campo recursivo del schema editor |
| `AddDocModal` | (dentro de WorkflowRunner) | Modal para agregar doc types |
| `BusinessRulesSection` | `components/BusinessRulesConfig.tsx` | Config de reglas de negocio |
| `KnowledgeBaseSection` | `components/workflow/KnowledgeBaseSection.tsx` | Gestin de docs KB |
| `RuleResultCard` | `components/workflow/RuleResultCard.tsx` | Resultado de regla evaluada |
| `PageSplitterModal` | `components/workflow/PageSplitterModal.tsx` | Dividir pginas de PDF |
| `DocumentDetailModal` | `components/DocumentDetailModal.tsx` | Detalle de documento extrado |
| `Admin` | `pages/Admin.tsx` | Panel de administracin |
| `WorkflowCard` | `components/WorkflowCard.tsx` | Card reutilizable para industria/proceso. Soporta prop `disabled` que muestra "(Prximamente)" y reduce opacity. Animaciones: hover scale 1.02, active scale 0.98, pulso verde en esquina |
| `NavLink` | `components/NavLink.tsx` | Wrapper de React Router NavLink con soporte de `activeClassName` (no usado actualmente en rutas) |

---

## Bloque 7: Estados de Error y Edge Cases

### Flujo 7.1 — Pgina 404 (NotFound)
1. Cualquier ruta no definida muestra componente `NotFound`
2. Ruta: `/*` (catch-all)
3. Muestra: heading "404", mensaje "Oops! Page not found", enlace "Return to Home" (`/`)
4. Registra en consola: `404 Error: User attempted to access non-existent route: {pathname}`

### Flujo 7.2 — Proceso no encontrado
1. Si `fetchProcessConfig(industry, process)` falla
2. Muestra: "Proceso no encontrado" con mensaje de error

### Flujo 7.3 — Error de carga de industrias (Landing)
1. `fetchIndustries()` falla 3 veces consecutivas
2. Muestra: "No se pudieron cargar las industrias" + botn "Reintentar"
3. Reintentar: vuelve a intentar desde 0 con retries incrementales

### Flujo 7.4 — Error de almacenamiento (localStorage lleno)
1. Al guardar caso si `localStorage` est lleno (~5MB)
2. Captura `QuotaExceededError`
3. Toast: "Almacenamiento lleno — el archivo es probablemente demasiado pesado"

### Flujo 7.5 — Error de extraccin OCR
1. Si `POST /extract` falla: todos los docs elegibles pasan a `ERROR`
2. Si polling falla: docs en `PROCESSING` pasan a `ERROR`
3. Toast con detalle del error

### Flujo 7.6 — Error de anlisis de reglas
1. Si `POST /analyze-stream` falla: toast "Error en anlisis"
2. Si SSE chunk no parsea: log en consola, contina con siguiente chunk

### Flujo 7.7 — Cambios sin guardar (RunView)
1. Al intentar cambiar de caso con cambios pendientes
2. Se abre modal de confirmacin "Cambios sin guardar"
3. Opciones: Descartar / Guardar y cambiar

### Flujo 7.8 — Reanudacin de extraccin tras refresh
1. Si el usuario recarga la pgina durante una extraccin
2. El `pendingJobId` se persisti en localStorage
3. Al montar RunView: detecta `pendingJobId` y reanuda polling automticamente

### Flujo 7.9 — Error al cargar PDF (viewers)
1. **DocumentDetailModal**: si pdfjs falla, muestra "No se pudo renderizar el PDF"
2. **PageSplitterModal**: si falla descarga/render, toast error y cierra modal
3. **Thumbnail generation**: si falla, fallback a icono placeholder

### Flujo 7.10 — Error al subir archivo
1. Si `POST /files/upload` falla: toast "Error subiendo archivo"
2. El doc type mantiene estado `EMPTY`

### Flujo 7.11 — Cdigo legacy no enrutado
1. `pages/Index.tsx` existe pero **NO est en las rutas** de App.tsx
2. Es un analizador de seguros legacy (receta + pliza) con `UploadZone` y `AnalysisResults`
3. Componentes asociados legacy: `UploadZone.tsx`, `AnalysisResults.tsx`
4. **No es alcanzable por el usuario** — no requiere tests e2e

### Flujo 7.12 — Eliminar archivo del backend
1. Al remover un documento del caso: si tiene `fileId` (no base64)
2. Se enva `DELETE /files/{fileId}` al backend
3. Si falla: log en consola (no bloquea la operacin local)

---

## Screenshots de Referencia

| Pantalla | Archivo |
|----------|---------|
| Landing Page | `docs/frontend/screenshots/01-landing.png` |
| Banca - Procesos | `docs/frontend/screenshots/02-banca-processes.png` |
| Workflow List (vaco) | `docs/frontend/screenshots/03-workflow-list-empty.png` |
| Workflow Builder | `docs/frontend/screenshots/04-workflow-builder.png` |
| Admin Panel | `docs/frontend/screenshots/05-admin.png` |