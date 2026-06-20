# VNext Web

Plataforma de procesamiento y validación de documentos con IA construida con Next.js 16, React 19 y TypeScript.

## Tech Stack

- Next.js 16 (App Router) + React 19
- TypeScript + Tailwind CSS 4
- shadcn/ui (base-vega) + @base-ui/react
- Biome (linting + formatting)
- Zustand (state management) + React Context
- Zod (validation)
- Axios (HTTP client)
- react-hook-form
- pnpm

## Desarrollo

```bash
# Instalar dependencias
pnpm install

# Servidor de desarrollo (http://localhost:3000)
pnpm dev

# Build producción
pnpm build

# Servidor producción
pnpm start
```

## Calidad de Código

```bash
# Lint + Format + Type check
pnpm check

# Corregir automáticamente
pnpm check:fix

# CI/CD
pnpm ci
```

**Comandos individuales:**
```bash
pnpm lint          # Revisar linting
pnpm lint:fix      # Corregir linting
pnpm format        # Formatear código
pnpm type-check    # Verificar tipos
```

## Estructura del Proyecto

```
src/
├── app/                           # Next.js App Router
│   ├── (protected)/              # Rutas protegidas
│   │   ├── layout.tsx           # Layout con sidebar
│   │   └── dashboard/           # Dashboard
│   ├── api/auth/                # API Routes de autenticación
│   │   ├── login/               # Login endpoint
│   │   ├── logout/              # Logout endpoint
│   │   └── refresh/             # Token refresh endpoint
│   └── globals.css              # Estilos globales
├── domain/                       # Capa de Dominio (DDD)
│   ├── entities/                # Entidades del dominio
│   ├── repositories/            # Interfaces de repositorios
│   ├── responses/               # Tipos de respuesta
│   └── errors/                  # Manejo de errores
├── application/                  # Capa de Aplicación (DDD)
│   ├── schemas/                 # Esquemas de validación (Zod)
│   └── contexts/                # Context API + Zustand stores
│       ├── session-store.ts     # Zustand store
│       └── session.tsx          # SessionProvider
├── infrastructure/               # Capa de Infraestructura (DDD)
│   ├── http/                    # Clientes HTTP (Axios)
│   ├── repositories/            # Implementación de repositorios
│   └── requests.ts              # Utilidades de requests
├── presentation/                 # Capa de Presentación (DDD)
│   ├── components/ui/           # shadcn/ui components
│   ├── common/                  # Layout components
│   │   ├── app-sidebar.tsx      # Sidebar component
│   │   ├── sidebar-config.ts    # Sidebar menu config
│   │   ├── nav-*.tsx            # Navigation components
│   │   └── app-shell.tsx        # App shell wrapper
│   └── auth/                    # Componentes de autenticación
│       └── auth-form.tsx        # Formulario de login
├── lib/                          # Utilidades
│   └── utils.ts                 # Helpers (cn)
├── utils/                        # Utilidades compartidas
│   └── http-error-handler.ts   # Manejo de errores HTTP
└── settings.ts                   # Configuración centralizada
proxy.ts                          # Next.js 16 Proxy (route protection)
```

## Configuración del Sidebar

Para editar el menú del sidebar, modifica `src/presentation/common/sidebar-config.ts`:

```typescript
export const sidebarConfig: SidebarConfig = {
  user: { name, email, avatar },
  teams: [...],
  navMain: [...],
  projects: [...]
}
```

## shadcn/ui

Agregar nuevos componentes:
```bash
npx shadcn@latest add [component-name]
```

Configuración: `base-vega` style, lucide icons, CSS variables

## Alias de Importación

```typescript
import { cn } from "@/src/lib/utils";
import { Button } from "@/src/presentation/components/ui/button";
import { AppSidebar } from "@/src/presentation/common/app-sidebar";
```

## Reglas de Código (Biome)

- No `var`, usar `const` o `let`
- Imports de tipos: `import type { Foo } from 'bar'`
- No `console.log()`, usar `console.warn()` o `console.error()`
- `===` en lugar de `==`
- Template strings sobre concatenación
- Arrow functions para callbacks
- Componentes auto-cerrados: `<Component />`
- `<Link>` en lugar de `<a>`
- `<Image>` en lugar de `<img>`

## Arquitectura DDD

El proyecto sigue los principios de **Domain-Driven Design (DDD)**:

- **Domain**: Entidades, interfaces de repositorios, tipos de error
- **Application**: Lógica de aplicación, validación (Zod), gestión de estado (Zustand)
- **Infrastructure**: Implementaciones de repositorios, clientes HTTP (Axios)
- **Presentation**: Componentes React, UI, formularios

## Sistema de Autenticación

Sistema de autenticación JWT completo con:

- **Tokens JWT**: Access token (10 min) + Refresh token (7 días)
- **HTTP-only Cookies**: Almacenamiento seguro contra XSS
- **Refresh Automático**: Interceptores de Axios renuevan tokens en 401
- **Gestión de Estado**: Zustand con persist + React Context
- **Validación**: Zod schemas para formularios
- **Protección de Rutas**: Proxy de Next.js 16 (reemplaza middleware)

### Flujo de Autenticación

1. Login → `/api/auth/login` → Cookies HTTP-only
2. Requests → Headers con token desde cookies
3. 401 Error → `/api/auth/refresh` → Nuevo access token
4. Logout → `/api/auth/logout` → Limpia cookies y store

### Rutas

- **Protegidas**: `/(protected)/*` (requiere autenticación)
- **Públicas**: `/` (login), `/api/auth/*`

## Variables de Entorno

Crear `.env.local`:

```env
# Backend API Configuration
NEXT_PUBLIC_BACKEND_API_HOST=http://localhost:8000
BACKEND_API_HOST=http://localhost:8000
BACKEND_API_KEY=your-api-key-here

# App Version
NEXT_PUBLIC_VERSION=1.0.0

# Node Environment
NODE_ENV=development

# Sentry (optional)
SENTRY_DSN=
```

## Fuentes

- **Figtree**: Primary sans-serif (`--font-sans`)
- **Geist Sans**: Secondary sans (`--font-geist-sans`)
- **Geist Mono**: Monospace (`--font-geist-mono`)

## Deployment

**Vercel:**
```bash
# Deploy automático desde GitHub
```

**Manual:**
```bash
pnpm build
pnpm start
```

**Docker:**
```bash
docker build -t vnext-web .
docker run -p 3000:3000 vnext-web
```

## Next.js 16 Migration Notes

Cambios importantes respecto a Next.js 15:

- **Middleware → Proxy**: `middleware.ts` deprecado, ahora se usa `proxy.ts`
  - Función `middleware()` → `proxy()`
  - Misma funcionalidad con nueva API

## Troubleshooting

```bash
# Limpiar instalación
pnpm store prune && rm -rf node_modules && pnpm install

# Limpiar build
rm -rf .next

# Verificar tipos
pnpm type-check

# Corregir código
pnpm check:fix
```

## Documentación

- [Guía de Migración Biome](./docs/BIOME_MIGRATION_GUIDE.md)
- [Mejores Prácticas](./docs/LINTING_BEST_PRACTICES.md)
- [Instrucciones Claude Code](AGENTS.md)

---

Construido con Next.js y shadcn/ui
