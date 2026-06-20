import secrets
from typing import Annotated, Any

from pydantic import (
    AnyUrl,
    BeforeValidator,
    HttpUrl,
    computed_field,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.common.domain.enums.common import Environment, ProcessLabel, Stage


def parse_items(v: Any) -> list[str]:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    if isinstance(v, list):
        return v
    return []


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "VNext"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Payments Platform"

    # Environment
    STAGE: Stage = Stage.dev
    ENVIRONMENT: Environment = Environment.development
    PROCESS_LABEL: ProcessLabel = ProcessLabel.api
    DEBUG: bool = False

    # CORS Configuration
    CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_items)] = []

    # Security Configuration
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1  # TODO apply 15 minutes
    # JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 2  # 7 days
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "vnext"

    # Common
    SECRET_KEY: str = secrets.token_urlsafe(32)

    # Database Configuration
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str | None = None

    # Redis Configuration
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_USER: str | None = None
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0

    PAGINATION_PAGE_SIZE: int = 25

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None
    GOOGLE_AUTH_URL: str = "https://accounts.google.com/o/oauth2/auth"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL: str = "https://www.googleapis.com/oauth2/v3/userinfo"
    GOOGLE_CERTS_URL: str = "https://www.googleapis.com/oauth2/v3/certs"

    # Email Configuration
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    DEFAULT_FROM_EMAIL: str | None = None

    # -> AWS S3 CONFIGURATION
    AWS_S3_ENDPOINT_URL: str | None = None
    AWS_S3_PUBLIC_URL: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_SESSION_TOKEN: str | None = None
    AWS_S3_REGION_NAME: str = "us-east-1"
    AWS_STORAGE_BUCKET_NAME: str | None = None
    AWS_CLOUDFRONT_DOMAIN: str | None = None

    # -> EXTRACTION / OCR / LLM
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    OCR_MAX_PAGE_THREADS: int = 20
    EXTRACTION_MAX_DOC_WORKERS: int = 8
    EXTRACTION_LAMBDA_ENABLED: bool = True
    EXTRACTION_LAMBDA_EXTRACTOR: str = "textract_layout"
    VNEXT_LAMBDA_PREFIX: str = "vnext-tools"

    # -> ANALYSIS PIPELINE: override del provider por agente.
    # Valores válidos: "anthropic" | "openai" | "gemini" | "openrouter".
    # Si está vacío, cada agente usa su ``default_provider`` propio.
    ANALYSIS_PARSER_PROVIDER: str | None = None
    ANALYSIS_REVIEWER_PROVIDER: str | None = None
    ANALYSIS_CRITIC_PROVIDER: str | None = None
    ANALYSIS_SYNTHESIZER_PROVIDER: str | None = None
    # E3 · fase assess (capa-2 de confianza). Declarado aquí explícitamente:
    # si faltara, `_resolve_role_model_id` caería en silencio al fallback
    # `openai:gpt-4o-mini` (el gotcha de DOCTYPE_SCHEMA_BUILDER_PROVIDER).
    ANALYSIS_ASSESS_PROVIDER: str | None = None

    # E3 · tools HTTP de la fase enrich. SOLO dev/test: permite http/localhost
    # en validate_tool_url para apuntar a servicios locales. JAMÁS en prod.
    TOOLS_ALLOW_INSECURE_HTTP: bool = False

    # phases-config · F5 (D-D): selector del runner de script tools (PYTHON/JS).
    # "" (default) ⇒ fail-closed (las script tools degradan; NUNCA ejecutan).
    # "local_subprocess" ⇒ runner local con rlimits/timeout — SOLO dev: NO aísla
    # red ni kernel; el sandbox de prod (gVisor/Firecracker) requiere ADR 0006 +
    # revisión de seguridad.
    TOOLS_SCRIPT_RUNNER: str = ""

    # -> ADMIN CONFIGURATION
    ADMIN_LOGO_URL: str = "https://preview.tabler.io/static/logo-white.svg"
    ADMIN_LOGIN_LOGO_URL: str = "https://preview.tabler.io/static/logo.svg"

    # -> FRONTEND CONFIGURATION
    FRONTEND_HOST: str = "http://localhost:3000"

    # -> MONITORING
    SENTRY_DSN: HttpUrl | None = None
    SENTRY_ENVIRONMENT: Stage = Stage.dev
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.1
    SENTRY_SEND_DEFAULT_PII: bool = True  # GDPR compliance

    # -> TEMPORAL
    TEMPORAL_HOST: str = "temporal:7233"
    TEMPORAL_TASK_QUEUE: str = "document-processing"

    # -> UPLOAD & EXTRACTION LIMITS
    # Max bytes accepted by /documents/upload (default 100 MB).
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024
    # Wall-clock budget for the bulk extraction Temporal workflow (seconds).
    EXTRACTION_TIMEOUT: int = 600
    # Comma-separated MIME allowlist for uploads (pydantic splits on comma when
    # reading from env: `ALLOWED_UPLOAD_MIMES=application/pdf,image/jpeg`).
    ALLOWED_UPLOAD_MIMES: list[str] = [
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
    ]
    # E6 · W5: audio MIMEs accepted ONLY by the native channel path (voice notes
    # → asr extractor). The web uploader keeps using ALLOWED_UPLOAD_MIMES — these
    # are merged in by UploadFileUseCase only when the caller opts in.
    CHANNEL_AUDIO_MIMES: list[str] = [
        "audio/ogg",
        "audio/mpeg",
        "audio/mp4",
        "audio/amr",
        "audio/wav",
    ]
    # E6 · W5: native channel infrastructure.
    # Domain for auto-generated inbound email aliases (in+{token}@{domain}).
    CHANNELS_EMAIL_DOMAIN: str | None = None
    # Dev only: mailpit HTTP API base for reading inbound MIME/attachments.
    MAILPIT_API_URL: str | None = None
    # Meta Graph API version for WhatsApp media downloads.
    META_GRAPH_API_VERSION: str = "v20.0"

    # Admin & Integrations
    ADMIN_API_KEY: str = secrets.token_urlsafe(32)

    # -> SCANNING / ATTACK LEVELS (owned by 02-attack-levels)
    # Feature-flag gate for hexstrike-ai. Default OFF: hexstrike is cut to zero
    # from the start of the plan. When True, the advanced level *may* receive the
    # hexstrike tool, but ONLY if the worker healthcheck also passes (the boolean
    # `hexstrike_ok` fed to resolve_toolset). The healthcheck mechanics live in
    # 04-scanning-engine §10; 02 only consumes the resulting boolean.
    ENABLE_HEXSTRIKE: bool = False
    # Real production budget for the advanced level (ZAP full active + Nuclei
    # fuzzing + sqlmap), enforced by 04's watchdog. ~8 min.
    SCAN_GLOBAL_BUDGET_SECONDS: int = 480
    # Hard timeout for the curated demo profile (Nuclei subset + testssl + 1 probe
    # against the own bot). MUST stay <= 90s and is intentionally distinct from
    # SCAN_GLOBAL_BUDGET_SECONDS — the two numbers are never interchangeable.
    DEMO_PROFILE_TIMEOUT_SECONDS: int = 90
    # Identifiable scanner User-Agent used to evaluate/honor robots.txt and to run
    # web requests. Rate-limit + UA policy detail lives in 01-legal-ethics.
    SCANNER_USER_AGENT: str = "Owliver-Scanner/1.0 (+contacto)"

    @computed_field
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.CORS_ORIGINS]

    @computed_field
    @property
    def database_url(self) -> MultiHostUrl:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @computed_field
    @property
    def async_database_url(self) -> MultiHostUrl:
        return MultiHostUrl.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @computed_field
    @property
    def redis_url(self) -> str:
        if self.ENVIRONMENT.is_production:
            return (
                f"redis://{self.REDIS_USER}:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def sentry_enabled(self) -> bool:
        return bool(self.SENTRY_DSN and not self.ENVIRONMENT.is_local)


settings = Settings()
