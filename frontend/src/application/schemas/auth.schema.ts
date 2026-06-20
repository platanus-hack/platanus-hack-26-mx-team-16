import { z } from "zod";
import { TenantRoleStatus, TenantStatus } from "@/src/domain/enums/tenants";

// Value Objects
export const rawEmailAddressSchema = z.object({
  email: z.string().email(),
  isVerified: z.boolean(),
});

export const rawPhoneNumberSchema = z.object({
  dialCode: z.number(),
  phoneNumber: z.string(),
  isoCode: z.string(),
  prefix: z.string().nullable().optional(),
});

// User Schema
export const userSchema = z.object({
  uuid: z.string(),
  username: z.string(),
  firstName: z.string().nullable().optional(),
  lastName: z.string().nullable().optional(),
  phoneNumber: rawPhoneNumberSchema.nullable().optional(),
  emailAddress: rawEmailAddressSchema.nullable().optional(),
  photoUrl: z.string().nullable().optional(),
  isSuperuser: z.boolean().optional(),
  isStaff: z.boolean().optional(),
  staffRole: z.string().nullable().optional(),
});

// Tenant Schema
export const tenantSchema = z.object({
  uuid: z.string(),
  name: z.string(),
  slug: z.string(),
  timeZone: z.string(),
  countryCode: z.string(),
  currencyCode: z.string(),
  currencySymbol: z.string(),
  logoUrl: z.string().nullable().optional(),
  status: z.nativeEnum(TenantStatus),
  createdAt: z.string().nullable().optional(),
  updatedAt: z.string().nullable().optional(),
});

// TenantRole Schema
export const tenantRoleSchema = z.object({
  uuid: z.string(),
  tenantId: z.string(),
  name: z.string(),
  status: z.nativeEnum(TenantRoleStatus),
  permissions: z.array(z.record(z.string(), z.any())),
  iconUrl: z.string().nullable().optional(),
  isOwner: z.boolean().optional(),
});

// JwtSession Schema
export const jwtSessionSchema = z.object({
  accessToken: z.string(),
  refreshToken: z.string(),
  expiresIn: z.number().nullable().optional(),
  tokenType: z.string().nullable().optional(),
});

// TenantUserSession Schema
export const tenantUserSessionSchema = z.object({
  session: jwtSessionSchema,
  user: userSchema,
  tenant: tenantSchema,
  tenantRole: tenantRoleSchema,
});

// TenantUserContext Schema (sin session)
export const tenantUserContextSchema = z.object({
  user: userSchema,
  tenant: tenantSchema,
  tenantRole: tenantRoleSchema,
});

// Login Form Schema
export const loginFormSchema = z.object({
  email: z.string().email({ message: "Email inválido" }),
  password: z
    .string()
    .min(6, { message: "La contraseña debe tener al menos 6 caracteres" }),
});

export type LoginFormData = z.infer<typeof loginFormSchema>;
