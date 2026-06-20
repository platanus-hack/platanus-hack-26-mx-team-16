---
feature: tenants
type: plan
status: implemented
coverage: 80
audited: 2026-06-16
---

# Spec: Tenant Switcher (carga de tenants y cambio de tenant)

Este spec describe, paso a paso, cómo replicar el switcher de tenants del sidebar tal como está implementado en `tripto-web`. Está orientado a implementación: indica archivos, contratos, dependencias y orden de creación.

> **Stack asumido:** Next.js (App Router) + TypeScript, Zustand (con `devtools` + `persist`), Axios, Tailwind, shadcn/ui (DropdownMenu, Sidebar, Badge), `lucide-react` para íconos.

---

## 1. Arquitectura general

```
┌──────────────────────────────────────────────────────────────┐
│ Sidebar (AppSidebar)                                          │
│  └── <TenantHead/>                                            │
│        ├── lee  tenant actual          ← useSessionStore()    │
│        └── lee  tenants[] + selectTenant ← useTenantStore()   │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
        useTenantStore (Zustand)
          ├── fetchTenants()  → tenantsRepository.getUserTenants()
          └── selectTenant(t) → tenantsRepository.setCurrentTenant(t.uuid)
                                  └── al éxito: sessionStore.setTenant(t)
                           │
                           ▼
        HttpTenantRepository (Axios)
          ├── GET  /v1/me/tenants
          └── PUT  /v1/me/tenants/{tenantId}
```

**Capas (Clean Architecture):**

- **Domain:** `Tenant`, `TenantStatus`, `TenantFilters`, `TenantRepository` (interfaz), `ErrorFeeback`, `TaskResultResponse`.
- **Infrastructure:** `HttpTenantRepository` (Axios), `domainContext` (DI).
- **Application:** `useTenantStore` (Zustand), `useSessionStore` (Zustand persistido), `useTenants` (hook), `StoreInitializer`.
- **Presentation:** `TenantHead` (componente del sidebar).

---

## 2. Contrato del backend (endpoints requeridos)

El switcher consume **dos** endpoints que viven en el módulo `me` del backend:

### 2.1 `GET /v1/me/tenants`
Lista los tenants del usuario autenticado.

**Query params (opcionales):**
- `status`: `ACTIVE | PENDING | INACTIVE | SUSPENDED`
- `search`: string

**Response:**
```ts
{
  data: Tenant[];
  timestamp: string;
}
```

### 2.2 `PUT /v1/me/tenants/{tenantId}`
Marca el tenant indicado como tenant actual del usuario en backend (afecta el `current_tenant_id` del JWT/sesión en el siguiente request).

**Response:**
```ts
{
  data: { status: 'SUCCESS' | string; completedAt: string };
  datetime: string;
}
```

> **Nota crítica:** El backend resuelve el tenant actual a partir del usuario autenticado. Después de hacer `PUT`, el frontend hace `window.location.reload()` para forzar que todos los requests subsiguientes usen el nuevo `current_tenant_id` del backend (ver §8). El `Authorization` header sigue siendo el mismo access token; no se rota el JWT en el cliente.

---

## 3. Capa de dominio

### 3.1 `Tenant` entity
Archivo: `src/common/domain/entities/Tenant.ts`

```ts
import { TenantStatus } from '@/src/common/domain/enums/tenants';

export interface Tenant {
  uuid: string;
  name: string;
  slug: string;
  timeZone: string;
  countryCode: string;
  currencyCode: string;
  currencySymbol: string;
  logoUrl?: string | null;
  contactEmail?: string | null;
  status: TenantStatus;
  createdAt?: string | null;
  updatedAt?: string | null;
  paymentPermalink?: { linkUrl: string } | null;
}

export function isTenantActive(tenant: Tenant): boolean {
  return tenant.status === TenantStatus.ACTIVE;
}

export const emptyTenant: Tenant = {
  uuid: '', name: '', slug: '', timeZone: '',
  countryCode: '', currencyCode: '', currencySymbol: '',
  status: TenantStatus.ACTIVE,
};
```

### 3.2 `TenantStatus` enum
Archivo: `src/common/domain/enums/tenants.ts`

```ts
export enum TenantStatus {
  ACTIVE = 'ACTIVE',
  PENDING = 'PENDING',
  INACTIVE = 'INACTIVE',
  SUSPENDED = 'SUSPENDED',
}
```

### 3.3 Filtros
Archivo: `src/common/domain/filters/tenant.ts`

