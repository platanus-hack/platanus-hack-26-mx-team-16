# Error Handling

Domain raises typed `DomainError` subclasses. Global handlers in `config/main.py`
map them to HTTP. Endpoints and use cases never `try/except` for business errors —
let them bubble.

## Base class

```python
# src/common/domain/exceptions/_base.py
class DomainError(Exception):
    code: str
    message: str
    status_code: int
    context: dict[str, Any] | None = None

    def __init__(self, code: str, message: str, status_code: int = 400, context: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.context = context
        super().__init__(message)
```

Re-exported as `from src.common.domain.exceptions import DomainError` (`__init__.py`).

## Subclasses live in `src/common/domain/exceptions/[area].py`

Centralize subclasses in the shared core, grouped by `[area]` (usually the feature):
`projects.py`, `auth.py`, `users.py`, `tenants.py`, `common.py`, etc. Do **not**
put them in feature modules (`src/[bounded_context]/domain/exceptions.py` should not exist).

```python
# src/common/domain/exceptions/projects.py
from src.common.domain.constants import status
from src.common.domain.exceptions import DomainError


class ProjectNotFoundError(DomainError):
    def __init__(self, context=None):
        super().__init__(
            code="projects.ProjectNotFoundError",
            message="Project Not Found",
            status_code=status.HTTP_404_NOT_FOUND,
            context=context,
        )
```

Conventions:
- Class name: `[Entity]<Condition>Error` (`ProjectNotFoundError`, `ProjectArchivedError`).
- `code = "[area].[Name]"` — `[area]` is the **domain**, which may differ from the
  filename (a `tenants`-area error can live in a file named for the table it guards).
  Stable string the client uses for i18n.
- `status_code` uses `status.HTTP_*` constants from `src.common.domain.constants`, never raw ints.
- ctor signature is `(self, context=None)` — callers pass observability data, not required
  business args. A subclass may enrich `context` itself (e.g. merge `{"project_id": ...}`).
- One subclass per distinct business condition; don't reuse a generic error.

## Error envelope models

```python
# src/common/domain/exceptions/common.py  (what the handlers import)
class ErrorItem(BaseModel):
    code: str
    message: str

class ValidationFeedback(BaseModel):
    code: str
    message: str

class ErrorFeedback(BaseModel):
    errors: list[ErrorItem]
    validation: dict[str, ValidationFeedback] | None = None
```

`timestamp` is **not** a field on `ErrorFeedback`. `ApiJSONResponse.render()`
(`src/common/infrastructure/responses/api_json.py`) detects `"errors" in content`
and injects `content["timestamp"] = datetime.now(UTC).isoformat()` on the way out.

> Always import the envelope from `src.common.domain.exceptions.common`. Keep a single
> source of truth for `ErrorFeedback`/`ErrorItem` so the handlers and the client agree.

## Global handlers

```python
# src/common/infrastructure/error_handlers.py
from src.common.domain.exceptions import DomainError
from src.common.domain.exceptions.common import ErrorFeedback, ErrorItem, ValidationFeedback
from src.common.infrastructure.responses.api_json import ApiJSONResponse


async def domain_error_handler(_: Request, exc: DomainError) -> ApiJSONResponse:
    return ApiJSONResponse(
        status_code=exc.status_code,
        content=ErrorFeedback(
            errors=[ErrorItem(code=exc.code, message=exc.message)],
            validation=None,
        ).model_dump(),
    )


async def validation_error_handler(_: Request, exc: RequestValidationError) -> ApiJSONResponse:
    validation_errors = {}
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"][1:])  # skip 'body' prefix
        if field_path:
            validation_errors[field_path] = ValidationFeedback(
                code=f"common.{error['type']}",
                message=error["msg"],
            )
    return ApiJSONResponse(
        status_code=422,
        content=ErrorFeedback(
            errors=[ErrorItem(code="common.ValidationError", message="Validation errors found")],
            validation=validation_errors if validation_errors else None,
        ).model_dump(),
    )


async def http_exception_handler(_: Request, exc: HTTPException) -> ApiJSONResponse:
    error_code, error_message = "common.HttpError", exc.detail
    if exc.status_code == 401 and exc.detail == "Not authenticated":
        error_code, error_message = "auth.InvalidOrExpiredToken", "Invalid or expired token"
    elif exc.status_code == 403 and exc.detail == "Not authenticated":
        error_code, error_message = "auth.NotAuthenticated", "Not Authenticated"
    return ApiJSONResponse(
        status_code=exc.status_code,
        content=ErrorFeedback(
            errors=[ErrorItem(code=error_code, message=error_message)],
            validation=None,
        ).model_dump(),
    )
```

`context` is **never** returned to the client — handlers serialize only `code` +
`message`. `context` is for logs / observability.

A rate-limit error may use a separate handler that returns a plain `JSONResponse`
with `{error, message, limit, window, retry_after}` + `X-RateLimit-*` / `Retry-After`
headers — it does **not** use the `ErrorFeedback` envelope.

## Registration (`config/main.py`, exact order)

```python
app.add_exception_handler(DomainError, domain_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(RateLimitExceededError, rate_limit_exception_handler)
```

## Response shapes

DomainError / HTTPException:

```json
{
  "errors": [{"code": "projects.ProjectNotFoundError", "message": "Project Not Found"}],
  "validation": null,
  "timestamp": "2026-06-02T15:30:00+00:00"
}
```

Request validation (422):

```json
{
  "errors": [{"code": "common.ValidationError", "message": "Validation errors found"}],
  "validation": {
    "name": {"code": "common.string_type", "message": "Input should be a valid string"},
    "budget": {"code": "common.greater_than", "message": "Input should be greater than 0"}
  },
  "timestamp": "2026-06-02T15:30:00+00:00"
}
```

Client uses `errors[0]` for the toast, `validation[fieldPath]` to flag form fields,
and the `code` strings for i18n.

## Common mistakes

- **Catching `DomainError` in an endpoint/use case** → defeats the global handler. Let it bubble.
- **Raising `HTTPException(400, "...")` from a use case** → use a `DomainError` subclass instead.
- **Putting a subclass in `src/[bounded_context]/domain/`** → all subclasses go in `src/common/domain/exceptions/[area].py`.
- **Raw `status_code=404`** → use `status.HTTP_404_NOT_FOUND` from `src.common.domain.constants`.
- **Importing `ErrorFeedback` from elsewhere** → handlers use the one in `domain/exceptions/common.py`.
- **Leaking `context` to clients** → it's logs/observability only; handlers return `code` + `message`.
- **Mixing statuses in one class** → one class = one status. Different statuses = different classes.

## See also

- `dependency-injection.md` — where errors surface through `DomainContextDep` / `BusContextDep`.
- `endpoints.md` — endpoints stay thin; no error handling there.
- `cqrs-buses.md` — bus dispatch wraps handler exceptions (`infrastructure/buses/_exceptions.py`).
