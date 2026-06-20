# Frontend Updates — Migración a Nuevo Backend

> Cambios necesarios en el frontend (`frontend/`) para conectar con el nuevo backend (`backend/`) y eliminar localStorage como almacenamiento de datos de negocio.

---

## Principio General

**Antes:** Frontend es "dueño" de los datos (localStorage) y backend solo procesa.
**Después:** Backend es "dueño" de los datos (PostgreSQL) y frontend es un cliente que lee/escribe vía API.

---

## Bloque 1: Auth + Multi-tenancy

> El frontend debe autenticarse y enviar tenant en cada request.

### Cambios en `src/lib/api.ts`

```typescript
// Nuevo: cliente API con auth + tenant
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function apiFetch(path: string, options: RequestInit = {}) {
  const token = getAccessToken(); // desde cookie o memoria
  const tenant = getCurrentTenant(); // slug del tenant activo
  const isFormData = options.body instanceof FormData;

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      // No Content-Type para FormData — el browser lo pone con boundary
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      "Authorization": `Bearer ${token}`,
      "X-Tenant": tenant,
      ...options.headers,
    },
  });

  if (res.status === 401) {
    // Refresh token o redirect a login
    await refreshToken();
    return apiFetch(path, options); // retry
  }

  if (!res.ok) throw new ApiError(res.status, await res.json());
  return res.json();
}

// Variante para endpoints SSE (analyze-stream)
// No parsea JSON — retorna el Response raw para leer el stream
async function apiFetchStream(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getAccessToken();
  const tenant = getCurrentTenant();

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
      "X-Tenant": tenant,
      ...options.headers,
    },
  });

  if (res.status === 401) {
    await refreshToken();
    return apiFetchStream(path, options); // retry
  }

  if (!res.ok) throw new ApiError(res.status, await res.json());
  return res; // raw Response — caller reads via res.body (ReadableStream)
}
```

### Nuevas páginas

- **`/login`** — Login con email/password + Google OAuth
- **`/tenant-select`** — Seleccionar tenant activo (si user tiene múltiples)

### Nuevas dependencias

- Cookie/token management para JWT
- Google OAuth flow (redirect)

---

## Bloque 2: Eliminar `workflowStorage.ts`

> Reemplazar TODA la lógica de localStorage por llamadas API.

### Archivo a eliminar

- `src/lib/workflowStorage.ts` — **eliminar completamente**

### Reemplazos

| Función actual (localStorage) | Nuevo (API call) |
|-------------------------------|------------------|
| `getWorkflows(type)` | `GET /v1/extraction/workflows` |
| `saveWorkflow(type, workflow)` | `POST/PUT /v1/extraction/workflows` |
| `deleteWorkflow(type, id)` | `DELETE /v1/extraction/workflows/{id}` |
| `getRunState(workflowId)` | `GET /v1/extraction/workflows/{id}/cases` |
| `saveCase(workflowId, case)` | `POST /v1/extraction/workflows/{workflowId}/cases` (crear) / `PUT /v1/extraction/cases/{id}` (actualizar) |
| `deleteCase(workflowId, caseId)` | `DELETE /v1/extraction/cases/{id}` |
| `setLastActiveCase(wfId, caseId)` | Campo en localStorage (UI pref, OK mantener) |

### Usar TanStack Query

TanStack Query ya está instalado (se usa en Admin). Extender su uso a todo:

```typescript
// hooks/useWorkflows.ts
export function useWorkflows(processId: string) {
  return useQuery({
    queryKey: ["workflows", processId],
    queryFn: () => apiFetch(`/v1/extraction/workflows?processId=${processId}`),
  });
}

export function useCreateWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateWorkflowRequest) =>
      apiFetch("/v1/extraction/workflows", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workflows"] }),
  });
}

// hooks/useCases.ts
export function useCases(workflowId: string) {
  return useQuery({
    queryKey: ["cases", workflowId],
    queryFn: () => apiFetch(`/v1/extraction/workflows/${workflowId}/cases`),
  });
}

export function useCase(caseId: string) {
  return useQuery({
    queryKey: ["case", caseId],
    queryFn: () => apiFetch(`/v1/extraction/cases/${caseId}`),
  });
}
```

---

## Bloque 3: Eliminar base64 en documentos

> Los archivos ya no se almacenan como base64 en el frontend. Se suben al backend y se referencian por `fileId`.

### Cambio en `CaseDocument`

```typescript
// ANTES
interface CaseDocument {
  fileDataUrl: string;      // base64 completo (MB!)
  previewDataUrl: string;   // base64 thumbnail
  // ...
}

// DESPUÉS
interface CaseDocument {
  fileId: string | null;        // UUID del archivo en backend
  fileUrl: string | null;       // Presigned URL (temporal, para preview)
  thumbnailUrl: string | null;  // Presigned URL del thumbnail
  // ... resto igual
}
```

