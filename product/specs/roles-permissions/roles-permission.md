---
feature: roles-permissions
type: spec
status: implemented
coverage: 85
audited: 2026-06-16
---

# Roles y Permisos — Doxiq

## Resumen General

El sistema de roles y permisos opera a nivel de **tenant**. Cada tenant tiene sus propios roles, y cada rol contiene una lista de permisos (strings) que determinan las acciones permitidas para los usuarios asignados a ese rol.

### Modelo de Datos

```
Tenant
  └── TenantRole (name, slug, permissions[], status, is_owner)
        └── TenantUser (usuario asignado al rol)
```

**Campos principales de `TenantRole`:**

| Campo         | Tipo               | Descripcion                                      |
|---------------|--------------------|-------------------------------------------------|
| `uuid`        | UUID               | Identificador unico                              |
| `tenant_id`   | UUID               | Tenant al que pertenece                          |
| `name`        | str                | Nombre visible del rol                           |
| `slug`        | str                | Identificador URL-safe (auto-generado, unico por tenant) |
| `permissions` | list[str]          | Lista de permisos asignados                      |
| `status`      | TenantRoleStatus   | `ACTIVE` o `INACTIVE`                            |
| `is_owner`    | bool               | Rol de propietario (acceso total implicito)      |
| `icon_url`    | str \| None        | Icono opcional para la UI                        |

**Entidad:** `backend/src/common/domain/entities/tenants/tenant_role.py`

**Roles predeterminados (bootstrap via `roles/bootstrap`):**
- **Owner** — `is_owner=True`, acceso total implicito, sin permisos explicitos
- **Staff** — Rol de empleado base, sin permisos por defecto
- **Anonymous** — Rol de invitado, sin permisos por defecto

**Roles predeterminados (seed via `DEFAULT_TENANT_ROLES` en `permissions/roles.py`):**
- **Administrador** (`admin`) — Todos los permisos (`FULL_PERMISSIONS`)
- **Miembro** (`member`) — Solo `dashboard.view`

> **Nota:** El bootstrap y los default roles son mecanismos independientes. Verificar si ambos deben coexistir o unificarse.

---

## Catalogo de Permisos

Los permisos se representan como strings con formato `namespace.action`.

**Archivo:** `backend/src/common/domain/permissions/catalog.py`
**Namespaces:** `backend/src/common/domain/permissions/namespaces/`

| Categoria          | Namespace          | Permisos disponibles                                          |
|--------------------|--------------------|---------------------------------------------------------------|
| Dashboard          | `dashboard`        | `view`                                                        |
| Roles              | `tenant_roles`     | `view`, `create`, `update`, `delete`, `assign`                |
| Usuarios           | `tenant_users`     | `view`, `create`, `update`, `delete`                          |
| Configuraciones    | `tenant_settings`  | `update`                                                      |
| Workflows          | `workflows`        | `view`, `create`, `update`, `delete`, `view_usage`, `add_integration` |

**Formato:** `namespace.action` (ej. `tenant_roles.create`, `workflows.view`)

**Total:** 17 permisos

### Verificacion de Permisos

**Archivo:** `backend/src/common/domain/permissions/checker.py`

```python
check_tenant_permission(tenant_user, permissions) -> bool
```

- Si `PERMISSIONS_ENABLED` es `False`, siempre retorna `True` (bypass para desarrollo)
- Si el usuario no tiene los permisos requeridos, lanza `InsufficientPermissionsError`

---

## Endpoints de la API (Backend)

**Estado:** Ya implementados en `backend/src/tenants/presentation/`
**Base path:** `/v1/tenants`

### Tenants

| Metodo | Path                     | Descripcion           |
|--------|--------------------------|----------------------|
| POST   | `/`                      | Registrar tenant     |
| PUT    | `/{tenant_id}`           | Actualizar tenant    |

### Roles (CRUD completo)

| Metodo | Path                     | Permiso requerido       | Descripcion                              |
|--------|--------------------------|------------------------|------------------------------------------|
| GET    | `/roles`                 | `tenant_roles.view`    | Listar roles del tenant                  |
| POST   | `/roles`                 | `tenant_roles.create`  | Crear rol                                |
| POST   | `/roles/bootstrap`       | —                      | Crear roles predeterminados              |
| GET    | `/roles/{role_id}`       | `tenant_roles.view`    | Obtener detalle de un rol                |
| PUT    | `/roles/{role_id}`       | `tenant_roles.update`  | Actualizar rol                           |
| DELETE | `/roles/{role_id}`       | `tenant_roles.delete`  | Eliminar rol                             |

