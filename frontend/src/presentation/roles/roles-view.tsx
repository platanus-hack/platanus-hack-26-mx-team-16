"use client";

import { Plus, Shield } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import {
  useCreateRoleMutation,
  useDeleteRoleMutation,
  useRolesQuery,
  useUpdateRoleMutation,
} from "@/src/application/hooks/queries/roles";
import { usePermissions } from "@/src/application/hooks/use-permissions";
import type { TenantRole } from "@/src/domain/entities/tenants/tenant-role";
import type {
  CreateTenantRolePayload,
  UpdateTenantRolePayload,
} from "@/src/domain/repositories/tenant-role";
import { ConfirmDeleteDialog } from "@/src/presentation/components/common/confirm-delete-dialog";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import { Button } from "@/src/presentation/components/ui/button";
import { FullPageSpinner } from "@/src/presentation/components/ui/spinner";
import { CreateRoleDialog } from "./create-role-dialog";
import { EditRoleDialog } from "./edit-role-dialog";
import { RoleCard } from "./role-card";

export function RolesView() {
  const t = useTranslations("Roles");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingRole, setEditingRole] = useState<TenantRole | null>(null);
  const [deletingRoleId, setDeletingRoleId] = useState<string | null>(null);
  const { hasPermission } = usePermissions();
  const canCreate = hasPermission("tenant_roles.create");

  const { data: roles = [], isLoading, error } = useRolesQuery();
  const createMutation = useCreateRoleMutation();
  const updateMutation = useUpdateRoleMutation();
  const deleteMutation = useDeleteRoleMutation();

  const handleCreate = async (payload: CreateTenantRolePayload) => {
    await createMutation.mutateAsync(payload);
    setShowCreateDialog(false);
  };

  const handleEdit = (uuid: string) => {
    const role = roles.find((r: TenantRole) => r.uuid === uuid);
    if (role) setEditingRole(role);
  };

  const handleEditSubmit = async (
    uuid: string,
    payload: UpdateTenantRolePayload
  ) => {
    await updateMutation.mutateAsync({ uuid, payload });
    setEditingRole(null);
  };

  const handleDeleteConfirm = async () => {
    if (!deletingRoleId) return;
    await deleteMutation.mutateAsync(deletingRoleId);
    setDeletingRoleId(null);
  };

  const deletingRole = deletingRoleId
    ? roles.find((r: TenantRole) => r.uuid === deletingRoleId)
    : null;

  const dialogs = (
    <>
      <CreateRoleDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSubmit={handleCreate}
      />
      <EditRoleDialog
        role={editingRole}
        open={editingRole !== null}
        onOpenChange={(open) => {
          if (!open) setEditingRole(null);
        }}
        onSubmit={handleEditSubmit}
      />
      <ConfirmDeleteDialog
        open={deletingRoleId !== null}
        onOpenChange={(open) => {
          if (!open) setDeletingRoleId(null);
        }}
        onConfirm={handleDeleteConfirm}
        title={t("deleteTitle")}
        description={
          deletingRole
            ? t("deleteDescription", { name: deletingRole.name })
            : t("deleteDescriptionFallback")
        }
      />
    </>
  );

  if (isLoading) return <FullPageSpinner />;

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-100">
        <div className="text-destructive">{error.message}</div>
      </div>
    );
  }

  if (roles.length === 0) {
    return (
      <>
        <div className="flex flex-1 items-center justify-center">
          <EmptyState
            icon={Shield}
            title={t("emptyTitle")}
            description={t("emptyDescription")}
            actionLabel={canCreate ? t("create") : undefined}
            onAction={canCreate ? () => setShowCreateDialog(true) : undefined}
          />
        </div>
        {dialogs}
      </>
    );
  }

  return (
    <>
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">{t("title")}</h2>
            <p className="text-muted-foreground text-sm mt-1">
              {t("description")}
            </p>
          </div>
          <Button
            onClick={() => setShowCreateDialog(true)}
            className="gap-2"
            disabled={!canCreate}
          >
            <Plus className="h-4 w-4" />
            {t("create")}
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {roles.map((role: TenantRole) => (
            <RoleCard
              key={role.uuid}
              role={role}
              onEdit={handleEdit}
              onDelete={setDeletingRoleId}
            />
          ))}
        </div>
      </div>
      {dialogs}
    </>
  );
}