### Cambio en upload flow (`RunView.tsx`)

```typescript
// ANTES: convertir a base64 y guardar en state
const dataUrl = await fileToDataUrl(file);
doc.fileDataUrl = dataUrl;
saveCase(...); // → localStorage

// DESPUÉS: subir a backend y guardar referencia
const formData = new FormData();
formData.append("file", file);
const { fileId, fileUrl } = await apiFetch("/v1/files/upload", {
  method: "POST",
  body: formData, // apiFetch detecta FormData y omite Content-Type automáticamente
});

// Asociar archivo al documento del caso
await apiFetch(`/v1/extraction/documents/${docId}/upload`, {
  method: "POST",
  body: JSON.stringify({ fileId }),
});

// Thumbnail: pedir presigned URL al backend o generar client-side solo para preview temporal
```

### Impacto en localStorage

- Ya no crece a MB
- `fileDataUrl` y `previewDataUrl` se eliminan del modelo
- Se mantiene solo `lastActiveCaseId` como preferencia UI (OK en localStorage)

---

## Bloque 4: Extracción vía nueva API

> Los endpoints de extracción cambian de `/{industry}/{process}/extract` a `/v1/extraction/cases/{id}/extract`.

### Cambio en `RunView.tsx`

```typescript
// ANTES
const { job_id } = await fetch(`${API}/${industry}/${process}/extract`, {
  method: "POST",
  body: JSON.stringify({
    documents: docs.map(d => ({ docTypeKey: d.docTypeKey, fileDataUrl: d.fileDataUrl })),
    provider, perDocSchema, kbDocumentIds, perDocKbIds,
  }),
});

// DESPUÉS
const { jobId } = await apiFetch(`/v1/extraction/cases/${caseId}/extract`, {
  method: "POST",
  body: JSON.stringify({
    provider,
    structuringModel,
    llmModel,
  }),
});
// Documentos y schemas ya están en el backend (guardados al crear el caso)
// No se envía base64 — el backend ya tiene los file_ids
```

### Cambio en polling

```typescript
// ANTES
const status = await fetch(`${API}/${industry}/${process}/extract-status/${jobId}`);

// DESPUÉS — opción A: polling
const status = await apiFetch(`/v1/extraction/jobs/${jobId}/status`);

// DESPUÉS — opción B: Temporal query (si se expone)
// WebSocket con updates en tiempo real desde Temporal signals
```

---

## Bloque 5: Análisis vía nueva API

### Cambio en `RunView.tsx`

```typescript
// ANTES
const response = await fetch(`${API}/${industry}/${process}/analyze-stream`, {
  method: "POST",
  body: JSON.stringify({ rules, extracted_data }),
});
// Leer SSE stream...

// DESPUÉS — usar apiFetchStream (no parsea JSON, retorna Response raw)
const response = await apiFetchStream(`/v1/extraction/cases/${caseId}/analyze-stream`, {
  method: "POST",
  // No se envía extracted_data — el backend ya lo tiene en DB
  // Solo se envía config opcional (ej: qué reglas ejecutar)
  body: JSON.stringify({ ruleIds: activeRuleIds }),
});
// Leer SSE stream desde response.body (ReadableStream)
```

### Resultados persistentes

```typescript
// ANTES: resultados se guardan en localStorage
case.analysisResults = results;
saveCase(...);

// DESPUÉS: resultados ya están en DB, solo invalidar cache
queryClient.invalidateQueries({ queryKey: ["case", caseId] });
// El case del backend ya incluye analysisResults
```

---

## Bloque 6: Admin actualizado

> Admin ya usa API. Solo cambiar base URL y agregar auth headers.

### Cambios mínimos en `src/pages/Admin.tsx`

```typescript
// ANTES
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8100";

// DESPUÉS
// Usar el apiFetch centralizado que ya tiene auth + tenant
// Los endpoints cambian:
//   /admin/industries → /v1/industries
//   /admin/processes  → /v1/processes
```

### Cambios en `src/lib/api.ts`

```typescript
// ANTES
export async function fetchIndustries() {
  const res = await fetch(`${API_URL}/admin/industries`);
  return res.json();
}

// DESPUÉS
export async function fetchIndustries() {
  return apiFetch("/v1/industries");
}
```

---

## Bloque 7: Types actualizados

### Cambios en `src/types/workflow.ts`

