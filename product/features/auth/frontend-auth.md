---
feature: auth
type: plan
status: partial
coverage: 82
audited: 2026-06-16
---

# Guia de Autenticacion y Manejo de Sesiones

> Documentacion del sistema de autenticacion con access/refresh tokens implementado en Next.js 16 (App Router).
> Objetivo: servir como referencia para replicar este patron en otros proyectos.

---

## Tabla de Contenidos

1. [Arquitectura General](#arquitectura-general)
2. [Constantes y Configuracion](#constantes-y-configuracion)
3. [Flujo de Login](#flujo-de-login)
4. [Almacenamiento de Tokens (Cookies)](#almacenamiento-de-tokens-cookies)
5. [Estado en Cliente (Zustand)](#estado-en-cliente-zustand)
6. [Inyeccion de Headers en Peticiones](#inyeccion-de-headers-en-peticiones)
7. [Refresh Automatico de Access Token](#refresh-automatico-de-access-token)
8. [Proteccion de Rutas (Server-Side)](#proteccion-de-rutas-server-side)
9. [Logout](#logout)
10. [Login con Google (OAuth)](#login-con-google-oauth)
11. [Sincronizacion entre Tabs](#sincronizacion-entre-tabs)
12. [Decodificacion JWT](#decodificacion-jwt)
13. [Diagrama de Flujo Completo](#diagrama-de-flujo-completo)
14. [Checklist para Implementar en Otro Proyecto](#checklist-para-implementar-en-otro-proyecto)

---

## Arquitectura General

```
Browser (Client)                    Next.js Server (API Routes)              Backend API
┌─────────────────┐                ┌──────────────────────┐                ┌──────────────┐
│  Zustand Store   │───axios───▶   │  /api/auth/login     │───axios───▶   │ /auth/login   │
│  (accessToken,   │               │  /api/auth/refresh   │               │ /auth/refresh │
│   user, tenant)  │◀──cookies──   │  /api/auth/logout    │◀──response──  │ /auth/logout  │
│                  │               │  /api/auth/google/cb  │               │ /auth/google  │
│  Axios           │               │                      │               │               │
│  Interceptors    │               │  cookies (httpOnly)   │               │               │
└─────────────────┘                └──────────────────────┘                └──────────────┘
```

**Principio clave:** Los tokens nunca se exponen directamente al JavaScript del cliente via cookies. Se almacenan como `httpOnly` cookies gestionadas por las API Routes de Next.js, que actuan como un **BFF (Backend for Frontend)**. El cliente solo mantiene el `accessToken` en memoria (Zustand) para inyectarlo en los headers de las peticiones.

---

## Constantes y Configuracion

```typescript
// src/common/domain/constants.ts

export const REFRESH_TOKEN_COOKIE_KEY = '___RT9___';
export const ACCESS_TOKEN_COOKIE_KEY  = '___AT9___';

export const LOGIN_PATH = '/';
export const LOGIN_REDIRECT_PATH = '/dashboard';
export const UNASSIGNED_REDIRECT_PATH = '/unassigned';

// Configurables via env vars
export const JWT_ACCESS_TOKEN_EXPIRE_MINUTES = Number(
  process.env.JWT_ACCESS_TOKEN_EXPIRE_MINUTES ?? 30        // 30 minutos
);
export const JWT_REFRESH_TOKEN_EXPIRE_MINUTES = Number(
  process.env.JWT_REFRESH_TOKEN_EXPIRE_MINUTES ?? 10080    // 7 dias
);

export const PUBLIC_ROUTES = [
  LOGIN_PATH,
  '/logout',
  '/forgot-password',
  '/register',
  '/api/auth/google/callback',
];
```

```typescript
// src/common/settings.ts

import { getPublicEnv } from '@/src/public-env';

export const Settings = {
  apiBaseUrl: (() => {
    const { BACKEND_API_HOST } = getPublicEnv();
    return process.env.BACKEND_API_HOST || BACKEND_API_HOST;
  })(),
  isProduction: process.env.NODE_ENV === 'production',
};
```

---

## Flujo de Login

### 1. Cliente envia credenciales

El formulario de login hace POST a la API Route local (no directamente al backend):

```typescript
// Desde el cliente
await axios.post('/api/auth/login', { email, password });
```

### 2. API Route `/api/auth/login` (Server-Side)

```typescript
// src/app/api/auth/login/route.ts

export async function POST(req: NextRequest) {
  const body = await req.json();
  
  // 1. Llama al backend real
  const response = await authRepository.login(body.email, body.password);

  if (response && isErrorFeedback(response)) {
    return NextResponse.json(response, { status: 400 });
  }

  // 2. Extrae tokens de la respuesta del backend
  const session = response.data.session;
  // session = { accessToken, refreshToken, expiresIn?, tokenType? }

  // 3. Almacena ambos tokens como httpOnly cookies
  const cookieStore = await cookies();
  
  cookieStore.set(REFRESH_TOKEN_COOKIE_KEY, session.refreshToken, {
    httpOnly: true,
    secure: Settings.isProduction,   // solo HTTPS en produccion
    sameSite: 'lax',
    path: '/',
    maxAge: JWT_REFRESH_TOKEN_EXPIRE_MINUTES * 60,  // 7 dias en segundos
  });
  
  cookieStore.set(ACCESS_TOKEN_COOKIE_KEY, session.accessToken, {
    httpOnly: true,
    secure: Settings.isProduction,
    sameSite: 'lax',
    path: '/',
    maxAge: JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,   // 30 min en segundos
  });

  // 4. Retorna la sesion completa al cliente (sin cookies visibles)
  return NextResponse.json(response);
}
```

### 3. Cliente recibe la respuesta

El cliente almacena los datos de sesion en Zustand (user, tenant, accessToken en memoria):

```typescript
// Despues del login exitoso
const { session, user, tenant, tenantRole } = response.data;
useSessionStore.getState().setSession({
  accessToken: session.accessToken,
  refreshToken: session.refreshToken,
  user,
  tenant,
  tenantRole,
});
```

### Respuesta del backend

```typescript
// TenantUserSessionResponse
{
  data: {
    session: {
      accessToken: string;
      refreshToken: string;
      expiresIn?: number | null;
      tokenType?: string | null;
    },
    user: User;
    tenant: Tenant;
    tenantRole: TenantRole;
  },
  datetime: string;
}
```

---

## Almacenamiento de Tokens (Cookies)

| Cookie | Key | httpOnly | secure | sameSite | maxAge | Proposito |
|--------|-----|----------|--------|----------|--------|-----------|
| Access Token | `___AT9___` | `true` | solo en prod | `lax` | 30 min | Autenticar peticiones al backend |
| Refresh Token | `___RT9___` | `true` | solo en prod | `lax` | 7 dias | Renovar el access token |

**Consideraciones:**
- `httpOnly: true` impide acceso desde JavaScript (proteccion contra XSS)
- `secure: true` en produccion asegura que solo se envien por HTTPS
- `sameSite: 'lax'` permite navegacion normal pero protege contra CSRF basico
- `path: '/'` las cookies estan disponibles en toda la aplicacion

---

## Estado en Cliente (Zustand)

```typescript
// src/common/application/contexts/session-store.tsx

interface SessionState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  tenant: Tenant | null;
  tenantRole: TenantRole | null;
}

interface SessionActions {
  setAccessToken: (token: string | null) => void;
  setRefreshToken: (token: string | null) => void;
  setUser: (user: User | null) => void;
  setTenant: (tenant: Tenant | null) => void;
  setTenantRole: (tenantRole: TenantRole | null) => void;
  setSession: (session: Partial<SessionState>) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionStore>()(
  devtools(
    persist(
      (set) => ({
        ...initialSessionState,
        // ... acciones
        clearSession: () => set(initialSessionState, false, 'clearSession'),
      }),
      {
        name: 'session-store',
        partialize: (state) => ({
          // accessToken y refreshToken NO se persisten en localStorage
          // Solo se persisten datos de usuario/tenant
          user: state.user,
          tenant: state.tenant,
          tenantRole: state.tenantRole,
        }),
      }
    )
  )
);
```

**Nota importante:** El store usa `persist` middleware de Zustand con `partialize`, lo que significa que **solo `user`, `tenant` y `tenantRole`** se persisten en `localStorage`. Los tokens (`accessToken`, `refreshToken`) viven **solo en memoria** (se pierden al recargar). Esto es intencional: el access token real para autenticacion se recupera via refresh de cookies httpOnly cada vez que se carga una pagina protegida (ver [Proteccion de Rutas](#proteccion-de-rutas-server-side)).

---

## Inyeccion de Headers en Peticiones

Cada peticion HTTP lleva headers comunes inyectados automaticamente:

```typescript
// src/common/infrastructure/requests.ts

import { getPublicEnv } from '@/src/public-env';

export const isServer = (): boolean => typeof window === 'undefined';

export const getBackendHostname = () => {
  const { BACKEND_API_HOST } = getPublicEnv();
  return process.env.BACKEND_API_HOST || BACKEND_API_HOST;
};

export const getCommonHeaders = (
  tenantSlug?: string | null,
  accessToken?: string | null
) => {
  const version = process.env.version || '1';
  const client = `web:app.tripto.web/latest:${version}`;

  let headers: object = {
    'Content-Type': 'application/json',
    'X-Client': client,
  };

  if (tenantSlug)
    headers = { ...headers, 'X-Tenant': tenantSlug };

  if (accessToken)
    headers = { ...headers, Authorization: `Bearer ${accessToken}` };

  if (isServer())
    headers = { ...headers, 'X-Api-Key': `${process.env.BACKEND_API_KEY}` };

  return headers;
};
```

### Interceptor de Request (Axios)

```typescript
// src/common/infrastructure/http/client.ts

function attachAuthHeaders(config: InternalAxiosRequestConfig) {
  const { tenant, accessToken } = useSessionStore.getState();
  const common = getCommonHeaders(tenant?.slug ?? null, accessToken ?? null);

  config.headers = config.headers || {};

  if (typeof config.headers.set === 'function') {
    for (const [k, v] of Object.entries(common)) {
      if (v == null) continue;
      config.headers.set(k, v);
    }
  } else {
    config.headers = {
      ...(config.headers as any),
      ...(common as any),
    };
  }
  return config;
}

// Se aplica solo a las instancias client-side (serverHttp NO tiene interceptors)
localHttp.interceptors.request.use(attachAuthHeaders);
authHttp.interceptors.request.use(attachAuthHeaders);
```

### Instancias de Axios

```typescript
// Server-side: directo al backend
export const serverHttp = axios.create({
  baseURL: `${Settings.apiBaseUrl}/v1`,
  timeout: 10000,
});

// Client-side: a traves de las API Routes de Next.js
export const localHttp = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

// Client-side: para todos los repos de dominio (tenants, branches, users, etc.)
export const authHttp = axios.create({
  baseURL: '/api',
});
```

---

## Refresh Automatico de Access Token

El sistema renueva el access token de forma transparente cuando recibe un 401.

### Interceptor de Response (Client-Side)

```typescript
// src/common/infrastructure/http/client.ts

let refreshPromise: Promise<string | null> | null = null;
let isRedirecting = false;

// 1. DEDUPLICACION: Evita multiples refresh simultaneos
function deduplicatedRefresh(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = refreshAccess().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;  // Todas las peticiones comparten la misma Promise
}

// 2. REFRESH: Llama a la API Route local
async function refreshAccess(): Promise<string | null> {
  try {
    const res = await axios.post('/api/auth/refresh', null, {
      withCredentials: true,  // Envia las cookies automaticamente
    });
    return res.data?.data?.session?.accessToken ?? null;
  } catch {
    return null;
  }
}

// 3. MANEJO DE FALLO: Limpia sesion y redirige
function handleRefreshFailure(): void {
  if (isRedirecting) return;     // Evita loop de redirects
  isRedirecting = true;
  useSessionStore.getState().clearSession();
  if (typeof window !== 'undefined') {
    window.location.href = '/';   // Redirige al login
  }
}

// 4. INTERCEPTOR: Se activa en cada respuesta 401
function createRefreshInterceptor(httpClient: ReturnType<typeof axios.create>) {
  return async (error: AxiosError) => {
    const original: any = error.config;

    if (error.response?.status === 401 && !original?._retry && !isRedirecting) {
      original._retry = true;  // Marca para no reintentar infinitamente
      
      const newToken = await deduplicatedRefresh();
      
      if (newToken) {
        // Exito: actualiza token y reintenta la peticion original
        useSessionStore.getState().setAccessToken(newToken);
        original.headers = original.headers ?? {};
        original.headers.Authorization = `Bearer ${newToken}`;
        return httpClient(original);
      }
      
      // Fallo: redirige al login
      handleRefreshFailure();
    }
    
    return Promise.reject(error);
  };
}
```

### API Route `/api/auth/refresh` (Server-Side)

```typescript
// src/app/api/auth/refresh/route.ts

export async function POST(_: NextRequest) {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get(REFRESH_TOKEN_COOKIE_KEY)?.value;

  // 1. Valida que existe el refresh token en cookies
  if (!refreshToken) {
    return NextResponse.json(invalidRefreshToken, { status: 400 });
  }

  try {
    // 2. Llama al backend con el refresh token
    const response = await authRepository.refresh(refreshToken);
    
    if (response && isErrorFeedback(response)) {
      // 3a. Error: elimina ambas cookies
      cookieStore.delete(REFRESH_TOKEN_COOKIE_KEY);
      cookieStore.delete(ACCESS_TOKEN_COOKIE_KEY);
      return NextResponse.json(response, { status: 400 });
    }

    // 3b. Exito: actualiza ambas cookies con los nuevos tokens
    const session = response.data.session;
    cookieStore.set(REFRESH_TOKEN_COOKIE_KEY, session.refreshToken, {
      httpOnly: true,
      secure: Settings.isProduction,
      sameSite: 'lax',
      path: '/',
      maxAge: JWT_REFRESH_TOKEN_EXPIRE_MINUTES * 60,
    });
    cookieStore.set(ACCESS_TOKEN_COOKIE_KEY, session.accessToken, {
      httpOnly: true,
      secure: Settings.isProduction,
      sameSite: 'lax',
      path: '/',
      maxAge: JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    });

    return NextResponse.json(response);
  } catch (error) {
    cookieStore.delete(REFRESH_TOKEN_COOKIE_KEY);
    cookieStore.delete(ACCESS_TOKEN_COOKIE_KEY);
    return NextResponse.json(
      {
        errors: [{ code: 'SERVER_ERROR', message: 'Refresh failed' }],
        validation: null,
      },
      { status: 500 }
    );
  }
}
```

### Flujo del Refresh

```
Peticion falla con 401
        │
        ▼
¿Ya hay un refresh en curso?
   SI ──▶ Espera la misma Promise
   NO ──▶ Inicia refresh
              │
              ▼
     POST /api/auth/refresh
     (envia cookies automaticamente)
              │
              ▼
     API Route lee ___RT9___ cookie
              │
              ▼
     Llama backend /auth/refresh
              │
        ┌─────┴─────┐
     Exito        Error
        │             │
        ▼             ▼
  Actualiza       Elimina cookies
  ambas cookies   Retorna error
  Retorna tokens       │
        │              ▼
        ▼        handleRefreshFailure()
  Actualiza       clearSession()
  Zustand store   redirect('/')
  Reintenta
  peticion original
```

---

## Proteccion de Rutas (Server-Side)

### Layout Protegido

Todas las paginas protegidas estan bajo `src/app/(protected)/layout.tsx`:

```typescript
// src/app/(protected)/layout.tsx

export const dynamic = 'force-dynamic';  // No cachear, verificar siempre

export default async function ProtectedLayout({ children }) {
  // 1. Intenta refrescar la sesion desde el server
  const tenantUserSession = await refreshServerSession();

  // 2. Si falla (sin cookie, token expirado, etc.), redirige al login
  if (isErrorFeedback(tenantUserSession)) {
    redirect('/');
  }

  // 3. Si tiene sesion, provee los datos a los children
  return (
    <ProtectedProviders tenantUserSession={tenantUserSession}>
      {children}
    </ProtectedProviders>
  );
}
```

### Server Session

```typescript
// src/auth/application/server-session.ts
'use server';

export async function refreshServerSession(): Promise<
  TenantUserSession | ErrorFeedback
> {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get(REFRESH_TOKEN_COOKIE_KEY)?.value;

  if (!refreshToken) {
    return refreshCookieNotFound;  // No hay sesion
  }

  // Llama directamente al backend (server-to-server, sin pasar por API Route)
  const response = await authRepository.refresh(refreshToken);
  
  if (isErrorFeedback(response)) {
    return response;  // Token invalido/expirado
  }
  
  return response.data;  // { session, user, tenant, tenantRole }
}
```

**Nota:** `refreshServerSession` se ejecuta en cada carga de pagina protegida (`force-dynamic`), garantizando que la sesion siempre este vigente.

---

## Logout

### Flujo

```typescript
// 1. Cliente llama a la API Route
await axios.post('/api/auth/logout');

// 2. API Route (src/app/api/auth/logout/route.ts)
export async function POST(_: NextRequest) {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get(REFRESH_TOKEN_COOKIE_KEY)?.value ?? '';
  
  // 3. Notifica al backend para invalidar el refresh token
  const response = await authRepository.logout(refreshToken);
  
  // Si el backend retorna error, NO elimina cookies y retorna 400
  if (response && isErrorFeedback(response)) {
    return NextResponse.json(response, { status: 400 });
  }
  
  // 4. Solo elimina cookies si el logout fue exitoso
  cookieStore.delete(REFRESH_TOKEN_COOKIE_KEY);
  cookieStore.delete(ACCESS_TOKEN_COOKIE_KEY);
  
  return NextResponse.json(response);
}

// 5. Cliente limpia el estado local
useSessionStore.getState().clearSession();
```

---

## Login con Google (OAuth)

```typescript
// src/app/api/auth/google/callback/route.ts

export async function GET(request: NextRequest) {
  const code = new URL(request.url).searchParams.get('code');
  
  if (!code) {
    return NextResponse.json({ message: 'GoogleCodeNotFound' }, { status: 400 });
  }

  // 1. Intercambia el code con el backend
  const loginResponse = await authRepository.googleLogin(code);
  
  if (isErrorFeedback(loginResponse)) {
    return NextResponse.json({ message: loginResponse.errors }, { status: 401 });
  }

  // 2. Almacena tokens en cookies (mismo patron que login normal)
  const tenantUserSession = loginResponse.data as TenantUserSession;
  const session = tenantUserSession.session;
  const cookieStore = await cookies();
  cookieStore.set(REFRESH_TOKEN_COOKIE_KEY, session.refreshToken, { /* mismas opciones */ });
  cookieStore.set(ACCESS_TOKEN_COOKIE_KEY, session.accessToken, { /* mismas opciones */ });

  // 3. Redirige al dashboard (o ruta apropiada segun el tenant)
  const redirectUrl = new URL(getRedirectPath(tenantUserSession), request.url);
  return NextResponse.redirect(redirectUrl, 303);
}
```

---

## Sincronizacion entre Tabs

Se usa `BroadcastChannel` para mantener la sesion sincronizada entre pestanas:

```typescript
// src/common/infrastructure/http/token-store.ts

const broadcastChannel = new BroadcastChannel('auth');

// Cuando cambia el token en Zustand, notifica a otras tabs
useSessionStore.subscribe((state) => {
  const newToken = state.accessToken;
  if (accessToken !== newToken) {
    accessToken = newToken;
    broadcastChannel.postMessage({
      type: newToken ? 'LOGIN' : 'LOGOUT',
    });
  }
});

// Otras tabs escuchan los mensajes
export const AccessTokenStore = {
  onMessage: (callback) => {
    broadcastChannel.onmessage = (event) => callback(event.data);
    return () => (broadcastChannel.onmessage = null);
  },
};
```

**Resultado:** Si el usuario hace logout en una tab, todas las demas tabs reciben el evento `LOGOUT` y pueden limpiar su estado.

---

## Decodificacion JWT

```typescript
// src/common/infrastructure/http/jwt.ts

import { jwtDecode } from 'jwt-decode';

export type JwtClaims = {
  sub?: string;     // Subject (user ID)
  jti?: string;     // JWT ID (unique identifier)
  ns?: string;      // Namespace
  exp?: number;     // Expiration (seconds since epoch)
  iat?: number;     // Issued at
};

export function decodeClaims(token: string | null): JwtClaims | null {
  if (!token) return null;
  try {
    return jwtDecode<JwtClaims>(token);
  } catch {
    return null;
  }
}

export function getExpiration(token: string | null): number | null {
  const claims = decodeClaims(token);
  if (!claims?.exp) return null;
  return claims.exp * 1000;  // Convierte a milliseconds para JS Date
}
```

---

## Diagrama de Flujo Completo

```
                         ┌─────────────────┐
                         │   Usuario abre   │
                         │   pagina protegida│
                         └────────┬─────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │  Protected Layout           │
                    │  (Server Component)          │
                    │                              │
                    │  refreshServerSession()      │
                    │  Lee cookie ___RT9___        │
                    │  Llama backend /auth/refresh │
                    └─────────────┬───────────────┘
                          ┌───────┴───────┐
                       Exito            Error
                          │               │
                          ▼               ▼
                   Render pagina     redirect('/')
                   con providers     (pagina de login)
                          │
                          ▼
              ┌──────────────────────┐
              │  Cliente carga       │
              │  Zustand + Providers │
              │  (session data)      │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Peticion API        │
              │  axios interceptor   │
              │  agrega Bearer token │
              └──────────┬───────────┘
                         │
                   ┌─────┴─────┐
                200/OK      401
                   │           │
                   ▼           ▼
              Respuesta   deduplicatedRefresh()
              normal      POST /api/auth/refresh
                               │
                         ┌─────┴─────┐
                      Exito        Error
                         │           │
                         ▼           ▼
                   Reintenta    clearSession()
                   peticion     redirect('/')
                   original
```

---

## Checklist para Implementar en Otro Proyecto

### Dependencias

```bash
pnpm add axios zustand jwt-decode
```

### Archivos a crear

1. **Constantes** - Cookie keys, tiempos de expiracion, rutas publicas
2. **Settings** - `apiBaseUrl`, `isProduction`
3. **API Routes** (Next.js App Router):
   - `app/api/auth/login/route.ts` - Recibe credenciales, llama backend, setea cookies
   - `app/api/auth/refresh/route.ts` - Lee refresh cookie, renueva tokens
   - `app/api/auth/logout/route.ts` - Invalida refresh en backend, elimina cookies
4. **HTTP Client** (`infrastructure/http/client.ts`):
   - Instancias de axios (server, local)
   - Request interceptor para headers
   - Response interceptor 401 con refresh deduplicado
5. **Session Store** (Zustand):
   - Estado: `accessToken`, `refreshToken`, `user`, `tenant`
   - Acciones: `setSession`, `clearSession`, `setAccessToken`
   - Middleware: `persist` + `devtools`
6. **Server Session** (`server-session.ts`):
   - `refreshServerSession()` - Lee cookie, llama backend directamente
7. **Protected Layout**:
   - `export const dynamic = 'force-dynamic'`
   - Llama `refreshServerSession()`, redirige si falla
8. **Token Store** (opcional):
   - `BroadcastChannel` para sincronizar tabs
9. **Common Headers**:
   - `Authorization: Bearer <token>`
   - `X-Tenant: <slug>` (si es multi-tenant)
   - `X-Client: <app-identifier>`
   - `X-Api-Key: <key>` (solo server-side)

### Patrones clave a implementar

- [ ] Cookies `httpOnly` para ambos tokens (nunca exponer al JS)
- [ ] BFF pattern: cliente habla con API Routes, API Routes hablan con backend
- [ ] Refresh deduplicado: una sola Promise compartida para peticiones concurrentes
- [ ] Flag `_retry` en config de axios para evitar loops infinitos de refresh
- [ ] Flag `isRedirecting` para evitar multiples redirects simultaneos
- [ ] `force-dynamic` en layouts protegidos para validar sesion en cada request
- [ ] `BroadcastChannel` para sincronizar logout entre tabs
- [ ] Eliminar ambas cookies cuando el refresh falla (no dejar cookies huerfanas)

### Variables de entorno necesarias

```env
BACKEND_API_HOST=https://api.example.com
BACKEND_API_KEY=your-server-to-server-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_MINUTES=10080
```

### Repositorio de Auth (codigo exacto)

```typescript
// src/auth/infrastructure/repositories/http-auth.ts

import type { AxiosError, AxiosInstance } from 'axios';

import type { AuthRepository } from '@/src/auth/domain/repositories/auth';
import type { ErrorFeeback } from '@/src/common/domain/errors/ErrorFeeback';
import { genericServerError } from '@/src/common/domain/errors/ErrorFeeback';
import type TaskResultResponse from '@/src/common/domain/responses/task-result';
import type { TenantUserSessionResponse } from '@/src/common/domain/responses/tenant-user-session';
import { handleHttpError } from '@/src/common/utils/http-error-handler';

export class HttpAuthRepository implements AuthRepository {
  httpClient: AxiosInstance;

  constructor(httpClient: AxiosInstance) {
    this.httpClient = httpClient;
  }

  async login(
    email: string,
    password: string
  ): Promise<TenantUserSessionResponse | ErrorFeeback> {
    const payload = { email, password };
    try {
      const httpResponse = await this.httpClient.post('/auth/login', payload);
      return httpResponse.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async logout(
    refreshToken?: string | null
  ): Promise<TaskResultResponse | ErrorFeeback> {
    const payload = { refreshToken };
    try {
      const response = await this.httpClient.post('/auth/logout', payload);
      return response.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async googleLogin(
    code: string
  ): Promise<TenantUserSessionResponse | ErrorFeeback> {
    const payload = { code };
    try {
      const httpResponse = await this.httpClient.post(
        '/auth/google-login',
        payload
      );
      return httpResponse.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }

  async refresh(
    refreshToken?: string | null
  ): Promise<TenantUserSessionResponse | ErrorFeeback> {
    const payload = { refreshToken };
    try {
      const httpResponse = await this.httpClient.post('/auth/refresh', payload);
      return httpResponse.data;
    } catch (error) {
      return handleHttpError(error as AxiosError) || genericServerError;
    }
  }
}
```

### Endpoints del Backend requeridos

| Metodo | Endpoint | Body | Respuesta |
|--------|----------|------|-----------|
| POST | `/auth/login` | `{ email, password }` | `TenantUserSessionResponse` |
| POST | `/auth/logout` | `{ refreshToken }` | `TaskResultResponse` |
| POST | `/auth/refresh` | `{ refreshToken }` | `TenantUserSessionResponse` |
| POST | `/auth/google-login` | `{ code }` | `TenantUserSessionResponse` |

Donde `TenantUserSessionResponse` tiene la estructura:
```typescript
{
  data: {
    session: { accessToken, refreshToken, expiresIn?, tokenType? },
    user: User,
    tenant: Tenant,
    tenantRole: TenantRole
  },
  datetime: string
}
```
