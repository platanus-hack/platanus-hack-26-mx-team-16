---
feature: frontend-shell
type: plan
status: partial
coverage: 65
audited: 2026-06-16
---

# Guia del Proxy Middleware (Next.js 16)

> Documentacion de como `src/proxy.ts` actua como middleware de Next.js para hacer proxy de peticiones al backend, inyectar headers de seguridad y manejar redirects de autenticacion.
> Objetivo: servir como referencia para replicar este patron en otros proyectos.

---

## Tabla de Contenidos

1. [Arquitectura General](#arquitectura-general)
2. [Ubicacion y Convencion Next.js 16](#ubicacion-y-convencion-nextjs-16)
3. [Codigo Completo del Proxy](#codigo-completo-del-proxy)
4. [Proxy de Peticiones /api/v1/*](#proxy-de-peticiones-apiv1)
5. [Inyeccion de Headers](#inyeccion-de-headers)
6. [Auth Redirects en Middleware](#auth-redirects-en-middleware)
7. [Instancias de Axios y Quien Usa Cual](#instancias-de-axios-y-quien-usa-cual)
8. [Relacion con el Sistema de Auth](#relacion-con-el-sistema-de-auth)
9. [Variables de Entorno](#variables-de-entorno)
10. [Diagrama de Flujo](#diagrama-de-flujo)
11. [Checklist para Implementar en Otro Proyecto](#checklist-para-implementar-en-otro-proyecto)

---

## Arquitectura General

```
Browser                          Next.js Middleware (proxy.ts)              Backend API
┌─────────────┐                 ┌───────────────────────┐                 ┌──────────────┐
│  authHttp   │──/api/v1/...──▶ │  Intercepta /api/v1/* │──rewrite──▶    │  /v1/...     │
│  localHttp  │                 │  + X-Api-Key           │                │              │
│  (baseURL:  │                 │  + CF headers          │                │              │
│   '/api')   │                 │  Preserva headers      │                │              │
│             │◀──response────  │  del browser           │◀──response──   │              │
└─────────────┘                 ├───────────────────────┤                 └──────────────┘
                                │  Auth Redirects:       │
                                │  - con token + publica │
                                │    → dashboard         │
                                │  - sin token + proteg. │
                                │    → login             │
                                └───────────────────────┘

                                ┌───────────────────────┐
│  serverHttp │──directo──────▶ │  Backend API /v1/...  │  (sin proxy, server-to-server)
│  (baseURL:  │                 │  Sin interceptors —    │
│   host/v1)  │                 │  sin X-Api-Key         │
└─────────────┘                 └───────────────────────┘
```

**Principio clave:** El browser **nunca** hace peticiones directas al backend. Todas las peticiones van a `/api/v1/*` (same-origin), y el middleware las reescribe al backend real. Esto **elimina problemas de CORS** y permite inyectar el `X-Api-Key` sin exponerlo al cliente.

---

## Ubicacion y Convencion Next.js 16

En Next.js 16, el archivo de middleware se ubica en `src/proxy.ts` (antes era `middleware.ts` en la raiz o `src/middleware.ts`).

```
# Historico
middleware.ts          → Next.js 15 (convencion anterior)
src/proxy.ts           → Next.js 16 (convencion actual)
```

**Commit de migracion:** `83c2137 fix: migrate middleware.ts to proxy.ts for Next.js 16 compatibility`

El archivo debe:
- Exportar una funcion `default` que recibe `NextRequest`
- Exportar un `config` con `matcher` para definir que rutas intercepta
- No necesita registrarse en `next.config.mjs`

---

## Codigo Completo del Proxy

```typescript
// src/proxy.ts

import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

import { getRefreshTokenFromRequest } from '@/src/common/application/helpers/session';
import {
  LOGIN_REDIRECT_PATH,
  PUBLIC_ROUTES,
} from '@/src/common/domain/constants';

// Define que rutas intercepta el middleware
export const config = {
  matcher: [
    // Todas las rutas excepto assets estaticos
    '/((?!_next/|_vercel|.*\\..*|icons/|config/|images/).*)',
    // Explicitamente las rutas de API v1
    '/api/v1/:path*',
  ],
};

export default async function middleware(req: NextRequest) {
  const url = req.nextUrl;

  // ─── PROXY: reenviar /api/v1/* al backend ───
  if (url.pathname.startsWith('/api/v1/')) {
    const backendPath = url.pathname.replace(/^\/api/, '');
    const backendUrl = new URL(
      backendPath + url.search,
      process.env.BACKEND_API_HOST
    );
    const requestHeaders = new Headers(req.headers);
    requestHeaders.set('X-Api-Key', process.env.BACKEND_API_KEY!);

    // Headers opcionales de Cloudflare Access (para backends protegidos por CF)
    if (process.env.CF_ACCESS_CLIENT_ID) {
      requestHeaders.set('CF-Access-Client-Id', process.env.CF_ACCESS_CLIENT_ID);
    }
    if (process.env.CF_ACCESS_CLIENT_SECRET) {
      requestHeaders.set('CF-Access-Client-Secret', process.env.CF_ACCESS_CLIENT_SECRET);
    }

    return NextResponse.rewrite(backendUrl, {
      request: { headers: requestHeaders },
    });
  }

  // ─── SKIP: API routes internas manejan su propia auth ───
  if (url.pathname.startsWith('/api/')) {
    return NextResponse.next();
  }

  // ─── AUTH REDIRECTS ───
  const refreshToken = getRefreshTokenFromRequest(req);

  // Usuario autenticado en ruta publica → redirige al dashboard
  if (refreshToken && PUBLIC_ROUTES.includes(url.pathname)) {
    return NextResponse.redirect(new URL(LOGIN_REDIRECT_PATH, req.url));
  }

  // Usuario no autenticado en ruta protegida → redirige al login
  if (!refreshToken && !PUBLIC_ROUTES.includes(url.pathname)) {
    return NextResponse.redirect(new URL(`/`, req.url));
  }

  return NextResponse.next();
}
```

---

## Proxy de Peticiones /api/v1/*

### Como funciona el rewrite

Cuando el browser hace una peticion a `/api/v1/dashboard/stats`, el middleware:

1. **Detecta** que el pathname empieza con `/api/v1/`
2. **Construye la URL del backend** eliminando el prefijo `/api`:
   - `/api/v1/dashboard/stats?from=2024-01` → `https://api.backend.com/v1/dashboard/stats?from=2024-01`
3. **Copia todos los headers** del request original (incluyendo `Authorization`, `X-Tenant`, `X-Client`)
4. **Inyecta** `X-Api-Key` y headers de Cloudflare
5. **Reescribe** la peticion con `NextResponse.rewrite()` — el browser no ve la URL real del backend

```typescript
// Transformacion de URL
const backendPath = url.pathname.replace(/^\/api/, '');
// '/api/v1/tenants/123' → '/v1/tenants/123'

const backendUrl = new URL(
  backendPath + url.search,    // '/v1/tenants/123?active=true'
  process.env.BACKEND_API_HOST // 'https://api.backend.com'
);
// Resultado: 'https://api.backend.com/v1/tenants/123?active=true'
```

### Que NO pasa por el proxy

Las API routes internas de Next.js (`/api/auth/*`) no pasan por el proxy:

```typescript
// /api/auth/login, /api/auth/refresh, etc. → pasan directo
if (url.pathname.startsWith('/api/')) {
  return NextResponse.next();
}
```

Estas rutas manejan su propia logica (ver `docs/auth.md`).

---

## Inyeccion de Headers

### Headers inyectados por el proxy

| Header | Valor | Proposito |
|--------|-------|-----------|
| `X-Api-Key` | `process.env.BACKEND_API_KEY` | Autenticacion server-to-server. **Nunca expuesto al browser.** |
| `CF-Access-Client-Id` | `process.env.CF_ACCESS_CLIENT_ID` | Cloudflare Access (opcional, solo si el backend esta detras de CF) |
| `CF-Access-Client-Secret` | `process.env.CF_ACCESS_CLIENT_SECRET` | Cloudflare Access (opcional) |

### Headers que vienen del browser (via axios interceptor)

Estos headers son inyectados por el interceptor de request de axios en el cliente (ver `docs/auth.md`) y el proxy los **preserva** automaticamente:

| Header | Valor | Origen |
|--------|-------|--------|
| `Authorization` | `Bearer {accessToken}` | Zustand session store |
| `X-Tenant` | `{tenant.slug}` | Zustand session store |
| `X-Client` | `web:app.tripto.web/latest:{version}` | Constante del cliente |
| `Content-Type` | `application/json` | Axios default |

### Flujo completo de headers

```
Browser (axios interceptor)          Proxy (middleware)              Backend
┌─────────────────────┐             ┌──────────────────┐           ┌──────────────┐
│ Authorization: Bear…│────────────▶│ Authorization ✓  │──────────▶│ Recibe:      │
│ X-Tenant: my-tenant │             │ X-Tenant ✓       │           │ Authorization│
│ X-Client: web:...   │             │ X-Client ✓       │           │ X-Tenant     │
│ Content-Type: json  │             │ Content-Type ✓   │           │ X-Client     │
│                     │             │ + X-Api-Key ★    │           │ X-Api-Key    │
│                     │             │ + CF-Access-* ★  │           │ CF-Access-*  │
└─────────────────────┘             └──────────────────┘           └──────────────┘
                                    ★ = inyectado por proxy
```

---

## Auth Redirects en Middleware

Ademas de hacer proxy, el middleware maneja redirects de autenticacion para paginas (no para API calls):

### Logica de redirect

```typescript
const refreshToken = getRefreshTokenFromRequest(req);
```

La funcion `getRefreshTokenFromRequest` (en `src/common/application/helpers/session.ts`):

```typescript
export function getRefreshTokenFromRequest(request: NextRequest): string | null {
  const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE_KEY)?.value;
  if (!refreshToken) return null;
  // Valida que el JWT no este expirado
  if (isTokenValid(refreshToken)) return refreshToken;
  // Si expiro, lo elimina
  request.cookies.delete(REFRESH_TOKEN_COOKIE_KEY);
  return null;
}
```

La funcion `isTokenValid` (en `src/common/application/helpers/jwt-token.ts`):

```typescript
export function isTokenValid(token: string): boolean {
  try {
    const decoded = jwtDecode<JwtPayload>(token);
    if (!decoded.exp) return false;
    const currentTime = Math.floor(Date.now() / 1000);
    return decoded.exp >= currentTime;
  } catch (error) {
    return false;
  }
}
```

### Tabla de redirects

| Condicion | Accion | Ejemplo |
|-----------|--------|---------|
| Tiene refresh token + ruta publica | Redirect a `/dashboard` | Usuario logueado visita `/` → va al dashboard |
| No tiene refresh token + ruta protegida | Redirect a `/` (login) | Usuario no logueado visita `/dashboard` → va al login |
| Tiene refresh token + ruta protegida | `NextResponse.next()` | Acceso normal |
| No tiene refresh token + ruta publica | `NextResponse.next()` | Acceso normal al login |

### Rutas publicas

```typescript
// src/common/domain/constants.ts
export const PUBLIC_ROUTES = [
  '/',                           // Login
  '/logout',
  '/forgot-password',
  '/register',
  '/api/auth/google/callback',
];
```

---

## Instancias de Axios y Quien Usa Cual

```typescript
// src/common/infrastructure/http/client.ts

// 1. SERVER-SIDE DIRECTO: Va al backend sin proxy
//    Usado por: authRepository (login, refresh, logout en API routes)
export const serverHttp = axios.create({
  baseURL: `${Settings.apiBaseUrl}/v1`,   // https://api.backend.com/v1
  timeout: 10000,
});

// 2. CLIENT-SIDE VIA PROXY: Pasa por el middleware
//    Usado por: dashboardRepository
export const localHttp = axios.create({
  baseURL: '/api',                         // /api/v1/... → proxy → backend
  timeout: 10000,
});
// + interceptor de request (headers) + interceptor de response (refresh 401)

// 3. CLIENT-SIDE VIA PROXY + AUTH: Igual que localHttp
//    Usado por: todos los demas repos (tenants, branches, users, etc.)
export const authHttp = axios.create({
  baseURL: '/api',                         // /api/v1/... → proxy → backend
});
// + interceptor de request (headers) + interceptor de response (refresh 401)
```

### Asignacion de repos a HTTP clients

```typescript
// src/common/infrastructure/domain-context.ts

// serverHttp → directo al backend (server-side, API routes)
authRepository:         new HttpAuthRepository(serverHttp),
sessionRepository:      new HttpSessionRepository(serverHttp),

// localHttp → via proxy (client-side)
localAuthRepository:    new HttpAuthRepository(localHttp),
dashboardRepository:    new HttpDashboardRepository(localHttp),

// authHttp → via proxy + refresh interceptor (client-side, la mayoria)
tenantsRepository:      new HttpTenantRepository(authHttp),
branchRepository:       new HttpBranchRepository(authHttp),
userRepository:         new HttpTenantUserRepository(authHttp),
rolesRepository:        new HttpRolesRepository(authHttp),
transactionRepository:  new HttpTransactionRepository(authHttp),
tenantBalanceRepository: new HttpTenantBalanceRepository(authHttp),
tenantPayoutRepository: new HttpTenantPayoutRepository(authHttp),
bankAccountsRepository: new HttpTenantBankAccountsRepository(authHttp),
profileRepository:      new HttpProfileRepository(authHttp),
paymentRefundRepository: new HttpPaymentRefundRepository(authHttp),
posDeviceRepository:    new HttpPOSDeviceRepository(authHttp),
pendingIntentRepository: new HttpPaymentIntentRepository(authHttp),
paymentCheckoutRepository: new HttpPaymentCheckoutRepository(authHttp),
```

### Por que hay dos tipos de conexion?

| Tipo | HTTP Client | Ruta | Uso |
|------|-------------|------|-----|
| **Server-side directo** | `serverHttp` | `BACKEND_API_HOST/v1/...` | API routes de auth (`/api/auth/*`). Ya estan en el server, no necesitan proxy. **No tiene interceptors** — los endpoints de auth del backend no requieren `X-Api-Key`. |
| **Client-side via proxy** | `localHttp` / `authHttp` | `/api/v1/...` → proxy → backend | Peticiones del browser. El proxy inyecta `X-Api-Key`. Elimina CORS. |

---

## Relacion con el Sistema de Auth

El proxy y el sistema de auth (ver `docs/auth.md`) trabajan juntos:

1. **Login/Refresh/Logout** → usan API routes (`/api/auth/*`) que llaman al backend via `serverHttp` (directo). El proxy los deja pasar (`NextResponse.next()`).

2. **Peticiones normales** → usan `authHttp` o `localHttp` que envian a `/api/v1/*`. El proxy reescribe al backend, inyectando `X-Api-Key`.

3. **Si una peticion 401** → el interceptor de axios en `authHttp` llama a `/api/auth/refresh` (API route, no proxy) para renovar el token, y luego reintenta la peticion original (que vuelve a pasar por el proxy).

4. **Auth redirects** → el proxy lee la cookie `___RT9___` (refresh token) para decidir si redirigir paginas. No interfiere con las peticiones API.

```
Peticion normal:
Browser → authHttp → /api/v1/tenants → proxy.ts → rewrite → Backend

Login:
Browser → POST /api/auth/login → NextResponse.next() → API route → serverHttp → Backend

Refresh (automatico en 401):
Browser → POST /api/auth/refresh → NextResponse.next() → API route → serverHttp → Backend

Pagina protegida:
Browser → GET /dashboard → proxy.ts → tiene cookie? → si → NextResponse.next() → SSR layout → refreshServerSession()
```

---

## Variables de Entorno

```env
# Requeridas
BACKEND_API_HOST=https://api.example.com    # URL del backend (sin /v1)
BACKEND_API_KEY=your-server-api-key          # API key para X-Api-Key

# Opcionales (solo si el backend esta detras de Cloudflare Access)
CF_ACCESS_CLIENT_ID=your-cf-client-id
CF_ACCESS_CLIENT_SECRET=your-cf-client-secret
```

---

## Diagrama de Flujo

```
Request entrante
       │
       ▼
¿Pathname empieza con /api/v1/?
   SI ──▶ PROXY
          │
          ├── Construye URL: BACKEND_API_HOST + pathname sin /api + query
          ├── Copia headers del browser
          ├── Inyecta X-Api-Key
          ├── Inyecta CF-Access-* (si configurado)
          └── NextResponse.rewrite(backendUrl)
                    │
                    ▼
              Backend recibe peticion
              con todos los headers
   
   NO
   │
   ▼
¿Pathname empieza con /api/?
   SI ──▶ NextResponse.next()
          (API routes internas: /api/auth/*)
   
   NO
   │
   ▼
Lee refresh token de cookie ___RT9___
(valida que JWT no este expirado)
       │
       ├── Tiene token + ruta publica
       │   → NextResponse.redirect('/dashboard')
       │
       ├── No tiene token + ruta protegida
       │   → NextResponse.redirect('/')
       │
       └── Otro caso
           → NextResponse.next()
```

---

## Checklist para Implementar en Otro Proyecto

### Dependencias

```bash
pnpm add next@^16 jwt-decode
```

### Archivos a crear

1. **`src/proxy.ts`** — El middleware con 3 responsabilidades:
   - Proxy `/api/v1/*` al backend con `NextResponse.rewrite()`
   - Inyectar `X-Api-Key` y headers opcionales
   - Auth redirects basados en cookies
2. **Helper `getRefreshTokenFromRequest`** — Lee y valida la cookie de refresh token
3. **Helper `isTokenValid`** — Decodifica JWT y verifica expiracion
4. **Constantes** — `PUBLIC_ROUTES`, `LOGIN_REDIRECT_PATH`, cookie keys
5. **HTTP Clients** (axios):
   - `serverHttp` → directo al backend (server-side)
   - `localHttp` / `authHttp` → via proxy `/api` (client-side)

### Patron de matcher

```typescript
export const config = {
  matcher: [
    // Todas las rutas excepto archivos estaticos
    '/((?!_next/|_vercel|.*\\..*|icons/|config/|images/).*)',
    // Rutas de API que quieres proxear
    '/api/v1/:path*',
  ],
};
```

### Patrones clave

- [ ] `NextResponse.rewrite()` para proxy transparente (el browser no ve la URL real)
- [ ] `new Headers(req.headers)` para preservar todos los headers del browser
- [ ] Inyectar `X-Api-Key` solo en el middleware (nunca en el cliente)
- [ ] Separar rutas de API internas (`/api/auth/*`) del proxy (`/api/v1/*`)
- [ ] Validar JWT del refresh token en middleware para auth redirects
- [ ] Eliminar cookie expirada si el JWT ya no es valido
- [ ] Dos tipos de HTTP client: directo (server) y via proxy (client)

### Beneficios del patron proxy

- **Sin CORS:** Todas las peticiones son same-origin
- **Seguridad:** `X-Api-Key` nunca se expone al browser
- **Cloudflare Access:** Headers de CF se inyectan transparentemente
- **Simplicidad:** Los repos del cliente no necesitan saber la URL del backend
- **Auth centralizado:** Redirects de auth en un solo lugar
