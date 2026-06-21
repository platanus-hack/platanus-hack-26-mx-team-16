/**
 * Demo-fixtures switch (server-only).
 *
 * Owliver ships rich demo fixtures so screens render without a populated
 * backend. This flag controls whether those fixtures are still surfaced now that
 * the real endpoints are wired.
 *
 * DEFAULT: ON. The presentation must always have data even if few/no real scans
 * exist yet, so an UNSET env var keeps fixtures visible. To serve ONLY real
 * backend data (no demo rows, no silent fallback) set in the server env:
 *
 *     OWLIVER_USE_FIXTURES=0      # also accepts "false" / "off"
 *
 * Server-only: env vars without the `NEXT_PUBLIC_` prefix are not inlined into
 * the client bundle, so this never leaks the switch to the browser.
 */
import "server-only";

export function fixturesEnabled(): boolean {
  const v = process.env.OWLIVER_USE_FIXTURES?.trim().toLowerCase();
  return v !== "0" && v !== "false" && v !== "off";
}
