/// <reference path="../.astro/types.d.ts" />
/// <reference types="astro/client" />

declare namespace App {
  interface Locals {
    session?: {
      userId: string;
      email: string;
      name: string;
      role: string;
      tenantId?: string;
      expiresAt: number;
    };
  }
}

interface ImportMetaEnv {
  readonly BACKEND_API_HOST: string;
  readonly PUBLIC_SITE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
