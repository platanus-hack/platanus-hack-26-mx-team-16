/**
 * react-query for Owliver — there is NO separate provider to mount. The root
 * `app/layout.tsx` already wraps the whole tree in `QueryProvider`
 * (`@/src/application/providers/query-provider`), so every Owliver hook
 * (`useRanking`, `useWatchlist`, …) shares that single `QueryClient`.
 *
 * This module re-exports it for discoverability + centralizes the query keys, so
 * screen agents have ONE owliver-scoped entry point. Do not create a second
 * provider — nesting `QueryClientProvider` would fragment the cache.
 */
export { QueryProvider } from "@/src/application/providers/query-provider";
export { owliverKeys } from "../hooks/query-keys";