```ts
import type { TenantStatus } from '@/src/common/domain/enums/tenants';

export interface TenantFilters {
  status?: TenantStatus;
  search?: string;
}
```

### 3.4 Tipos de respuesta
Archivo: `src/common/domain/responses/tenant.ts`

```ts
import type { Tenant } from '@/src/common/domain/entities/Tenant';

export interface TenantsResponse { data: Tenant[];   timestamp: string; }
export interface TenantResponse  { data: Tenant;     timestamp: string; }
```

Archivo: `src/common/domain/responses/task-result.ts`

```ts
import type { TaskResult } from '@/src/common/domain/entities/common/task-result';

export default interface TaskResultResponse {
  data: TaskResult;
  datetime: string;
}
```

Archivo: `src/common/domain/entities/common/task-result.ts`

```ts
export interface TaskResult {
  status: string;
  completedAt: string;
}

export function isSuccessfulTask(t: TaskResult) {
  return t.status === 'SUCCESS';
}
```

### 3.5 Error type
Archivo: `src/common/domain/errors/ErrorFeeback.ts` *(sí, mantener el typo "Feeback" si se replica el proyecto verbatim)*

```ts
export interface ErrorItem { message: string; code: string; }
export interface ErrorFeeback {
  errors: Array<ErrorItem>;
  validation: object | null;
}

export function isErrorFeedback(obj: unknown): obj is ErrorFeeback {
  return typeof obj === 'object' && obj !== null
    && 'errors' in (obj as Record<string, unknown>)
    && 'validation' in (obj as Record<string, unknown>);
}

export const genericServerError: ErrorFeeback = {
  errors: [{ code: 'client.ServerError', message: 'Something went wrong.' }],
  validation: null,
};
```

### 3.6 Interface del repositorio
Archivo: `src/common/domain/repositories/tenant.ts`

```ts
import type { Tenant } from '@/src/common/domain/entities/Tenant';
import type { ErrorFeeback } from '@/src/common/domain/errors/ErrorFeeback';
import type { TenantFilters } from '@/src/common/domain/filters/tenant';
import type TaskResultResponse from '@/src/common/domain/responses/task-result';

export interface TenantRepository {
  getUserTenants(filters?: TenantFilters): Promise<Tenant[] | ErrorFeeback>;
  setCurrentTenant(tenantId: string): Promise<TaskResultResponse | ErrorFeeback>;
  getTenant(tenantId: string): Promise<Tenant | ErrorFeeback>;
  updateTenant(tenantId: string, formData: FormData): Promise<Tenant | ErrorFeeback>;
}
```

> Para el switcher solo hacen falta `getUserTenants` y `setCurrentTenant`. Los otros dos se incluyen porque el store los reutiliza (`updateTenant` se usa en settings; `getTenant` queda disponible).

---

## 4. Capa de infraestructura

### 4.1 Helper de logo
Archivo: `src/common/utils/tenant-utils.ts`

```ts
const ASSETS_BASE_URL = 'https://assets.<tu-cdn>/<tu-bucket>';

export function getTenantLogoUrl(logoPath: string | null | undefined): string {
  if (!logoPath) return '/images/logo.png';
  if (logoPath.startsWith('http://') || logoPath.startsWith('https://')) {
    return logoPath;
  }
  return `${ASSETS_BASE_URL}/${logoPath}`;
}
```

### 4.2 HttpTenantRepository
Archivo: `src/common/infrastructure/repositories/http-tenant.ts`

Puntos clave verificados contra el código:
- Recibe `AxiosInstance` por constructor.
- Construye query string con `URLSearchParams` solo si vienen filtros.
- En `getUserTenants` mapea cada tenant inyectando `logoUrl: getTenantLogoUrl(tenant.logoUrl)`.
- Captura cualquier error con `handleHttpError(error as AxiosError)` y devuelve un `ErrorFeeback`.

