from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError

from src.common.domain.exceptions import DomainError
from src.common.domain.exceptions.common import ErrorFeedback, ErrorItem, ValidationFeedback
from src.common.infrastructure.responses.api_json import ApiJSONResponse


async def domain_error_handler(_: Request, exc: DomainError) -> ApiJSONResponse:
    error_feedback = ErrorFeedback(
        errors=[
            ErrorItem(
                code=exc.code,
                message=exc.message,
            )
        ],
        validation=None,
    )

    content = error_feedback.model_dump()
    # Claves de contexto expuestas en el error item (whitelist):
    # - E4 · 409 ``case.not_complete`` ⇒ ``errors[0].missing`` (dialog force).
    # - E5 · 409 ``human_task.open_flags`` ⇒ ``errors[0].openFields`` (lista de
    #   campos flageados sin verificar, para el force-dialog del FE).
    # - E5 · 409 ``human_task.already_claimed`` / 423 ``case.locked`` ⇒
    #   ``errors[0].holder`` (lock visible: la UI muestra quién la tiene).
    for exposed_key in ("missing", "openFields", "holder"):
        if exc.context and exposed_key in exc.context and exc.context[exposed_key] is not None:
            content["errors"][0][exposed_key] = exc.context[exposed_key]

    return ApiJSONResponse(
        status_code=exc.status_code,
        content=content,
    )


async def validation_error_handler(
    _: Request,
    exc: RequestValidationError,
) -> ApiJSONResponse:
    validation_errors = {}

    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"][1:])  # Skip 'body' prefix
        if field_path:
            validation_errors[field_path] = ValidationFeedback(
                code=f"common.{error['type']}",
                message=error["msg"],
            )

    error_feedback = ErrorFeedback(
        errors=[
            ErrorItem(
                code="common.ValidationError",
                message="Existen errores de Validación",
            )
        ],
        validation=validation_errors if validation_errors else None,
    )

    return ApiJSONResponse(
        status_code=422,
        content=error_feedback.model_dump(),
    )


async def http_exception_handler(_: Request, exc: HTTPException) -> ApiJSONResponse:
    error_code = "common.HttpError"
    error_message = exc.detail

    # Map specific HTTP exceptions to domain errors
    http_unauthorized = 401
    http_forbidden = 403

    if exc.status_code == http_unauthorized and exc.detail == "Not authenticated":
        error_code = "auth.InvalidOrExpiredToken"
        error_message = "Invalid or expired token"
    elif exc.status_code == http_forbidden and exc.detail == "Not authenticated":
        error_code = "auth.NotAuthenticated"
        error_message = "Not Authenticated"

    error_feedback = ErrorFeedback(
        errors=[
            ErrorItem(
                code=error_code,
                message=error_message,
            )
        ],
        validation=None,
    )

    return ApiJSONResponse(
        status_code=exc.status_code,
        content=error_feedback.model_dump(),
    )
