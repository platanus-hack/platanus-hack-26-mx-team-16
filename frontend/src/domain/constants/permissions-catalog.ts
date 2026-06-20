export interface PermissionDefinition {
  code: string;
  label: string;
}

export interface PermissionCategory {
  id: string;
  label: string;
  permissions: PermissionDefinition[];
}

export const PERMISSIONS_CATALOG: PermissionCategory[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    permissions: [{ code: "dashboard.view", label: "Ver dashboard" }],
  },
  {
    id: "tenant_roles",
    label: "Roles",
    permissions: [
      { code: "tenant_roles.view", label: "Ver roles" },
      { code: "tenant_roles.create", label: "Crear roles" },
      { code: "tenant_roles.update", label: "Actualizar roles" },
      { code: "tenant_roles.delete", label: "Eliminar roles" },
      { code: "tenant_roles.assign", label: "Asignar roles" },
    ],
  },
  {
    id: "tenant_users",
    label: "Usuarios",
    permissions: [
      { code: "tenant_users.view", label: "Ver usuarios" },
      { code: "tenant_users.create", label: "Crear usuarios" },
      { code: "tenant_users.update", label: "Actualizar usuarios" },
      { code: "tenant_users.delete", label: "Eliminar usuarios" },
    ],
  },
  {
    id: "tenant_settings",
    label: "Configuraciones",
    permissions: [
      {
        code: "tenant_settings.update",
        label: "Actualizar configuraciones",
      },
    ],
  },
  {
    id: "workflows",
    label: "Workflows",
    permissions: [
      { code: "workflows.view", label: "Ver workflows" },
      { code: "workflows.create", label: "Crear workflows" },
      { code: "workflows.update", label: "Actualizar workflows" },
      { code: "workflows.delete", label: "Eliminar workflows" },
      { code: "workflows.view_usage", label: "Ver uso de workflows" },
      {
        code: "workflows.add_integration",
        label: "Agregar integración a workflows",
      },
    ],
  },
];

export const ALL_PERMISSION_CODES = PERMISSIONS_CATALOG.flatMap((cat) =>
  cat.permissions.map((p) => p.code)
);
