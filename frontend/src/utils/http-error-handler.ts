import type { AxiosError } from "axios";

import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";

/**
 * Maneja errores de respuesta HTTP y los convierte a ErrorFeeback
 * Sistema centralizado para todos los repositorios del proyecto
 */
export function handleHttpError(error: AxiosError): ErrorFeeback {
  // Si la respuesta del servidor contiene errores estructurados
  if (error.response?.data && typeof error.response.data === "object") {
    const data = error.response.data as any;

    // Si ya es un ErrorFeeback válido
    if (data.errors && Array.isArray(data.errors)) {
      return {
        errors: data.errors,
        validation: data.validation || null,
      };
    }
    if (data.message) {
      return {
        errors: [
          {
            code: `HTTP_${error.response.status}`,
            message: data.message,
          },
        ],
        validation: data.validation || null,
      };
    }
  }

  // Crear ErrorFeeback genérico basado en el status HTTP
  const statusCode = error.response?.status || 0;
  let message = "Error desconocido";
  let code = "UNKNOWN_ERROR";

  switch (statusCode) {
    case 400:
      message = "Solicitud inválida";
      code = "BAD_REQUEST";
      break;
    case 401:
      message = "No autorizado";
      code = "UNAUTHORIZED";
      break;
    case 403:
      message = "Acceso denegado";
      code = "FORBIDDEN";
      break;
    case 404:
      message = "Recurso no encontrado";
      code = "NOT_FOUND";
      break;
    case 409:
      message = "Conflicto de datos";
      code = "CONFLICT";
      break;
    case 422:
      message = "Datos de validación incorrectos";
      code = "VALIDATION_ERROR";
      break;
    case 429:
      message = "Demasiadas solicitudes";
      code = "RATE_LIMIT";
      break;
    case 500:
      message = "Error interno del servidor";
      code = "INTERNAL_SERVER_ERROR";
      break;
    case 502:
      message = "Gateway incorrecto";
      code = "BAD_GATEWAY";
      break;
    case 503:
      message = "Servicio no disponible";
      code = "SERVICE_UNAVAILABLE";
      break;
    case 504:
      message = "Timeout del gateway";
      code = "GATEWAY_TIMEOUT";
      break;
    default:
      if (statusCode >= 500) {
        message = "Error del servidor";
        code = "SERVER_ERROR";
      } else if (statusCode >= 400) {
        message = "Error en la solicitud";
        code = "CLIENT_ERROR";
      } else {
        message = error.message || "Error de conexión";
        code = "NETWORK_ERROR";
      }
  }

  return {
    errors: [
      {
        code,
        message,
      },
    ],
    validation: null,
  };
}

/**
 * Verifica si una respuesta es un ErrorFeeback
 */
export function isErrorResponse(response: any): response is ErrorFeeback {
  return (
    response &&
    typeof response === "object" &&
    "errors" in response &&
    Array.isArray(response.errors)
  );
}

/**
 * Extrae el primer mensaje de error de un ErrorFeeback
 */
export function getFirstErrorMessage(errorFeedback: ErrorFeeback): string {
  if (errorFeedback.errors && errorFeedback.errors.length > 0) {
    return errorFeedback.errors[0].message;
  }
  return "Error desconocido";
}

/**
 * Verifica si un error es de autenticación (401)
 */
export function isAuthError(error: AxiosError): boolean {
  return error.response?.status === 401;
}

/**
 * Verifica si un error es de validación (422)
 */
export function isValidationError(error: AxiosError): boolean {
  return error.response?.status === 422;
}

/**
 * Verifica si un error es un Bad Request (400)
 */
export function isBadRequestError(error: AxiosError): boolean {
  return error.response?.status === 400;
}
