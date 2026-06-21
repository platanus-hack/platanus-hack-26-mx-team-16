/**
 * Client-side URL normalization + host extraction for the scan form (§F5).
 *
 * IMPORTANT: this is UX/preview only — it shapes what the user sees ("Vas a
 * escanear: sat.gob.mx") and disables obviously-bad submits. The REAL SSRF
 * defense (private-range resolution, rebinding) is the backend's job
 * (01-legal-ethics §4). Never treat these as a security boundary.
 */

/**
 * Normalize a user-typed URL: prefix `https://` if no scheme, then parse with
 * the WHATWG `URL`. Returns the parsed URL or `null` if unparseable.
 */
export function normalizeUrl(input: string): URL | null {
  const trimmed = input.trim();
  if (!trimmed) return null;
  const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed)
    ? trimmed
    : `https://${trimmed}`;
  try {
    return new URL(withScheme);
  } catch {
    return null;
  }
}

/** Extract the lowercased hostname (e.g. "sat.gob.mx"), or `null`. */
export function extractHost(input: string): string | null {
  const url = normalizeUrl(input);
  if (!url) return null;
  return url.hostname.toLowerCase();
}

const PRIVATE_HOSTNAMES = new Set(["localhost", "0.0.0.0", "::1", "[::1]"]);

/** True if `host` is an IPv4 literal in a private/loopback/link-local range. */
function isPrivateIpv4(host: string): boolean {
  const m = host.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (!m) return false;
  const [a, b] = [Number(m[1]), Number(m[2])];
  if ([a, b, Number(m[3]), Number(m[4])].some((n) => n > 255)) return true;
  if (a === 10) return true; // 10.0.0.0/8
  if (a === 127) return true; // loopback
  if (a === 0) return true;
  if (a === 169 && b === 254) return true; // link-local
  if (a === 172 && b >= 16 && b <= 31) return true; // 172.16.0.0/12
  if (a === 192 && b === 168) return true; // 192.168.0.0/16
  return false;
}

/**
 * Heuristic: is this a routable public host worth submitting? Rejects
 * localhost, private IPv4 ranges, raw IPv6, and hostnames without a dot
 * (a bare label like "intranet" is almost never a public site).
 */
export function isLikelyPublicHost(input: string): boolean {
  const host = extractHost(input);
  if (!host) return false;
  if (PRIVATE_HOSTNAMES.has(host)) return false;
  if (host.startsWith("[")) return false; // raw IPv6 literal
  if (isPrivateIpv4(host)) return false;
  if (!host.includes(".")) return false; // bare label, no TLD
  if (host.endsWith(".local")) return false;
  return true;
}

/** True if the host belongs to the Mexican government zone (`.gob.mx`). */
export function isGovHost(input: string): boolean {
  const host = extractHost(input);
  if (!host) return false;
  return host === "gob.mx" || host.endsWith(".gob.mx");
}
