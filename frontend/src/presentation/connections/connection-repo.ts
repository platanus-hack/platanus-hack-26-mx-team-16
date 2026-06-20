import { HttpConnectionRepository } from "@/src/infrastructure/repositories/http-connection";

/** Single repository instance shared by the connections (integrations) UI. */
export const connectionRepo = new HttpConnectionRepository();

/** React Query key for the org-level connection accounts list. */
export const CONNECTIONS_QUERY_KEY = ["connections"] as const;
