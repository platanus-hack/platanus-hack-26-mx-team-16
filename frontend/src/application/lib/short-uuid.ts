/**
 * Return the first `length` hex chars of a UUID with the dashes stripped.
 * Useful as a compact, copy-safe identifier suffix (filenames, badges, etc.).
 *
 * `shortUuid("a1b2c3d4-e5f6-7890-abcd-ef1234567890", 10)` → `"a1b2c3d4e5"`
 */
export function shortUuid(uuid: string, length = 10): string {
  return uuid.replace(/-/g, "").slice(0, length);
}
