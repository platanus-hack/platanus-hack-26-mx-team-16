// sample-data.ts — example catalog (7 stages / 15 phases) + defaults.
// Replace with your own data source; the editor only needs `Stage[]`.
import type { Stage, PipelineState } from "./types";

export const SAMPLE_STAGES: Stage[] = [
  {
    id: "extraccion", num: "1", name: "Extracción", type: "group", scope: "document",
    accent: "teal", tag: "Grupo · cadena de dependencia", layout: "stack",
    summary: "La base de todo workflow con archivo. Cada fase necesita la salida de la anterior.",
    removable: false, icon: "classify_pages",
    phases: [
      { kind: "ingest", label: "Ingest", icon: "ingest", scope: "document",
        summary: "Recibe el archivo y normaliza el formato de entrada.",
        config: [
          { key: "formats", type: "select", label: "Formatos aceptados", value: "PDF, imagen, email", options: ["PDF, imagen, email", "Solo PDF", "Todos"] },
          { key: "maxmb", type: "number", label: "Tamaño máx.", value: 50, unit: "MB" },
        ] },
      { kind: "extract_text", label: "Extract text", icon: "extract_text", scope: "document",
        summary: "OCR y extracción de la capa de texto del documento.",
        config: [
          { key: "engine", type: "select", label: "Motor OCR", value: "Automático", options: ["Automático", "Tesseract", "Cloud OCR"] },
          { key: "langs", type: "text", label: "Idiomas", value: "es, en" },
        ] },
      { kind: "classify_pages", label: "Classify pages", icon: "classify_pages", scope: "document",
        summary: "Asigna un tipo de documento a cada página. Sin clase no se sabe qué extraer.",
        config: [
          { key: "model", type: "select", label: "Modelo", value: "doc-classifier-v3", options: ["doc-classifier-v3", "doc-classifier-v2"] },
          { key: "thr", type: "slider", label: "Umbral de confianza", value: 0.8, min: 0.5, max: 1, step: 0.01 },
        ] },
      { kind: "extract_fields", label: "Extract fields", icon: "extract_fields", scope: "document",
        summary: "Extrae los campos estructurados según el esquema del tipo de documento.",
        config: [
          { key: "schema", type: "select", label: "Esquema", value: "Factura · v4", options: ["Factura · v4", "Recibo · v2", "Contrato · v1"] },
          { key: "mode", type: "segmented", label: "Modo", value: "LLM", options: ["LLM", "Plantilla"] },
        ] },
      { kind: "assess", label: "Assess", icon: "assess", scope: "document", optional: true,
        summary: "Evalúa la calidad de la extracción antes de continuar. Toggle interno opcional.",
        config: [
          { key: "metrics", type: "select", label: "Métrica", value: "Cobertura + confianza", options: ["Cobertura + confianza", "Solo cobertura"] },
        ] },
      { kind: "validate_extraction", label: "Validate", icon: "validate_extraction", scope: "document", optional: true,
        summary: "Aplica reglas de validación sobre los campos extraídos. Toggle interno opcional.",
        config: [
          { key: "ruleset", type: "select", label: "Ruleset", value: "Reglas fiscales ES", options: ["Reglas fiscales ES", "Reglas básicas"] },
        ] },
      { kind: "finalize", label: "Finalize", icon: "finalize", scope: "document",
        summary: "Cierra el documento si es un caso straight-through (sin pasos case-scope).",
        config: [] },
    ],
  },
  {
    id: "completitud", num: "2", name: "Completitud", type: "solo", scope: "case",
    accent: "amber", tag: "Fase suelta · opcional", layout: "stack",
    summary: "Primera fase case-scope. Convierte el caso en un expediente: espera el conjunto de documentos.",
    removable: true, icon: "await_documents",
    phases: [
      { kind: "await_documents", label: "Await documents", icon: "await_documents", scope: "case",
        summary: "Retiene el caso en RECEIVING hasta reunir todos los documentos requeridos.",
        config: [
          { key: "required", type: "text", label: "Documentos requeridos", value: "DNI, nómina, contrato" },
          { key: "timeout", type: "number", label: "Timeout", value: 72, unit: "h" },
        ] },
    ],
  },
  {
    id: "calidad", num: "3", name: "Control de calidad", type: "group", scope: "case",
    accent: "gold", tag: "Grupo · disparo compartido", layout: "branch",
    summary: "El gate calcula señales de confianza; las otras dos fases se disparan vía «when» sobre ellas.",
    removable: true, toggleable: true, icon: "confidence_gate",
    phases: [
      { kind: "confidence_gate", label: "Confidence gate", icon: "confidence_gate", scope: "case", role: "gate",
        summary: "Calcula las señales gate.clarify y gate.review a partir de la confianza de la extracción.",
        config: [
          { key: "clarify", type: "slider", label: "Umbral clarify", value: 0.6, min: 0, max: 1, step: 0.01 },
          { key: "review", type: "slider", label: "Umbral review", value: 0.85, min: 0, max: 1, step: 0.01 },
        ] },
      { kind: "await_clarification", label: "Await clarification", icon: "await_clarification", scope: "case",
        when: "gate.clarify > 0", branch: true,
        summary: "Solicita aclaración al remitente cuando hay campos por debajo del umbral.",
        config: [
          { key: "channel", type: "select", label: "Canal", value: "Email", options: ["Email", "SMS", "Portal"] },
          { key: "timeout", type: "number", label: "Timeout", value: 48, unit: "h" },
        ] },
      { kind: "review_gate", label: "Review gate", icon: "review_gate", scope: "case",
        when: "gate.review > 0", branch: true, sameKind: "human_review",
        summary: "Cola de revisión humana para los casos de baja confianza (trigger = \"gate\").",
        config: [
          { key: "queue", type: "select", label: "Cola", value: "Revisión nivel 1", options: ["Revisión nivel 1", "Revisión especializada"] },
          { key: "sla", type: "number", label: "SLA", value: 4, unit: "h" },
        ] },
    ],
  },
  {
    id: "enriquecimiento", num: "4", name: "Enriquecimiento", type: "solo", scope: "case",
    accent: "violet", tag: "Fase suelta · independiente", layout: "stack",
    summary: "Independiente. Llama a herramientas HTTP firmadas para enriquecer los datos del caso.",
    removable: true, icon: "enrich",
    phases: [
      { kind: "enrich", label: "Enrich", icon: "enrich", scope: "case",
        summary: "Ejecuta tools HTTP firmadas contra servicios externos.",
        config: [
          { key: "endpoint", type: "text", label: "Endpoint", value: "https://api.interno/enrich" },
          { key: "auth", type: "select", label: "Autenticación", value: "HMAC firmado", options: ["HMAC firmado", "OAuth2"] },
          { key: "timeout", type: "number", label: "Timeout", value: 10, unit: "s" },
        ] },
    ],
  },
  {
    id: "analisis", num: "5", name: "Análisis", type: "solo", scope: "case",
    accent: "blue", tag: "Fase suelta · independiente", layout: "stack",
    summary: "Independiente. Ejecuta reglas de negocio sobre los datos consolidados del caso.",
    removable: true, icon: "analyze",
    phases: [
      { kind: "analyze", label: "Analyze", icon: "analyze", scope: "case",
        summary: "Aplica el motor de reglas de negocio y produce un veredicto.",
        config: [
          { key: "ruleset", type: "select", label: "Ruleset", value: "Riesgo crédito v2", options: ["Riesgo crédito v2", "Cumplimiento KYC"] },
          { key: "onfail", type: "segmented", label: "Si falla", value: "A revisión", options: ["A revisión", "Rechazar"] },
        ] },
    ],
  },
  {
    id: "aprobacion", num: "6", name: "Aprobación", type: "solo", scope: "case",
    accent: "rose", tag: "Fase suelta · independiente", layout: "stack",
    summary: "Independiente. Aprobación humana final L1/L2 (mismo kind human_review, sin trigger \"gate\").",
    removable: true, icon: "approval",
    phases: [
      { kind: "approval", label: "Approval", icon: "approval", scope: "case", sameKind: "human_review",
        summary: "Aprobación humana final. Mismo kind que review_gate pero sin trigger = \"gate\".",
        config: [
          { key: "trigger", type: "segmented", label: "Disparo", value: "Por excepción", options: ["Obligatorio", "Por excepción"] },
          { key: "levels", type: "segmented", label: "Niveles", value: "L1 + L2", options: ["Solo L1", "L1 + L2"] },
        ] },
    ],
  },
  {
    id: "salida", num: "7", name: "Salida", type: "group", scope: "case",
    accent: "teal", tag: "Grupo · par atómico", layout: "stack",
    summary: "Par atómico. output proyecta el resultado; deliver lo entrega y cierra el caso. Van juntas siempre.",
    removable: false, atomic: true, icon: "deliver",
    phases: [
      { kind: "output", label: "Output", icon: "output", scope: "case",
        summary: "Proyecta y sintetiza el resultado final del caso.",
        config: [
          { key: "format", type: "select", label: "Formato", value: "JSON estructurado", options: ["JSON estructurado", "CSV", "PDF + JSON"] },
        ] },
      { kind: "deliver", label: "Deliver", icon: "deliver", scope: "case",
        summary: "Entrega el resultado al destino y cierra el caso.",
        config: [
          { key: "dest", type: "select", label: "Destino", value: "Webhook", options: ["Webhook", "Email", "Almacenamiento"] },
          { key: "retries", type: "number", label: "Reintentos", value: 3, unit: "" },
        ] },
    ],
  },
];

export const SAMPLE_INITIAL_STATE: PipelineState = {
  order: ["extraccion", "completitud", "calidad", "enriquecimiento", "analisis", "aprobacion", "salida"],
  collapsed: { extraccion: false, calidad: false, salida: false },
  optional: { assess: true, validate_extraction: true },
  config: {},
};

/** Stage ids that can be inserted from the "+" menu (removable optionals). */
export const SAMPLE_ADDABLE = ["completitud", "calidad", "enriquecimiento", "analisis", "aprobacion"];
