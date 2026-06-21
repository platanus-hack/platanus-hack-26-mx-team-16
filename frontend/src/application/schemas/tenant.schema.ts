import { z } from "zod";

// Create Tenant Form Schema — used by the /unassigned onboarding form where a
// user without an organization creates their first tenant (and becomes owner).
export const createTenantFormSchema = z.object({
  name: z
    .string()
    .trim()
    .min(2, { message: "El nombre debe tener al menos 2 caracteres" })
    .max(120, { message: "El nombre es demasiado largo" }),
  // ISO 3166-1 alpha-2 country code (matches the backend `CountryIsoCode`).
  countryCode: z.string().min(2, { message: "Selecciona un país" }),
});

export type CreateTenantFormData = z.infer<typeof createTenantFormSchema>;