```ts
import type { AxiosError, AxiosInstance } from 'axios';
import type { Tenant } from '@/src/common/domain/entities/Tenant';
import type { ErrorFeeback } from '@/src/common/domain/errors/ErrorFeeback';
import type { TenantFilters } from '@/src/common/domain/filters/tenant';
import type TaskResultResponse from '@/src/common/domain/responses/task-result';
import type { TenantResponse, TenantsResponse } from '@/src/common/domain/responses/tenant';
import type { TenantRepository } from '@/src/common/domain/repositories/tenant';
import { handleHttpError } from '@/src/common/utils/http-error-handler';
import { getTenantLogoUrl } from '@/src/common/utils/tenant-utils';

export class HttpTenantRepository implements TenantRepository {
  constructor(private httpClient: AxiosInstance) {}

  async getUserTenants(filters?: TenantFilters): Promise<Tenant[] | ErrorFeeback> {
    try {
      const params = new URLSearchParams();
      if (filters?.status) params.append('status', filters.status);
      if (filters?.search) params.append('search', filters.search);
      const qs = params.toString();
      const endpoint = `/v1/me/tenants${qs ? `?${qs}` : ''}`;

      const { data } = await this.httpClient.get<TenantsResponse>(endpoint);
      return data.data.map((t) => ({ ...t, logoUrl: getTenantLogoUrl(t.logoUrl) }));
    } catch (error) {
      console.error('Error fetching user tenants:', error);
      return handleHttpError(error as AxiosError);
    }
  }

  async setCurrentTenant(tenantId: string): Promise<TaskResultResponse | ErrorFeeback> {
    try {
      const { data } = await this.httpClient.put<TaskResultResponse>(`/v1/me/tenants/${tenantId}`);
      return data;
    } catch (error) {
      console.error('Error setting current tenant:', error);
      return handleHttpError(error as AxiosError);
    }
  }

  // getTenant + updateTenant: ver §3.6
}
```

### 4.3 DI container
Archivo: `src/common/infrastructure/domain-context.ts`

```ts
import { HttpTenantRepository } from '@/src/common/infrastructure/repositories/http-tenant';
import { authHttp /* AxiosInstance autenticado */ } from '@/src/common/infrastructure/http/client';

export const domainContext = {
  // …otros repos
  tenantsRepository: new HttpTenantRepository(authHttp),
};
```

> El `AxiosInstance` (`authHttp`) debe inyectar el `Authorization: Bearer <accessToken>` automáticamente (se sincroniza con el `useSessionStore` vía `token-store.ts` en el proyecto original — ver `src/common/infrastructure/http/token-store.ts`).

---

## 5. Capa de aplicación: stores

### 5.1 `useSessionStore` (fuente de verdad del tenant actual)
Archivo: `src/common/application/contexts/session-store.tsx`

- Zustand con middleware `devtools` + `persist`.
- `name: 'session-store'` en localStorage.
- `partialize` persiste `user`, `tenant`, `tenantRole` (NO los tokens — los tokens viven en cookies/memoria).

```ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { Tenant } from '@/src/common/domain/entities/Tenant';
import type { TenantRole } from '@/src/common/domain/entities/tenants/TenantRole';
import type { User } from '@/src/common/domain/entities/User';

interface SessionState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  tenant: Tenant | null;
  tenantRole: TenantRole | null;
}
interface SessionActions {
  setAccessToken: (t: string | null) => void;
  setRefreshToken: (t: string | null) => void;
  setUser: (u: User | null) => void;
  setTenant: (t: Tenant | null) => void;
  setTenantRole: (r: TenantRole | null) => void;
  setSession: (s: Partial<SessionState>) => void;
  clearSession: () => void;
}

const initial: SessionState = {
  accessToken: null, refreshToken: null,
  user: null, tenant: null, tenantRole: null,
};

export const useSessionStore = create<SessionState & SessionActions>()(
  devtools(
    persist(
      (set) => ({
        ...initial,
        setAccessToken: (token) => set((s) => ({ ...s, accessToken: token }), false, 'setAccessToken'),
        setRefreshToken: (token) => set((s) => ({ ...s, refreshToken: token }), false, 'setRefreshToken'),
        setUser: (user) => set((s) => ({ ...s, user }), false, 'setUser'),
        setTenant: (tenant) => set((s) => ({ ...s, tenant }), false, 'setTenant'),
        setTenantRole: (tenantRole) => set((s) => ({ ...s, tenantRole }), false, 'setTenantRole'),
        setSession: (session) => set((s) => ({ ...s, ...session }), false, 'setSession'),
        clearSession: () => set(initial, false, 'clearSession'),
      }),
      {
        name: 'session-store',
        partialize: (state) => ({
          user: state.user,
          tenant: state.tenant,
          tenantRole: state.tenantRole,
        }),
      },
    ),
    { name: 'SessionStore' },
  ),
);
```

### 5.2 `useTenantStore` (lista de tenants disponibles + acción de switch)
Archivo: `src/tenants/application/stores/tenant-store.ts`

