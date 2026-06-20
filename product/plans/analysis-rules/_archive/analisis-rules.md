---
feature: analysis-rules
type: plan
status: obsolete
coverage: 0
audited: 2026-06-16
superseded_by: backend DDD re-arch (ver docs/backend/)
---


  Flujo completo

  1. Configuración de reglas (BusinessRulesConfig.tsx)
  - El usuario crea reglas con texto que puede referenciar
  variables de documentos (@DOC_TYPE.field_name) y variables del
  sistema ({{today}}, {{current_year}})
  - Opcionalmente asocia Knowledge Bases (kb_ids) para dar
  contexto adicional
  - También puede importar reglas desde archivo o pedir
  sugerencias con IA

  2. Trigger del análisis (RunView.tsx → handleRunAnalysis())
  - El usuario hace clic en "Analizar"
  - Se recolectan los campos extraídos de todos los documentos
  (extractedFields)
  - Se valida que haya reglas configuradas y datos extraídos

  3. Llamada API con streaming
  - POST a /{config.apiSlug}/analyze-stream enviando las reglas +
   datos extraídos
  - La respuesta es Server-Sent Events (SSE) — el backend va
  enviando resultados línea por línea como data: JSON

  4. Parsing del stream
  - El frontend lee con ReadableStreamDefaultReader, acumula los
  resultados parciales en case.analysisResults
  - Cada resultado llega como RuleEvaluationResult con:
  is_passed, reasoning, structured_data opcional, y mensajes de
  error

  5. Visualización de resultados (RuleResultCard.tsx)
  - Badge resumen (passed/failed/error)
  - Soporte para datos estructurados: two_lists (cubierto/no
  cubierto), items_status (badges por ítem), metric (valor
  único), table (multi-columna)
  - Panel opcional de pivot table

  Estado

  - React useState con persistencia en localStorage via
  getRunState() / saveCase()
  - El caso activo se computa desde cases[] + activeCaseId

  Archivos clave

  - frontend/src/components/workflow/RunView.tsx — orquestador
  principal
  - frontend/src/components/BusinessRulesConfig.tsx — UI de
  gestión de reglas
  - frontend/src/components/workflow/RuleResultCard.tsx —
  renderizado de resultados
  - frontend/src/types/workflow.ts — tipos (BusinessRule,
  RuleEvaluationResult, etc.)

✻ Crunched for 5m 47s

❯ ahora mapea todo el flujo de analisis incluyendo el del        
backend y frontend                                               

⏺ Explore(Map backend analysis flow for business rules)
  ⎿  Done (10 tool uses · 59.5k tokens · 1m 19s)
  (ctrl+o to expand)

⏺ Explore(Trace frontend analysis trigger and streaming consumption)

  ⎿  Done (9 tool uses · 62.4k tokens · 1m 2s)
  (ctrl+o to expand)