### Usuarios del Tenant

| Metodo | Path                              | Permiso requerido       | Descripcion                    |
|--------|-----------------------------------|------------------------|--------------------------------|
| GET    | `/users/stats`                    | `tenant_users.view`    | Estadisticas de usuarios       |
| GET    | `/users`                          | `tenant_users.view`    | Listar usuarios del tenant     |
| POST   | `/users`                          | `tenant_users.create`  | Crear usuario en tenant        |
| GET    | `/users/{tenant_user_id}`         | `tenant_users.view`    | Detalle de un usuario          |
| PUT    | `/users/{tenant_user_id}`         | `tenant_users.update`  | Actualizar usuario             |
| DELETE | `/users/{tenant_user_id}`         | `tenant_users.delete`  | Eliminar usuario               |

### Permisos

| Metodo | Path                     | Descripcion                                       |
|--------|--------------------------|--------------------------------------------------|
| POST   | `/permissions/missing`   | Validar permisos contra `FULL_PERMISSIONS`        |

### Endpoint faltante: Catalogo de Permisos

> **TODO:** Implementar `GET /v1/tenants/permissions` que retorne el catalogo completo de categorias y permisos disponibles para asignar a roles.

**Respuesta esperada:**

```json
{
  "data": {
    "categories": [
      {
        "id": "dashboard",
        "label": "Dashboard",
        "permissions": [
          { "code": "dashboard.view", "label": "Ver dashboard" }
        ]
      },
      {
        "id": "tenant_roles",
        "label": "Roles",
        "permissions": [
          { "code": "tenant_roles.view", "label": "Ver roles" },
          { "code": "tenant_roles.create", "label": "Crear roles" },
          { "code": "tenant_roles.update", "label": "Actualizar roles" },
          { "code": "tenant_roles.delete", "label": "Eliminar roles" },
          { "code": "tenant_roles.assign", "label": "Asignar roles" }
        ]
      },
      {
        "id": "tenant_users",
        "label": "Usuarios",
        "permissions": [
          { "code": "tenant_users.view", "label": "Ver usuarios" },
          { "code": "tenant_users.create", "label": "Crear usuarios" },
          { "code": "tenant_users.update", "label": "Actualizar usuarios" },
          { "code": "tenant_users.delete", "label": "Eliminar usuarios" }
        ]
      },
      {
        "id": "tenant_settings",
        "label": "Configuraciones",
        "permissions": [
          { "code": "tenant_settings.update", "label": "Actualizar configuraciones" }
        ]
      },
      {
        "id": "workflows",
        "label": "Workflows",
        "permissions": [
          { "code": "workflows.view", "label": "Ver workflows" },
          { "code": "workflows.create", "label": "Crear workflows" },
          { "code": "workflows.update", "label": "Actualizar workflows" },
          { "code": "workflows.delete", "label": "Eliminar workflows" },
          { "code": "workflows.view_usage", "label": "Ver uso de workflows" },
          { "code": "workflows.add_integration", "label": "Agregar integracion a workflows" }
        ]
      }
    ]
  }
}
```

---

## UI del CRUD de Roles (Frontend)

**Estado:** No implementado. Solo existe la entidad `TenantRole` en `frontend/src/domain/entities/tenants/tenant-role.ts`.

### Estructura de Archivos a Crear

Siguiendo la arquitectura Clean Architecture del frontend:

