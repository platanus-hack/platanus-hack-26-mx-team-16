export enum ConnectionProvider {
  WEBHOOK = "WEBHOOK",
  SLACK = "SLACK",
  EMAIL = "EMAIL",
  WHATSAPP = "WHATSAPP",
  DRIVE = "DRIVE",
  HTTP = "HTTP",
}

export enum ConnectionCapability {
  RECEIVE = "RECEIVE",
  SEND = "SEND",
  LOOKUP = "LOOKUP",
}

export enum ConnectionStatus {
  CONNECTED = "CONNECTED",
  ERROR = "ERROR",
  EXPIRED = "EXPIRED",
  REVOKED = "REVOKED",
}

/** Org-level connection account (mirrors backend connections module §2.1). */
export interface ConnectionAccount {
  uuid: string;
  tenantId: string;
  provider: ConnectionProvider;
  displayName: string;
  capabilities: ConnectionCapability[];
  status: ConnectionStatus;
  config: Record<string, unknown>;
  hasSecret: boolean;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface CreateConnectionPayload {
  provider: ConnectionProvider;
  displayName: string;
  capabilities?: ConnectionCapability[];
  config?: Record<string, unknown>;
  secret?: string | null;
}
