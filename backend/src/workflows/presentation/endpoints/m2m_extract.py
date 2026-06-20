"""``POST /v1/extract`` — plano 1 de la API pública: extracción stateless (E1 · D1).

Async-first: despacha la receta del workflow por el intérprete y responde
``202 + job_id``. Con ``mode=sync`` y un archivo de ≤``SYNC_MAX_PAGES`` páginas
espera el resultado inline (timeout ~30 s); timeout o exceso de páginas
**degrada a 202, nunca error**. El resultado siempre queda recuperable vía
``GET /v1/jobs/{job_id}`` (el job persiste — por eso el job_id es reusable).

Decisión (Vic, 2026-06-09): ``workflow`` es OBLIGATORIO — sin él 422. La
extracción ancla sus filas al workflow indicado y usa sus document types;
se puede relajar después sin breaking change. ANALYSIS workflows requieren
caso (plano 2, E3) y aquí se rechazan con 422.

Entradas aceptadas:
- ``multipart/form-data`` con campo ``file`` (igual que el upload de la app).
- ``application/json`` con ``{"url": ...}`` (descarga server-side con guard
  SSRF) o ``{"base64": ..., "filename": ..., "content_type": ...}``.

``workflow`` (UUID), ``pipeline`` (slug, opcional) y ``mode`` (``async`` |
``sync``) viajan como query params o campos del form/body.
"""

from __future__ import annotations

import asyncio
import base64 as b64
import binascii
from io import BytesIO
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Request, status
from starlette.datastructures import Headers, UploadFile
from temporalio.client import WorkflowFailureError

from src.common.application.helpers.webhooks.url_validation import (
    InvalidWebhookUrlError,
    validate_webhook_url,
)
from src.common.application.logging import get_logger
from src.common.domain.enums.workflows import WorkflowProcessingJobTrigger
from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import (
    AsyncSessionDep,
    DomainContextDep,
    TemporalClientDep,
)
from src.common.infrastructure.dependencies.tenant_api_key import get_tenant_from_api_key
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.common.settings import settings
from src.storage.application.use_cases.upload_file import UploadFileUseCase
from src.workflows.application.processing_jobs.dispatcher import WorkflowProcessingJobDispatcher
from src.workflows.application.processing_jobs.page_count import count_pages
from src.workflows.presentation.presenters.m2m_job import present_job

logger = get_logger(__name__)

SYNC_MAX_PAGES = 5
SYNC_TIMEOUT_SECONDS = 30.0
URL_FETCH_TIMEOUT_SECONDS = 20.0

PDF_MAGIC = b"%PDF"


def _error(status_code: int, error: str, detail: str) -> ApiJSONResponse:
    return ApiJSONResponse(content={"error": error, "detail": detail}, status_code=status_code)