```
frontend/src/
├── domain/
│   ├── entities/tenants/tenant-role.ts          # Ya existe
│   ├── repositories/tenant-role-repository.ts   # Interfaz del repositorio
│   └── responses/tenant-role-responses.ts       # Tipos de respuesta API
├── application/
│   ├── hooks/
│   │   ├── use-roles.ts                         # Hook para listar roles
│   │   ├── use-available-permissions.ts         # Hook para catalogo de permisos
│   │   └── use-role-mutations.ts                # Hooks de create/update/delete
│   └── stores/roles-store.ts                    # Zustand store (si necesario)
├── infrastructure/
│   └── repositories/http-tenant-role-repository.ts  # Implementacion HTTP
└── presentation/
    └── roles/
        ├── components/
        │   ├── create-role-dialog.tsx            # Dialog de creacion
        │   ├── edit-role-dialog.tsx              # Dialog de edicion
        │   ├── permission-selector.tsx           # Selector modal de permisos
        │   ├── selected-permissions.tsx          # Badges de permisos seleccionados
        │   ├── role-card.tsx                     # Tarjeta individual de rol
        │   ├── roles-grid.tsx                    # Grid responsivo
        │   ├── roles-header.tsx                  # Header con boton crear
        │   ├── roles-empty-state.tsx             # Estado vacio
        │   └── role-actions-menu.tsx             # Menu dropdown (editar/eliminar)
        └── roles-view.tsx                        # Vista principal
```

**Pagina:** Agregar ruta en `frontend/src/app/(protected)/settings/roles/page.tsx`

### Componentes Principales

#### Pagina de Roles (`/settings/roles`)
- Protegida por permisos (`tenant_roles.view`)
- Grid responsivo de tarjetas de roles (1-4 columnas segun pantalla)
- Header con boton "Crear Rol"
- Estado vacio con CTA cuando no hay roles

#### RoleCard
- Nombre del rol, estado (badge ACTIVE/INACTIVE), permisos como badges agrupados por categoria
- Menu de acciones (dropdown): Editar, Eliminar

#### CreateRoleDialog / EditRoleDialog
- Dialogs modales con shadcn/ui
- Formulario con React Hook Form + validacion Zod
- Campos: Nombre (min 2 chars), Estado (select), Permisos (selector interactivo)
- Notificaciones toast (Sonner) al crear/editar

#### PermissionSelector
- Dialog modal con permisos agrupados por categoria
- Busqueda/filtro de permisos
- Cada permiso con `code` y `label`

#### SelectedPermissions
- Badges agrupados por categoria
- Modo lectura y modo editable (con boton eliminar por permiso)

### Stack UI
- **Componentes:** shadcn/ui (Dialog, Form, Select, Input, Badge, Button)
- **Formularios:** React Hook Form + Zod
- **Estado servidor:** TanStack React Query
- **Estado cliente:** Zustand (si necesario)
- **Notificaciones:** Sonner
- **Iconos:** Lucide React

### Flujo de Creacion

```
1. Usuario hace clic en "Crear Rol" (RolesHeader)
2. Se abre CreateRoleDialog
3. Ingresa nombre y selecciona estado
4. Abre PermissionSelector para elegir permisos
5. Permisos seleccionados se muestran como badges (SelectedPermissions)
6. Al confirmar → POST /v1/tenants/roles
7. Toast de exito, se refresca la lista
```

### Flujo de Edicion

```
1. Usuario abre menu de acciones en un RoleCard
2. Selecciona "Editar" → se abre EditRoleDialog con datos precargados
3. Modifica campos y/o permisos
4. Al confirmar → PUT /v1/tenants/roles/{role_id}
5. Toast de exito, se refresca la lista
```

---

## Plan de Implementacion

### Backend (poco trabajo, casi todo existe)

1. **Crear endpoint `GET /v1/tenants/permissions`** — Nuevo endpoint que genera la respuesta del catalogo agrupado por categorias a partir de `PERMISSIONS_CATALOG`
   - Archivo: `backend/src/tenants/presentation/endpoints/` (nuevo endpoint)
   - Registrar en: `backend/src/tenants/presentation/router.py`

2. **Revisar consistencia de roles predeterminados** — `TenantRoleMeta.owner/staff/anonymous` vs `DEFAULT_TENANT_ROLES` (admin/member). Decidir cual se usa.

### Frontend (trabajo principal)

3. **Domain layer** — Crear repositorio interface y tipos de respuesta
4. **Infrastructure layer** — Implementar HTTP repository para roles y permisos
5. **Application layer** — Hooks con React Query para CRUD de roles y catalogo de permisos
6. **Presentation layer** — Todos los componentes UI listados arriba
7. **Routing** — Agregar pagina `/roles`