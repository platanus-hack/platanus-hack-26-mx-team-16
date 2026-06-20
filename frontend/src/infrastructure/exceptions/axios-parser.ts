import axios from "axios";
import { genericServerError } from "@/src/domain/errors/common";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";

export function errorFromAxios(
  error: unknown,
  fallbackMessage: string
): ErrorFeeback {
  if (axios.isAxiosError(error)) {
    const data: any = error.response?.data ?? {};
    return {
      errors: [
        {
          message: data?.message || fallbackMessage,
          code:
            error.response?.status?.toString() || data?.code || "UNKNOWN_ERROR",
        },
      ],
      validation: data?.validation || null,
    };
  }
  return genericServerError;
}
