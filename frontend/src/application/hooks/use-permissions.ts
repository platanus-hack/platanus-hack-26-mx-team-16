import { useSession } from "@/src/application/contexts/session";

export function usePermissions() {
  const { tenantRole } = useSession();

  const isOwner = tenantRole?.isOwner ?? false;

  function hasPermission(code: string): boolean {
    if (isOwner) return true;
    return tenantRole?.permissions.some((p) => p.code === code) ?? false;
  }

  function hasPermissions(codes: string[]): boolean {
    if (isOwner) return true;
    return codes.every((code) =>
      tenantRole?.permissions.some((p) => p.code === code)
    );
  }

  return { hasPermission, hasPermissions, isOwner };
}