⏺ Aquí está el mapeo completo del flujo de análisis de reglas de negocio, de punta a
  punta:

  ---
  Flujo Completo: Análisis de Reglas de Negocio

  FASE 1 — Frontend: Trigger del Análisis

  Archivo: frontend/src/components/workflow/RunView.tsx (~línea 713)

  1. El usuario hace clic en "Analizar"  → handleAnalyze()
  2. Validaciones:
    - Verifica que existan reglas de negocio configuradas (si no, muestra toast de error)
    - Recolecta datos extraídos de documentos con status EXTRACTED
  3. Limpia resultados previos: analysisResults: []
  4. Activa estado de carga: setAnalyzing(true)
  5. POST a /{industry}/{process}/analyze-stream con body:
  { "rules": [BusinessRule[]], "extracted_data": { "doc_key": { fields } } }

  ---
  FASE 2 — Backend: Recepción y Enrutamiento

  Archivo: backend/src/api/routes/analysis.py (~línea 83)

  1. FastAPI recibe POST /{industry}/{process}/analyze-stream
  2. Valida el body contra AnalysisRequest (Pydantic)
  3. Busca configuración del proceso via get_config(industry, process) en el registry
  4. Filtra solo reglas activas (isActive == True)
  5. Retorna StreamingResponse con media_type="text/event-stream"

  ---
  FASE 3 — Backend: Evaluación Concurrente de Reglas

  Archivo: backend/src/api/services/_shared/analyser.py (~línea 203)

  analyze_rules_stream() → Generador async que:

  Para CADA regla (en paralelo con asyncio.as_completed):

  3a. Inyección de Knowledge Base

  Archivo: backend/src/api/services/_shared/kb_service.py (~línea 304)

  - Si la regla tiene kb_ids[]:
    - Docs pequeños (<20K chars): se inyectan completos como markdown
    - Docs grandes (≥20K chars): se hace búsqueda semántica:
        - Chunking (1,500 chars, 200 overlap; Excel: 100 rows/chunk)
      - Embedding con gemini-embedding-001
      - Cosine similarity → Top 3 chunks (similitud ≥ 0.80, máx 4,000 chars)
    - Se prepende como ## CONTEXTO DE REFERENCIA al prompt

  3b. Evaluación con LLM

  Archivo: backend/src/api/services/_shared/analyser.py (~línea 131)

  1. Resolución de templates: {{today}}, {{current_year}}, {{current_month}}
  2. Limpieza de sintaxis interna: @recipe.medications → "el campo 'medications' del
  documento 'recipe'"
  3. Construcción del prompt con instrucciones detalladas:
    - Datos extraídos como JSON
    - Regla a evaluar (nombre + lógica)
    - Instrucciones: responder en español, no usar paths técnicos, evaluar listas/arrays
  4. Ejecución LLM con retry (3 intentos, backoff exponencial):
    - Modelo: gemini-2.5-flash via Agno Agent
    - Schema de salida: RuleEvaluation (Pydantic)
  5. Post-procesamiento: fix de acentos (bug de Gemini), parseo de structured_data_json

  3c. Streaming del Resultado

  - Cada regla completada se emite inmediatamente como SSE:
  data: {"rule_id":"...", "rule_name":"...", "is_passed":true/false, "reasoning":"...",
  "structured_data":{...}}\n\n
  - El orden no es determinístico (la primera regla que termine se envía primero)
  - Si una regla falla, se envía error inline sin romper el stream

  ---
  FASE 4 — Frontend: Consumo del Stream

  Archivo: frontend/src/components/workflow/RunView.tsx (~línea 753)

  1. Lee con response.body.getReader() + TextDecoder (UTF-8 streaming)
  2. Bufferea mensajes incompletos, split por \n\n
  3. Parsea cada data: {JSON} → RuleEvaluationResult
  4. Acumula resultados progresivamente en case.analysisResults (spread operator)
  5. Actualiza timestamp en cada resultado parcial
  6. Errores de parseo se loguean a consola sin romper el stream

  ---
  FASE 5 — Frontend: Renderizado de Resultados

  Archivo: frontend/src/components/workflow/RuleResultCard.tsx

  1. AnalysisResultsPanel muestra:
    - Barra resumen con conteo passed/failed
    - Pivot table agregada (si ≥2 reglas tienen datos items_status)
    - Cards individuales por regla (RuleResultCard)
  2. Cada RuleResultCard es expandible y muestra:
    - Badge (passed/failed/error)
    - Reasoning en español
    - Datos estructurados según tipo:
        - two_lists → listas cubierto/no cubierto
      - items_status → badges por ítem
      - metric → valor único
      - table → tabla multi-columna

  ---
  FASE 6 — Persistencia

  - Al completar el stream, handleSaveCase(updatedCase) guarda el caso completo en
  IndexedDB
  - setAnalyzing(false) en el finally

  ---
  Diagrama Resumen

  ┌─────────────────────────────────────────────────────────────────┐
  │  FRONTEND                                                        │
  │                                                                  │
  │  Click "Analizar" → handleAnalyze()                              │
  │       │                                                          │
  │       ├─ Validar reglas + datos extraídos                        │
  │       ├─ POST /analyze-stream { rules[], extracted_data }        │
  │       │                                                          │
  │       ▼                                                          │
  │  ReadableStream reader ◄─── SSE data: {result}\n\n               │
  │       │                                                          │
  │       ├─ Acumula en analysisResults[] (progresivo)               │
  │       ├─ Re-render AnalysisResultsPanel                          │
  │       └─ Al terminar → saveCase() a IndexedDB                   │
  └───────────────────────┬─────────────────────────────────────────┘
                          │ HTTP POST + SSE Stream
  ┌───────────────────────▼─────────────────────────────────────────┐
  │  BACKEND (FastAPI)                                               │
  │                                                                  │
  │  analysis.py → Validar + filtrar reglas activas                  │
  │       │                                                          │
  │       ▼                                                          │
  │  analyser.py → analyze_rules_stream()                            │
  │       │                                                          │
  │       ├─ Para CADA regla (asyncio paralelo):                     │
  │       │   ├─ kb_service.py → Inyectar KB context                 │
  │       │   │   ├─ Doc pequeño → verbatim                          │
  │       │   │   └─ Doc grande → embed + semantic search (top 3)    │
  │       │   │                                                      │
  │       │   ├─ Resolver templates ({{today}}, etc.)                │
  │       │   ├─ Limpiar sintaxis (@doc.field → texto natural)       │
  │       │   ├─ Construir prompt completo                           │
  │       │   ├─ LLM: Gemini 2.5 Flash (3 retries)                  │
  │       │   │   └─ → RuleEvaluation(is_passed, reasoning, data)   │
  │       │   └─ yield SSE result                                    │
  │       │                                                          │
  │       └─ Stream termina cuando todas las reglas completaron      │
  └─────────────────────────────────────────────────────────────────┘

  Constantes Clave

  ┌───────────────┬────────────────────────────────┬────────────────────────────────┐
  │    Config     │             Valor              │           Propósito            │
  ├───────────────┼────────────────────────────────┼────────────────────────────────┤
  │ LLM Model     │ gemini-2.5-flash               │ Evaluación rápida y económica  │
  ├───────────────┼────────────────────────────────┼────────────────────────────────┤
  │ Retry         │ 3 intentos (exponential        │ Tolerancia a fallos            │
  │               │ backoff)                       │ transitorios                   │
  ├───────────────┼────────────────────────────────┼────────────────────────────────┤
  │ Chunk size    │ 1,500 chars / 200 overlap      │ Balance contexto vs tokens     │
  ├───────────────┼────────────────────────────────┼────────────────────────────────┤
  │ Top-K chunks  │ 3                              │ Chunks más relevantes del KB   │
  ├───────────────┼────────────────────────────────┼────────────────────────────────┤
  │ Min           │ 0.80                           │ Umbral alto para evitar ruido  │
  │ similarity    │                                │                                │
  ├───────────────┼────────────────────────────────┼────────────────────────────────┤
  │ Max KB chars  │ 4,000                          │ Límite de inyección al prompt  │
  ├───────────────┼────────────────────────────────┼────────────────────────────────┤
  │ Embed workers │ 10 threads                     │ Paralelismo en embedding       │
  └───────────────┴────────────────────────────────┴────────────────────────────────┘

