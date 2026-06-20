import type { RawEmailAddress } from "@/src/domain/entities/email-address";
import type { RawPhoneNumber } from "@/src/domain/entities/phone-number";

export interface User {
  uuid: string;
  username: string;
  firstName?: string | null;
  lastName?: string | null;
  phoneNumber?: RawPhoneNumber | null;
  emailAddress?: RawEmailAddress | null;
  photoUrl?: string | null;
  isSuperuser?: boolean;
  /** E5 · ADR 0001: fila activa en `staff_users` (consola /staff). */
  isStaff?: boolean;
  /** `staff_analyst_l1` | `staff_admin` — gatea la vista de audit. */
  staffRole?: string | null;
}

export const emptyUser: User = {
  uuid: "",
  username: "",
};
