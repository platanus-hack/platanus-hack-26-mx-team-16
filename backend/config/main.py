#  F A S T A P I
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from config.lifespan import lifespan
from config.monitoring import init_sentry
from config.router import api_router
from src.common.domain.exceptions import DomainError
from src.common.infrastructure.error_handlers import (
    domain_error_handler,
    http_exception_handler,
    validation_error_handler,
)
from src.common.infrastructure.handlers.rate_limit_handler import (
    rate_limit_exception_handler,
)
from src.common.infrastructure.middlewares.camel_case import CamelCaseToSnakeCaseMiddleware
from src.common.infrastructure.middlewares.rate_limit_headers import (
    RateLimitHeadersMiddleware,
)
from src.common.infrastructure.middlewares.request_tracking import RequestTrackingMiddleware
from src.common.infrastructure.middlewares.security_headers import SecurityHeadersMiddleware
from src.common.infrastructure.responses.camel_case import CamelCaseJSONResponse
from src.common.infrastructure.services.rate_limiter import RateLimitExceededError
from src.common.settings import settings

init_sentry()
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    docs_url="/api/py/docs",
    openapi_url="/api/py/openapi.json",
    lifespan=lifespan,
    default_response_class=CamelCaseJSONResponse,
    redirect_slashes=True,
)
app.include_router(api_router)

# Static evidence mount (04-scanning-engine §8): serves /data/scans/{id}/{n}.png
# under /static/scans. Finding.evidence stores the relative URL; 09's PDF export
# embeds from this same path. Failing softly keeps the API up if the volume is
# absent in a non-scanning deployment.
try:
    from src.scanning.evidence import mount_static_scans

    mount_static_scans(app)
except Exception:  # noqa: BLE001 - evidence mount is optional for non-scan deploys
    pass

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CamelCaseToSnakeCaseMiddleware)
app.add_middleware(RequestTrackingMiddleware)
app.add_middleware(RateLimitHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.all_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

app.add_exception_handler(DomainError, domain_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(RateLimitExceededError, rate_limit_exception_handler)
