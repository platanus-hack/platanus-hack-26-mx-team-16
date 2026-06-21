import { Settings } from "@/src/settings";

export const isServer = (): boolean => typeof window === "undefined";

export const getBackendHostname = () => {
  return Settings.apiBaseUrl;
};

export const getCommonHeaders = (
  tenantSlug?: string | null,
  accessToken?: string | null
) => {
  const version = Settings.version;
  const client = `web:app.owliver.web/latest:${version}`;

  let headers: Record<string, string> = {
    "X-Client": client,
  };

  if (tenantSlug) {
    headers = {
      ...headers,
      "X-Tenant": tenantSlug,
    };
  }

  if (accessToken) {
    headers = {
      ...headers,
      Authorization: `Bearer ${accessToken}`,
    };
  }

  if (isServer() && Settings.apiKey) {
    headers = {
      ...headers,
      "X-Api-Key": Settings.apiKey,
    };
  }

  return headers;
};
