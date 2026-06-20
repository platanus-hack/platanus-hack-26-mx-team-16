/**
 * E5 · identidad del actor staff en el cliente.
 *
 * El backend identifica al staff como `staff:<staff_uuid>` (uuid de la fila
 * `staff_users`, NO el `users.uuid` de la sesión), y la superficie /staff/v1
 * no expone ese uuid directamente. Lo aprendemos del primer claim exitoso
 * (la respuesta trae `claimedBy` con nuestro actor) y lo recordamos para
 * poder distinguir "mi lock" de "lock de otro" en la cola.
 */

const STORAGE_KEY = "doxiq:staff:actor";

export function getStaffActor(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function rememberStaffActor(actor: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, actor);
  } catch {
    // localStorage indisponible (p. ej. modo privado) — sin consecuencia:
    // solo perdemos el chip "Tuya"; claim/release siguen funcionando.
  }
}
