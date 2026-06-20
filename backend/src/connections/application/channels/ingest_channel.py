"""Ingest a verified inbound :class:`ChannelMessage` (E6 · W5 · diseño §5).

This is the shared pipeline behind ``POST /v1/channels/{provider}/{token}``,
invoked once the channel adapter has verified the provider signature and parsed
the payload. Per message it:

1. **Dedup, delivery-first**: ``source_deliveries.insert_if_absent`` keyed on
   ``UNIQUE(source_id, idempotency_key)``. It returns ``claimed`` — a brand-new
   row OR a reclaimed FAILED row (``claimed=True``) is processed; only a genuine
   duplicate (an in-flight RECEIVED or completed PROCESSED row, ``claimed=False``)
   is a no-op — the endpoint returns a 200 idempotent response with NO side
   effects. A FAILED delivery is retriable: a provider redelivery reclaims it.
2. **Resolve a case** by the source's ``case_strategy``
   (``per_message`` default | ``per_sender`` | ``per_thread``) via the existing
   :class:`ResolveIngestCase` (find-or-create by ``external_ref``).
3. **Upload each attachment bytes-first** (reusing :class:`UploadFileUseCase`
   with the channel audio MIME allowlist) and dispatch :class:`IngestViaSource`
   pre-authenticated, one document-scope run per attachment.
4. **Text without attachments** becomes a ``text/plain`` document so the body
   still flows through the pipeline.

Deferred media (WhatsApp ``media_id``, mailpit message ID) is resolved through
``adapter.fetch_attachment`` before upload; the endpoint runs that in a
background task after ACKing 200 to the provider.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from src.common.application.logging import get_logger
from src.common.database.config import get_database_config
from src.common.domain.enums.source_deliveries import SourceDeliveryStatus
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.common.settings import settings
from src.connections.domain.channels.base import ChannelAdapter
from src.connections.domain.models.channel_message import ChannelAttachment, ChannelMessage
from src.connections.domain.models.source_delivery import SourceDelivery
from src.connections.domain.models.workflow_source import WorkflowSource
from src.connections.domain.repositories.source_delivery import SourceDeliveryRepository
from src.connections.infrastructure.repositories.sql_workflow_source import (
    SQLWorkflowSourceRepository,
)
from src.storage.application.use_cases.upload_file import (
    UploadFileUseCase,
    bytes_to_upload_file,
)
from src.storage.infrastructure.repositories.s3_file_repository import S3FileRepository
from src.workflows.application.sources.ingest import IngestViaSource, ResolveIngestCase
from src.workflows.infrastructure.repositories.sql_document_type import (
    SQLDocumentTypeRepository,
)
from src.workflows.infrastructure.repositories.sql_pipeline import SQLPipelineRepository
from src.workflows.infrastructure.repositories.sql_workflow import SQLWorkflowRepository
from src.workflows.infrastructure.repositories.sql_workflow_case import (
    SQLWorkflowCaseRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow_processing_job import (
    SQLWorkflowProcessingJobRepository,
)
from src.workflows.infrastructure.services.webhooks.case_event_dispatcher import (
    CaseEventDispatcher,
)

logger = get_logger(__name__)

# Text bodies without attachments are ingested as a small text document.
_TEXT_MIME = "text/plain"


def case_name_for(message: ChannelMessage, strategy: str) -> str:
    """Map a channel message + case_strategy to a case external_ref (diseño §5)."""
    if strategy == "per_sender":
        return message.sender or message.provider_message_id
    if strategy == "per_thread":
        return message.thread_ref or message.provider_message_id
    # per_message (default): each message is its own case.
    return message.provider_message_id


@dataclass
class IngestChannelMessageResult:
    delivery_id: UUID
    duplicate: bool
    case_id: UUID | None = None
    job_ids: list[str] = field(default_factory=list)


@dataclass
class IngestChannelMessage(UseCase):
    """Dedup → case → upload+dispatch for one verified channel message."""

    source: WorkflowSource
    message: ChannelMessage
    adapter: ChannelAdapter
    session: object  # AsyncSession
    temporal_client: object
    source_delivery_repository: SourceDeliveryRepository

    async def execute(self) -> IngestChannelMessageResult:
        delivery = SourceDelivery(
            uuid=uuid4(),
            source_id=self.source.uuid,
            idempotency_key=self.message.provider_message_id,
            provider_message_id=self.message.provider_message_id,
            status=SourceDeliveryStatus.RECEIVED,
        )
        stored, claimed = await self.source_delivery_repository.insert_if_absent(delivery)
        if not claimed:
            # Genuine duplicate (in-flight RECEIVED or completed PROCESSED) —
            # 200 idempotent, no side effects (diseño §5). A FAILED row is NOT a
            # duplicate: insert_if_absent reclaims it to RECEIVED and reports
            # claimed=True so the redelivery is reprocessed instead of lost.
            logger.info(
                "channel.delivery_duplicate",
                source_id=str(self.source.uuid),
                idempotency_key=self.message.provider_message_id,
            )
            return IngestChannelMessageResult(
                delivery_id=stored.uuid, duplicate=True, case_id=stored.case_id
            )

        try:
            return await self._process(stored.uuid)
        except Exception as exc:  # noqa: BLE001 — record FAILED, let endpoint surface
            await self.source_delivery_repository.mark_status(
                stored.uuid, SourceDeliveryStatus.FAILED, error=str(exc)[:500]
            )
            raise

    async def _process(self, delivery_id: UUID) -> IngestChannelMessageResult:
        strategy = str(self.source.config.get("case_strategy", "per_message"))
        case_result = await ResolveIngestCase(
            tenant_id=self.source.tenant_id,
            workflow_id=self.source.workflow_id,
            case_name=case_name_for(self.message, strategy),
            workflow_repository=SQLWorkflowRepository(self.session),
            case_repository=SQLWorkflowCaseRepository(self.session),
            pipeline_repository=SQLPipelineRepository(self.session),
            temporal_client=self.temporal_client,
            task_queue=settings.TEMPORAL_TASK_QUEUE,
            case_event_dispatcher=CaseEventDispatcher(
                session_maker=get_database_config().session_maker
            ),
        ).execute()
        case = case_result.case
        case_id = case.uuid if case is not None else None

        # Resolve deferred-media attachments to bytes, then any inline ones.
        resolved = await self._resolve_attachments()

        job_ids: list[str] = []
        for index, (filename, content_type, content) in enumerate(resolved):
            job_id = await self._ingest_one(filename, content_type, content, case_id, index)
            if job_id is not None:
                job_ids.append(job_id)

        await self.source_delivery_repository.mark_status(
            delivery_id, SourceDeliveryStatus.PROCESSED, case_id=case_id
        )
        await self.session.commit()
        return IngestChannelMessageResult(
            delivery_id=delivery_id, duplicate=False, case_id=case_id, job_ids=job_ids
        )

    async def _resolve_attachments(self) -> list[tuple[str, str, bytes]]:
        """Return ``(filename, content_type, bytes)`` for every uploadable item."""
        resolved: list[tuple[str, str, bytes]] = []
        for att in self.message.attachments:
            content, content_type = await self._attachment_bytes(att)
            if content:
                resolved.append((att.filename, content_type, content))

        # Body text with no attachments → a text/plain document.
        if not resolved and self.message.text:
            resolved.append(
                (f"message-{self.message.provider_message_id[-12:]}.txt", _TEXT_MIME,
                 self.message.text.encode("utf-8"))
            )
        return resolved

    async def _attachment_bytes(self, att: ChannelAttachment) -> tuple[bytes, str]:
        if att.content is not None:
            return att.content, att.content_type
        if att.fetch_ref:
            content, content_type = await self.adapter.fetch_attachment(
                self.source, att.fetch_ref
            )
            return content, (content_type or att.content_type)
        return b"", att.content_type

    async def _ingest_one(
        self,
        filename: str,
        content_type: str,
        content: bytes,
        case_id: UUID | None,
        index: int,
    ) -> str | None:
        upload = bytes_to_upload_file(content, filename, content_type)
        extra_mimes = [*settings.CHANNEL_AUDIO_MIMES, _TEXT_MIME]
        uploaded = await UploadFileUseCase(
            tenant_id=self.source.tenant_id,
            file=upload,
            file_repository=S3FileRepository(self.session),
            extra_allowed_mimes=extra_mimes,
        ).execute()

        # Stable per (message, attachment) job id → dedup of processing_job rows.
        # Use a deterministic digest (NOT builtin hash — PYTHONHASHSEED varies).
        digest = hashlib.sha256(self.message.provider_message_id.encode()).hexdigest()[:12]
        job_id = f"SRC#{self.source.route_token}_MSG#{digest}_A{index}"
        ds_repo = SQLWorkflowProcessingJobRepository(self.session)
        processing_job = await ds_repo.find_by_temporal_workflow_id(job_id)
        if processing_job is None:
            processing_job = await ds_repo.create(
                WorkflowProcessingJob(
                    uuid=uuid4(),
                    temporal_workflow_id=job_id,
                    tenant_id=self.source.tenant_id,
                    workflow_id=self.source.workflow_id,
                    workflow_case_id=case_id,
                    file_id=uploaded.uuid,
                )
            )

        return await IngestViaSource(
            route_token=self.source.route_token,
            object_key=uploaded.s3_key,
            file_name=uploaded.file_name,
            source_repository=SQLWorkflowSourceRepository(self.session),
            pipeline_repository=SQLPipelineRepository(self.session),
            document_type_repository=SQLDocumentTypeRepository(self.session),
            temporal_client=self.temporal_client,
            task_queue=settings.TEMPORAL_TASK_QUEUE,
            file_id=uploaded.uuid,
            processing_job_uuid=processing_job.uuid,
            case_id=case_id,
            pre_authenticated=True,
            job_id_override=job_id,
            extra_allowed_mimes=extra_mimes,
        ).execute()