Estado: `tenants`, `selectedTenant`, `loading`, `error`. **NO se persiste**.

```ts
import { create } from 'zustand';
import { useSessionStore } from '@/src/common/application/contexts/session-store';
import type { Tenant } from '@/src/common/domain/entities/Tenant';
import type { ErrorFeeback } from '@/src/common/domain/errors/ErrorFeeback';
import { genericServerError, isErrorFeedback } from '@/src/common/domain/errors/ErrorFeeback';
import type { TenantFilters } from '@/src/common/domain/filters/tenant';
import { domainContext } from '@/src/common/infrastructure/domain-context';

interface TenantsState {
  tenants: Tenant[];
  selectedTenant: Tenant | null;
  loading: boolean;
  error: ErrorFeeback | null;
  fetchTenants: (filters?: TenantFilters) => Promise<void>;
  selectTenant: (tenant: Tenant) => Promise<void>;
  clearSelection: () => void;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
}

const { tenantsRepository } = domainContext;

export const useTenantStore = create<TenantsState>()((set) => ({
  tenants: [],
  selectedTenant: null,
  loading: false,
  error: null,

  fetchTenants: async (filters) => {
    set({ loading: true, error: null });
    try {
      const result = await tenantsRepository.getUserTenants(filters);
      if (isErrorFeedback(result)) {
        set({ loading: false, error: result, tenants: [] });
      } else {
        set({ loading: false, error: null, tenants: result });
      }
    } catch (err) {
      console.error('Error fetching tenants:', err);
      set({ loading: false, error: genericServerError, tenants: [] });
    }
  },

  selectTenant: async (tenant) => {
    const sessionStore = useSessionStore.getState();
    const taskResult = await tenantsRepository.setCurrentTenant(tenant.uuid);
    if (isErrorFeedback(taskResult)) return;        // si falla, no se cambia
    set({ selectedTenant: tenant });
    sessionStore.setTenant(tenant);                 // sincroniza session-store
  },

  clearSelection: () => set({ selectedTenant: null }),
  clearError:     () => set({ error: null }),
  setLoading:     (loading) => set({ loading }),
}));

// Selectores
export const useTenants         = () => useTenantStore((s) => s.tenants);
export const useSelectedTenant  = () => useTenantStore((s) => s.selectedTenant);
export const useTenantsLoading  = () => useTenantStore((s) => s.loading);
export const useTenantsError    = () => useTenantStore((s) => s.error);
```

> **Importante:** `selectTenant` **no** verifica el `status` del `TaskResult` — solo trata el resultado como error si pasa el `isErrorFeedback`. Replicar la misma semántica.

### 5.3 (Opcional) Hook `useTenants`
Archivo: `src/tenants/application/hooks/use-tenants.ts`

Wrapper de conveniencia sobre el store. Expone `{ tenants, selectedTenant, loading, error, refetch, selectTenant, clearSelection, clearError, updateTenant }`. Útil para pantallas de settings; **no es estrictamente necesario para el switcher** (el componente lee directo del store).

---

## 6. Bootstrap: cargar tenants al iniciar sesión

### 6.1 `StoreInitializer`
Archivo: `src/common/components/store-initializer.tsx`

Componente vacío (`return null`) que se monta una sola vez en el layout protegido. Dispara `fetchTenants()` cuando hay `accessToken`.

```tsx
'use client';
import { useEffect } from 'react';
import { useSessionStore } from '@/src/common/application/contexts/session-store';
import { useStoreCleaner } from '@/src/common/application/hooks/use-store-cleaner';
import { useTenantStore } from '@/src/tenants/application/stores/tenant-store';

export function StoreInitializer() {
  const { fetchTenants } = useTenantStore();
  const { accessToken } = useSessionStore();

  useStoreCleaner();

  useEffect(() => {
    if (accessToken) fetchTenants();
  }, [fetchTenants, accessToken]);

  return null;
}
```

### 6.2 Mount point
En `src/common/components/layout/protected-providers.tsx` (o el provider raíz de la zona autenticada):

```tsx
import { StoreInitializer } from '@/src/common/components/store-initializer';
// …
<StoreInitializer />
{children}
```

### 6.3 `useStoreCleaner` (limpieza al cambiar de tenant)
Archivo: `src/common/application/hooks/use-store-cleaner.ts`

