/**
 * API envelope helpers (12-api §5). The backend wraps every success in a
 * camelCase envelope:
 *
 *   single    → { data: T, timestamp }
 *   paginated → { data: T[], pagination: { nextCursor, limit }, timestamp }
 *   error     → { errors: [{ code, message }], validation, timestamp }
 *
 * (The rate-limit handler diverges to `{ error, Retry-After }`.)
 *
 * These are isomorphic (no React, no fetch) so they're usable from BFF routes,
 * RSC, fixtures, and client hooks alike.
 */
import type { z } from "zod";

export type ApiError = { code: string; message: string };

export type ErrorEnvelope = {
  errors: ApiError[];
  validation: Record<string, unknown> | null;
  timestamp?: string;
};

export type DataEnvelope<T> = {
  data: T;
  timestamp?: string;
};

export type Pagination = {
  nextCursor: string | null;
  limit: number;
};

export type PageEnvelope<T> = {
  data: T[];
  pagination: Pagination;
  timestamp?: string;
};

export function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  return (
    typeof value === "object" &&
    value !== null &&
    "errors" in value &&
    Array.isArray((value as ErrorEnvelope).errors)
  );
}

/** Pull the first error message, with a fallback. */
export function firstErrorMessage(
  value: unknown,
  fallback = "Ocurrió un error"
): string {
  if (isErrorEnvelope(value) && value.errors[0]) {
    return value.errors[0].message || fallback;
  }
  return fallback;
}

/** First error code (for branching UI on `validation`/specific codes). */
export function firstErrorCode(value: unknown): string | null {
  if (isErrorEnvelope(value) && value.errors[0]) {
    return value.errors[0].code ?? null;
  }
  return null;
}

/** Wrap a payload in the single-data envelope (for BFF/fixtures). */
export function asData<T>(data: T, timestamp?: string): DataEnvelope<T> {
  return { data, timestamp: timestamp ?? new Date().toISOString() };
}

/** Wrap a list in the paginated envelope. */
export function asPage<T>(
  data: T[],
  pagination?: Partial<Pagination>
): PageEnvelope<T> {
  return {
    data,
    pagination: {
      nextCursor: pagination?.nextCursor ?? null,
      limit: pagination?.limit ?? data.length,
    },
    timestamp: new Date().toISOString(),
  };
}

/** Build an error envelope (for BFF error translation). */
export function asError(
  errors: ApiError[],
  validation: Record<string, unknown> | null = null
): ErrorEnvelope {
  return { errors, validation, timestamp: new Date().toISOString() };
}

/**
 * Parse `{ data }` against a zod schema and return the validated `data`.
 * Throws (zod) if the shape doesn't match — useful in BFF/RSC where a contract
 * drift should surface loudly rather than render garbage.
 */
export function parseData<T extends z.ZodTypeAny>(
  schema: T,
  envelope: unknown
): z.infer<T> {
  const data = (envelope as DataEnvelope<unknown>)?.data ?? envelope;
  return schema.parse(data);
}

/** Parse the `data[]` of a paginated envelope, preserving pagination. */
export function parsePage<T extends z.ZodTypeAny>(
  schema: T,
  envelope: unknown
): { data: z.infer<T>[]; pagination: Pagination } {
  const env = envelope as PageEnvelope<unknown>;
  const items = (env?.data ?? []).map((d) => schema.parse(d));
  return {
    data: items,
    pagination: env?.pagination ?? { nextCursor: null, limit: items.length },
  };
}
