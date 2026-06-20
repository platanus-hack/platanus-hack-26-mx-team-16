export const queryKeys = {
  pipelines: {
    // Catálogo de fases (GET /v1/pipelines/phase-catalog) — sigue siendo
    // tenant-level (ADR 0002 lo dejó intacto).
    catalog: ["pipelines", "phase-catalog"] as const,
    // ── Pipeline propiedad 1:1 del workflow (ADR 0002) ──
    // El pipeline ya no tiene UUID propio en el FE: se direcciona por workflow.
    byWorkflow: (workflowId: string) =>
      ["workflows", workflowId, "pipeline"] as const,
    versions: (workflowId: string) =>
      ["workflows", workflowId, "pipeline", "versions"] as const,
    version: (workflowId: string, version: number | null) =>
      ["workflows", workflowId, "pipeline", "versions", version] as const,
  },
  workflows: {
    all: ["workflows"] as const,
    detail: (uuid: string) => ["workflows", uuid] as const,
    events: (uuid: string, deliveryStatus?: string) =>
      ["workflows", uuid, "events", deliveryStatus ?? "all"] as const,
  },
  permissions: {
    all: (workflowUuid: string) =>
      ["workflow-permissions", workflowUuid] as const,
    assignableUsers: (workflowUuid: string) =>
      ["workflow-permissions", workflowUuid, "assignable-users"] as const,
  },
  webhookDestinations: {
    all: (workflowUuid: string) =>
      ["webhook-destinations", workflowUuid] as const,
    detail: (workflowUuid: string, destinationId: string) =>
      ["webhook-destinations", workflowUuid, destinationId] as const,
    events: (
      workflowUuid: string,
      destinationId: string,
      deliveryStatus?: string
    ) =>
      [
        "webhook-destinations",
        workflowUuid,
        destinationId,
        "events",
        deliveryStatus ?? "all",
      ] as const,
  },
  cases: {
    all: (workflowUuid: string) => ["cases", workflowUuid] as const,
    detail: (workflowUuid: string, caseUuid: string) =>
      ["cases", workflowUuid, caseUuid] as const,
    // Sin `filters` la key debe ser un PREFIJO real de la key con filtros
    // (gotcha E1): un 4º elemento `undefined` impide que invalidate/
    // refetchQueries matcheen las queries vivas con filtros.
    paginated: (workflowUuid: string, filters?: object) =>
      filters === undefined
        ? (["cases", workflowUuid, "paginated"] as const)
        : (["cases", workflowUuid, "paginated", filters] as const),
    completeness: (workflowUuid: string, caseUuid: string) =>
      ["cases", workflowUuid, caseUuid, "completeness"] as const,
    // E5 · fan-out: lista de children de un caso padre.
    children: (workflowUuid: string, caseUuid: string) =>
      ["cases", workflowUuid, caseUuid, "children"] as const,
  },
  humanTasks: {
    all: ["human-tasks"] as const,
    list: (audience?: string) =>
      ["human-tasks", audience ?? null] as const,
  },
  // E5 · consola staff (/staff — superficie /staff/v1 vía BFF /api/staff/*).
  // Mismo gotcha de prefijos que `cases.paginated`: sin filtros la key es un
  // PREFIJO real de la key con filtros para que invalidate matchee.
  staff: {
    all: ["staff"] as const,
    tasks: (filters?: object) =>
      filters === undefined
        ? (["staff", "tasks"] as const)
        : (["staff", "tasks", filters] as const),
    case: (caseId: string) => ["staff", "cases", caseId] as const,
    audit: (filters?: object) =>
      filters === undefined
        ? (["staff", "audit"] as const)
        : (["staff", "audit", filters] as const),
    metrics: (filters?: object) =>
      filters === undefined
        ? (["staff", "metrics"] as const)
        : (["staff", "metrics", filters] as const),
  },
  documents: {
    all: (workflowUuid: string) => ["documents", workflowUuid] as const,
    detail: (documentUuid: string) =>
      ["documents", "detail", documentUuid] as const,
    workflowDocument: (documentId: string) =>
      ["workflow-documents", documentId] as const,
  },
  processingJobs: {
    all: (workflowUuid: string) => ["processing-jobs", workflowUuid] as const,
    // Sin `filters` la key debe ser un PREFIJO real de la key con filtros:
    // un 4º elemento `undefined` hace que invalidate/refetchQueries nunca
    // matcheen la query viva (TanStack compara posición a posición) y la
    // lista jamás se refresque al terminar un procesamiento.
    paginated: (workflowUuid: string, filters?: object) =>
      filters === undefined
        ? (["processingJobs", workflowUuid, "paginated"] as const)
        : (["processingJobs", workflowUuid, "paginated", filters] as const),
    // Per-phase execution timeline of one job (Ejecuciones split detail).
    phases: (workflowUuid: string, processingJobId: string) =>
      ["processing-jobs", workflowUuid, processingJobId, "phases"] as const,
  },
  documentTypes: {
    all: (workflowUuid?: string) =>
      workflowUuid
        ? ["document-types", workflowUuid]
        : (["document-types"] as const),
    detail: (uuid: string) => ["document-types", "detail", uuid] as const,
  },
  members: {
    all: ["members"] as const,
  },
  invitations: {
    pending: ["invitations", "pending"] as const,
  },
  industries: {
    all: ["industries"] as const,
  },
  roles: {
    all: ["roles"] as const,
    detail: (uuid: string) => ["roles", uuid] as const,
  },
  settings: {
    all: ["settings"] as const,
  },
  billing: {
    all: ["billing"] as const,
  },
  usage: {
    summary: ["usage", "summary"] as const,
    records: (filters?: object) => ["usage", "records", filters] as const,
  },
  knowledge: {
    all: ["knowledge"] as const,
    byWorkflow: (workflowId: string) => ["knowledge", workflowId] as const,
  },
  knowledgeBases: {
    all: ["knowledge-bases"] as const,
  },
  dashboard: {
    overview: (params?: object) => ["dashboard", "overview", params] as const,
    processing: (params?: object) =>
      ["dashboard", "processing", params] as const,
    // Section prefix used by the SSE event handler to invalidate just one tab
    // — `invalidateQueries({ queryKey: ["dashboard", "overview"] })` performs
    // a prefix match and catches every params variant.
    section: (section: "overview" | "processing") =>
      ["dashboard", section] as const,
  },
};
