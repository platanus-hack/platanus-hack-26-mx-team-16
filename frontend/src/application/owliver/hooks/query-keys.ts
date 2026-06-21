/**
 * Centralized react-query keys for Owliver. Keeps cache invalidation consistent
 * across screens (the root `QueryProvider` in `app/layout.tsx` already wraps the
 * tree — Owliver hooks reuse that client).
 */
export const owliverKeys = {
  ranking: (country: string, filters?: Record<string, unknown>) =>
    ["owliver", "ranking", country, filters ?? {}] as const,
  scan: (id: string) => ["owliver", "scan", id] as const,
  findings: (id: string) => ["owliver", "scan", id, "findings"] as const,
  site: (id: string) => ["owliver", "site", id] as const,
  watchlist: () => ["owliver", "watchlist"] as const,
  alertPrefs: () => ["owliver", "me", "alerts"] as const,
} as const;
