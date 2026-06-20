export interface TenantSettings {
  uuid: string;
  name: string;
  tenantId: string;
  avatar: string | null;
  maxPages: number;
  webhookSignatureKey: string;
}