Observa `tenant.slug`; si cambia, resetea los datos en localStorage de los stores tenant-específicos (`transaction-store`, `payment-store`, `pos-device-store`, etc.) preservando `pagination`. **Adaptar la lista `storeKeys` a los stores que tu proyecto persista.**

También exporta `clearTenantSpecificStores()` y `clearAllStores()` (usado en logout).

---

## 7. Componente UI: `TenantHead`

Archivo: `src/common/components/layout/tenant-head.tsx` (168 líneas en el original).

### 7.1 Inputs
- `tenant` (actual) ← `useSessionStore()`
- `{ tenants, selectTenant, loading }` ← `useTenantStore()`
- `{ open }` ← `useSidebar()` (de shadcn/ui)

### 7.2 Reglas de render
```ts
const hasMultipleTenants = (tenants?.length ?? 0) > 1;
const logoSrc = tenant?.logoUrl || '/images/logo.png';
const logoAlt = tenant?.name || 'Tripto';
const isExternal = !!tenant?.logoUrl;
const iconSize = open ? 60 : 80;
```

- Si `hasMultipleTenants` ⇒ render del **dropdown** (trigger con logo+nombre+`ChevronDown` + lista).
- Si NO ⇒ render del `SidebarMenuButton` simple (solo logo+nombre, sin chevron).

### 7.3 Handler de cambio
**Replicar tal cual** (incluye el reload — comentado como TODO en el original):

```tsx
const handleTenantChange = React.useCallback(
  async (tenantOption: (typeof tenants)[number]) => {
    await selectTenant(tenantOption);
    if (typeof window !== 'undefined') {
      window.location.reload();
    }
  },
  [selectTenant],
);
```

### 7.4 Estructura del dropdown
```tsx
<SidebarMenu>
  <SidebarMenuItem>
    {hasMultipleTenants ? (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <SidebarMenuButton size="lg" className="...">
            {/* logo + nombre + countryCode + ChevronDown */}
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-64" align="start" side="right">
          <DropdownMenuLabel>Cambiar Tenant</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {loading ? (
            <DropdownMenuItem disabled>Cargando tenants...</DropdownMenuItem>
          ) : (
            tenants.map((opt) => (
              <DropdownMenuItem
                key={opt.uuid}
                onClick={() => handleTenantChange(opt)}
                className="flex items-center gap-3 p-3 cursor-pointer"
              >
                <Building2 className="h-4 w-4 text-muted-foreground" />
                <div className="flex flex-col flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{opt.name}</span>
                    {tenant?.uuid === opt.uuid && (
                      <Badge variant="default" className="text-xs">Actual</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <span>{opt.slug}</span>
                    <span>•</span>
                    <span>{opt.countryCode}</span>
                    <span>•</span>
                    <span>{opt.currencyCode}</span>
                  </div>
                </div>
              </DropdownMenuItem>
            ))
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    ) : (
      <SidebarMenuButton size="lg" className="...">
        {/* logo + nombre + countryCode (sin chevron, sin dropdown) */}
      </SidebarMenuButton>
    )}
  </SidebarMenuItem>
</SidebarMenu>
```

### 7.5 Mount en el sidebar
Archivo: `src/common/components/layout/app-sidebar.tsx`

```tsx
<Sidebar collapsible="icon" variant="floating" {...props}>
  <SidebarHeader>
    <TenantHead />
  </SidebarHeader>
  <SidebarContent>{/* nav groups */}</SidebarContent>
  <SidebarFooter><UserSideNav /></SidebarFooter>
  <SidebarRail />
</Sidebar>
```

> Nota: el archivo `team-switcher.tsx` existe en el repo pero **NO se usa**. El sidebar real renderiza `TenantHead`, no `TeamSwitcher`.

---

## 8. Flujo end-to-end del switch

1. Usuario hace login → `auth` guarda `accessToken` en `useSessionStore`.
2. `StoreInitializer` detecta `accessToken` ⇒ llama `useTenantStore.fetchTenants()`.
3. `fetchTenants` hace `GET /v1/me/tenants` ⇒ guarda `tenants[]` en el store (con `logoUrl` resueltos por `getTenantLogoUrl`).
4. `TenantHead` lee `tenants` y renderiza el dropdown si `tenants.length > 1`.
5. Usuario elige un tenant ⇒ `handleTenantChange(opt)`:
   1. `selectTenant(opt)` del store.
   2. Store hace `PUT /v1/me/tenants/{opt.uuid}`.
   3. Si NO es `ErrorFeeback` ⇒ `set({ selectedTenant: opt })` y `sessionStore.setTenant(opt)`.
   4. El componente hace `window.location.reload()`.
