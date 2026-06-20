"use client";

import { Plus, Trash2 } from "lucide-react";
import { useOnboardTenantWizardStore } from "@/src/application/stores/onboard-tenant-wizard-store";
import { Button } from "@/src/presentation/components/ui/button";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";
import { Switch } from "@/src/presentation/components/ui/switch";

const ROLE_OPTIONS = [
  { slug: "admin", label: "Admin" },
  { slug: "member", label: "Member" },
] as const;

export function StepMembers() {
  const members = useOnboardTenantWizardStore((s) => s.members);
  const skipEmail = useOnboardTenantWizardStore((s) => s.skipEmail);
  const addMember = useOnboardTenantWizardStore((s) => s.addMember);
  const updateMember = useOnboardTenantWizardStore((s) => s.updateMember);
  const removeMember = useOnboardTenantWizardStore((s) => s.removeMember);
  const setSkipEmail = useOnboardTenantWizardStore((s) => s.setSkipEmail);

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <Label className="text-xs font-medium">Miembros a invitar</Label>
          <p className="text-xs text-muted-foreground">
            Recibirán un correo con un enlace de un solo uso. El superusuario
            creador se incluye automáticamente.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0 pt-1">
          <Switch
            id="skip-email"
            checked={skipEmail}
            onCheckedChange={setSkipEmail}
          />
          <Label
            htmlFor="skip-email"
            className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground"
          >
            No enviar correos
          </Label>
        </div>
      </div>

      <div className="space-y-2">
        {members.map((m) => (
          <div key={m.rowId} className="flex items-center gap-2">
            <Input
              type="email"
              placeholder="alguien@empresa.com"
              value={m.email}
              onValueChange={(value) =>
                updateMember(m.rowId, { email: value })
              }
              className="flex-1"
            />
            <Select
              value={m.roleSlug}
              onValueChange={(value) => {
                if (value)
                  updateMember(m.rowId, {
                    roleSlug: value as "admin" | "member",
                  });
              }}
            >
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ROLE_OPTIONS.map((role) => (
                  <SelectItem key={role.slug} value={role.slug}>
                    {role.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => removeMember(m.rowId)}
              aria-label="Eliminar miembro"
              disabled={members.length <= 1}
              className="text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={addMember}
          className="gap-2"
        >
          <Plus className="h-3.5 w-3.5" />
          Agregar miembro
        </Button>
      </div>
    </div>
  );
}
