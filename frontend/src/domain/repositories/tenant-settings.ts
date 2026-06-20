import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { TenantSettingsResponse } from "@/src/domain/responses/tenant-settings";

export interface TenantSettingsRepository {
  get(): Promise<TenantSettingsResponse | ErrorFeeback>;
  update(name: string): Promise<TenantSettingsResponse | ErrorFeeback>;
  updateAvatar(file: File): Promise<TenantSettingsResponse | ErrorFeeback>;
  regenerateWebhookKey(): Promise<TenantSettingsResponse | ErrorFeeback>;
  deleteTenant(): Promise<{ success: boolean } | ErrorFeeback>;
}