```typescript
// Eliminar WorkflowType enum hardcodeado
// Ahora es dinámico, viene del process.workflow_type

// Agregar UUID a todas las entidades
interface WorkflowDefinition {
  uuid: string;              // nuevo: UUID del backend
  processId: string;         // nuevo: reemplaza workflowType
  name: string;
  selectedDocTypes: string[];
  perDocSchema: Record<string, SchemaObject>;
  businessRules?: BusinessRule[];
  kbDocumentIds?: string[];
  perDocKbIds?: Record<string, string[]>;
  structuringModel?: string;
  llmModel?: string;
  createdAt: string;
  updatedAt: string;
}

interface WorkflowCase {
  uuid: string;              // nuevo
  workflowId: string;        // ahora es UUID, no el string generado
  name: string;
  status: CaseStatus;
  lastOcrProvider?: OcrProvider;
  documents: Record<string, CaseDocument>;
  analysisResults?: RuleEvaluationResult[];
  pendingJobId?: string;
  createdAt: string;
  updatedAt: string;
}

interface CaseDocument {
  uuid: string;              // nuevo
  caseId: string;
  docTypeKey: string;
  fileName?: string;
  fileId?: string;           // nuevo: reemplaza fileDataUrl
  fileUrl?: string;          // nuevo: presigned URL para preview
  thumbnailUrl?: string;     // nuevo: reemplaza previewDataUrl
  status: DocStatus;
  extractedFields: Record<string, unknown>;
  extractedText?: string;
  ocrProviderUsed?: OcrProvider;
  confidence?: number;
  includeInExtraction?: boolean;
  kbContextUsed?: KBContextInfo[];
  updatedAt: string;
}

// Eliminar: fileDataUrl, previewDataUrl
// Eliminar: WorkflowRunState (ya no hay wrapper de localStorage)
```

---

## Bloque 8: Routing actualizado

### Cambios en `src/App.tsx`

```typescript
// Agregar rutas de auth
<Route path="/login" element={<LoginPage />} />
<Route path="/tenant-select" element={<TenantSelectPage />} />

// Proteger rutas existentes con AuthGuard
<Route path="/" element={<AuthGuard><DynamicLanding /></AuthGuard>} />
<Route path="/admin" element={<AuthGuard permission="industries:write"><Admin /></AuthGuard>} />
// ...
```

### AuthGuard component

```typescript
function AuthGuard({ children, permission }: { children: ReactNode; permission?: string }) {
  const { isAuthenticated, hasPermission } = useAuth();

  if (!isAuthenticated) return <Navigate to="/login" />;
  if (permission && !hasPermission(permission)) return <Forbidden />;
  return children;
}
```

---

## Resumen de Archivos Afectados

### Eliminar
- `src/lib/workflowStorage.ts`

### Crear
- `src/lib/apiFetch.ts` — cliente HTTP con auth + tenant (`apiFetch` para JSON, `apiFetchStream` para SSE)
- `src/hooks/useAuth.ts` — auth state + token management
- `src/hooks/useWorkflows.ts` — TanStack Query para workflows
- `src/hooks/useCases.ts` — TanStack Query para cases
- `src/hooks/useDocuments.ts` — TanStack Query para documents
- `src/pages/LoginPage.tsx`
- `src/pages/TenantSelectPage.tsx`
- `src/components/AuthGuard.tsx`

### Modificar
- `src/lib/api.ts` — usar `apiFetch`, actualizar endpoints
- `src/types/workflow.ts` — agregar UUIDs, eliminar base64 fields
- `src/App.tsx` — agregar rutas de auth, proteger rutas
- `src/pages/Admin.tsx` — usar `apiFetch`
- `src/components/WorkflowRunner.tsx` — usar hooks TanStack Query
- `src/components/workflow/RunView.tsx` — eliminar base64, usar fileId, nuevos endpoints
- `src/components/BusinessRulesConfig.tsx` — persistir vía API
- `src/components/workflow/KnowledgeBaseSection.tsx` — nuevo endpoint KB
- `src/pages/DynamicLanding.tsx` — usar `apiFetch`
- `src/pages/workflows/IndustryProcesses.tsx` — usar `apiFetch`
- `src/pages/workflows/DynamicWorkflow.tsx` — usar hooks, eliminar localStorage

---

## Orden de Ejecución

```
Bloque 1: Auth + Multi-tenancy    ← primero (todo depende de esto)
Bloque 7: Types actualizados      ← definir contratos antes de implementar
Bloque 2: Eliminar workflowStorage ← cambio más grande
Bloque 6: Admin actualizado        ← rápido, ya usa API
Bloque 3: Eliminar base64         ← depende de Bloque 2
Bloque 4: Extracción nueva API    ← depende de Bloque 2 + 3
Bloque 5: Análisis nueva API      ← depende de Bloque 4
Bloque 8: Routing + AuthGuard     ← puede ir en paralelo con 2-5
```