6. Tras el reload:
   - `session-store` ya tiene el nuevo `tenant` persistido (vía `partialize`).
   - El backend resuelve `current_tenant_id` desde la sesión del usuario.
   - `useStoreCleaner` detecta el cambio de `tenant.slug` y limpia los stores de datos tenant-específicos.

> **Por qué el reload:** el comentario `// TODO: Quitar este handle cuando se solucione lo del cambio de session del tenant.` indica que el reload es un workaround actual. Si quieres evitarlo, tendrías que invalidar/refetch manualmente todos los datos en memoria que dependen del tenant — hoy se delega al reload.

---

## 9. Checklist de implementación (orden recomendado)

1. [ ] **Domain types**
   - `domain/enums/tenants.ts` (`TenantStatus`)
   - `domain/entities/Tenant.ts`
   - `domain/entities/common/task-result.ts`
   - `domain/filters/tenant.ts`
   - `domain/responses/tenant.ts`, `domain/responses/task-result.ts`
   - `domain/errors/ErrorFeeback.ts`
   - `domain/repositories/tenant.ts`
2. [ ] **Infra**
   - `utils/tenant-utils.ts` (`getTenantLogoUrl`)
   - `utils/http-error-handler.ts` (helper `handleHttpError`)
   - `infrastructure/http/client.ts` (Axios instance autenticada)
   - `infrastructure/repositories/http-tenant.ts`
   - `infrastructure/domain-context.ts` (registrar `tenantsRepository`)
3. [ ] **Stores**
   - `application/contexts/session-store.tsx` (con `persist` + `partialize`)
   - `tenants/application/stores/tenant-store.ts`
4. [ ] **Bootstrap**
   - `application/hooks/use-store-cleaner.ts`
   - `components/store-initializer.tsx`
   - Montar `<StoreInitializer />` en el provider del layout protegido
5. [ ] **UI**
   - `components/layout/tenant-head.tsx`
   - Renderizar `<TenantHead />` en `<SidebarHeader>` de `app-sidebar.tsx`

---

## 10. Pruebas manuales mínimas

- [ ] Usuario con **1 tenant**: el header muestra logo+nombre, sin chevron, sin dropdown.
- [ ] Usuario con **N tenants**: el header muestra chevron y al click abre el dropdown con label "Cambiar Tenant".
- [ ] Cada item muestra `name`, `slug`, `countryCode`, `currencyCode`. El item del tenant actual muestra el badge **"Actual"**.
- [ ] Estado `loading` muestra `"Cargando tenants..."` (item disabled).
- [ ] Click en otro tenant: se hace `PUT /v1/me/tenants/{uuid}` y luego un reload completo de la página.
- [ ] Tras el reload, el nuevo tenant queda persistido (recargar otra vez no debe perderlo) y los stores tenant-específicos (`transaction-store`, etc.) aparecen reseteados.
- [ ] Si el `PUT` falla: el tenant actual NO cambia (el store no actualiza `selectedTenant`/sessionStore).

---

## 11. Referencias al código original (verificación)

| Archivo | Rol |
|---|---|
| `src/common/components/layout/app-sidebar.tsx` | Monta `<TenantHead />` en `<SidebarHeader>` |
| `src/common/components/layout/tenant-head.tsx` | Switcher UI (168 líneas) |
| `src/tenants/application/stores/tenant-store.ts` | Store Zustand: `fetchTenants`, `selectTenant` |
| `src/common/application/contexts/session-store.tsx` | Tenant actual + `persist` |
| `src/common/components/store-initializer.tsx` | Dispara `fetchTenants` al haber accessToken |
| `src/common/components/layout/protected-providers.tsx` | Mount point del `StoreInitializer` |
| `src/common/infrastructure/repositories/http-tenant.ts` | Llama `GET/PUT /v1/me/tenants` |
| `src/common/domain/repositories/tenant.ts` | Interface `TenantRepository` |
| `src/common/domain/entities/Tenant.ts` | Entity `Tenant` |
| `src/common/utils/tenant-utils.ts` | `getTenantLogoUrl` |
| `src/common/application/hooks/use-store-cleaner.ts` | Reset de stores tenant-específicos |
| `src/common/application/hooks/use-tenant-change.ts` | Detector reusable de cambio de tenant |

> El archivo `src/common/components/team-switcher.tsx` **existe pero no se usa**. No replicarlo.