def _sniff_mime(content: bytes, declared: str | None, filename: str | None) -> str:
    if declared:
        return declared
    if content[:4] == PDF_MAGIC:
        return "application/pdf"
    if content[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if filename and filename.lower().endswith(".pdf"):
        return "application/pdf"
    return "application/octet-stream"


def _as_upload(content: bytes, filename: str, mime: str) -> UploadFile:
    return UploadFile(
        BytesIO(content),
        size=len(content),
        filename=filename,
        headers=Headers({"content-type": mime}),
    )


async def _fetch_url(url: str) -> tuple[bytes, str | None, str]:
    """Descarga server-side con guard SSRF. Devuelve (bytes, mime, filename)."""
    validate_webhook_url(url)
    async with httpx.AsyncClient(
        timeout=URL_FETCH_TIMEOUT_SECONDS,
        follow_redirects=False,
        max_redirects=0,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        content = response.content
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise ValueError("downloaded file exceeds MAX_UPLOAD_SIZE")
        mime = (response.headers.get("content-type") or "").split(";")[0].strip() or None
        filename = url.rstrip("/").rsplit("/", 1)[-1] or "downloaded"
        return content, mime, filename


async def _parse_input(request: Request) -> tuple[UploadFile | None, dict, ApiJSONResponse | None]:
    """Normaliza multipart vs JSON. Devuelve (upload, params, error_response)."""
    content_type = (request.headers.get("content-type") or "").lower()
    params: dict = dict(request.query_params)

    if content_type.startswith("multipart/"):
        form = await request.form()
        for key in ("workflow", "pipeline", "mode"):
            if key in form and key not in params:
                params[key] = str(form[key])
        upload = form.get("file")
        if upload is None or isinstance(upload, str):
            return None, params, _error(422, "file_required", "multipart requests must include a 'file' part")
        return upload, params, None

    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return None, params, _error(
            422, "invalid_body", "send multipart/form-data with 'file', or JSON with 'url' or 'base64'"
        )
    if not isinstance(body, dict):
        return None, params, _error(422, "invalid_body", "JSON body must be an object")
    for key in ("workflow", "pipeline", "mode"):
        if key in body and key not in params:
            params[key] = str(body[key])

    if body.get("url"):
        try:
            content, mime, filename = await _fetch_url(str(body["url"]))
        except InvalidWebhookUrlError as exc:
            return None, params, _error(422, "invalid_url", str(exc))
        except Exception as exc:  # noqa: BLE001 — red/HTTP/size: el integrador debe saber por qué
            return None, params, _error(422, "url_fetch_failed", str(exc))
        filename = str(body.get("filename") or filename)
        mime = _sniff_mime(content, str(body.get("content_type")) if body.get("content_type") else mime, filename)
        return _as_upload(content, filename, mime), params, None

    if body.get("base64"):
        try:
            content = b64.b64decode(str(body["base64"]), validate=True)
        except (binascii.Error, ValueError):
            return None, params, _error(422, "invalid_base64", "the 'base64' field is not valid base64")
        filename = str(body.get("filename") or "upload")
        mime = _sniff_mime(content, str(body.get("content_type")) if body.get("content_type") else None, filename)
        return _as_upload(content, filename, mime), params, None

    return None, params, _error(422, "input_required", "provide 'file' (multipart), 'url' or 'base64'")


async def extract(
    request: Request,
    session: AsyncSessionDep,
    temporal_client: TemporalClientDep,
    domain: DomainContextDep,
    tenant: Tenant = Depends(get_tenant_from_api_key),
) -> ApiJSONResponse:
    upload, params, error = await _parse_input(request)
    if error is not None:
        return error

    raw_workflow = params.get("workflow")
    if not raw_workflow:
        return _error(
            422,
            "workflow_required",
            "pass ?workflow=<uuid> (or 'workflow' in the form/body): extraction anchors to a workflow's document types",
        )
    try:
        workflow_id = UUID(str(raw_workflow))
    except ValueError:
        return _error(422, "invalid_workflow", f"'{raw_workflow}' is not a valid workflow UUID")

    mode = str(params.get("mode") or "async").lower()
    if mode not in ("async", "sync"):
        return _error(422, "invalid_mode", "mode must be 'async' or 'sync'")
    pipeline_slug = params.get("pipeline") or None

    # Subida idéntica al plano app: valida mime/tamaño, S3 + fila file (cada
    # POST crea un file nuevo ⇒ job nuevo; no hay colisión de idempotencia).
    content = await upload.read()
    await upload.seek(0)
    uploaded = await UploadFileUseCase(
        tenant_id=tenant.uuid,
        file=upload,
        file_repository=domain.file_repository,
    ).execute()

    page_count = count_pages(content, upload.content_type or "")

    processing_job = await WorkflowProcessingJobDispatcher(
        tenant_id=tenant.uuid,
        workflow_id=workflow_id,
        file_id=uploaded.uuid,
        workflow_case_id=None,
        session=session,
        temporal_client=temporal_client,
        processing_job_repository=domain.processing_job_repository,
        workflow_repository=domain.workflow_repository,
        workflow_case_repository=domain.workflow_case_repository,
        document_type_repository=domain.document_type_repository,
        file_repository=domain.file_repository,
        pipeline_repository=domain.pipeline_repository,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        trigger=WorkflowProcessingJobTrigger.SYSTEM,
        pipeline_slug=pipeline_slug,
    ).execute()

    job_id = processing_job.temporal_workflow_id

    if mode == "sync" and page_count is not None and page_count <= SYNC_MAX_PAGES:
        try:
            handle = temporal_client.get_workflow_handle(job_id)
            await asyncio.wait_for(handle.result(), timeout=SYNC_TIMEOUT_SECONDS)
        except (TimeoutError, asyncio.TimeoutError):
            logger.info("m2m.extract.sync_timeout", job_id=job_id)
        except WorkflowFailureError:
            # El run terminó en fallo: el estado/los documentos fallidos se
            # presentan igual — el integrador ve status=FAILED, no un 5xx.
            logger.info("m2m.extract.sync_run_failed", job_id=job_id)
        else:
            return await _present_terminal(session, domain, tenant, job_id)
        # Falló o expiró el modo sync ⇒ degradar a 202 (D1: nunca error).
        refreshed = await domain.processing_job_repository.find_by_temporal_workflow_id(job_id)
        if refreshed is not None and refreshed.status.is_terminal:
            return await _present_terminal(session, domain, tenant, job_id)

    return ApiJSONResponse(
        content={
            "job_id": job_id,
            "status": processing_job.status.value,
            "status_url": f"/v1/jobs/{job_id}",
            "page_count": page_count,
        },
        status_code=status.HTTP_202_ACCEPTED,
    )


async def _present_terminal(session, domain, tenant: Tenant, job_id: str) -> ApiJSONResponse:
    processing_job = await domain.processing_job_repository.find_by_temporal_workflow_id(job_id)
    if processing_job is None or processing_job.tenant_id != tenant.uuid:
        return _error(404, "job_not_found", job_id)
    documents = await domain.document_repository.list_by_processing_job(processing_job.uuid)
    return ApiJSONResponse(
        content=present_job(processing_job, documents),
        status_code=status.HTTP_200_OK,
    )


m2m_extract_router = APIRouter(prefix="", tags=["M2M"])

m2m_extract_router.add_api_route(
    "/extract",
    extract,
    methods=["POST"],
    summary="Stateless extraction — async-first con mode=sync ≤5 páginas (E1 · D1)",
)
