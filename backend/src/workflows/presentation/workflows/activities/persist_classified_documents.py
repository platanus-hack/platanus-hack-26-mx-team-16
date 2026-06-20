"""Activity that creates `WorkflowDocument` rows after classify_pages.

Persisting the rows BEFORE `JOB_CLASSIFIED` is emitted is the contract
that lets the SSE stream carry real DB UUIDs from the very first event
the frontend ever receives. Idempotent: if the document set already has
documents the activity returns the existing rows without inserting
duplicates.

When the insert wins the race we also fan out a single
`DashboardEvent("DOCUMENT_CREATED")` so the dashboard refetches its
counters without waiting for the first `mark_document_status`
transition. Idempotent-hit and race-lost paths skip the publish — the
winning attempt already emitted it.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio import activity

from src.common.application.logging import get_logger
from src.common.database.models.workflow_document import WorkflowDocumentORM
from src.common.domain.enums.processing_job_events import DocumentStatus
from src.common.domain.enums.workflows import (
    WorkflowDocumentSource,
    WorkflowDocumentStatus,
)
from src.common.infrastructure.event_publisher import EventPublisher
from src.dashboard.domain.events import DashboardEvent
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    PersistClassifiedDocumentsInput,
    PersistClassifiedDocumentsOutput,
    PersistedDocumentRef,
)

logger = get_logger(__name__)


class PersistClassifiedDocumentsActivity:
    def __init__(
        self,
        session_maker: async_sessionmaker,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._session_maker = session_maker
        self._event_publisher = event_publisher

    @activity.defn(name="persist_classified_documents")
    async def persist_classified_documents(
        self, payload: PersistClassifiedDocumentsInput
    ) -> PersistClassifiedDocumentsOutput:
        data = PersistClassifiedDocumentsInput.model_validate(payload)
        logger.info(
            "persist_classified_documents.start "
            f"processing_job_uuid={data.processing_job_uuid} tenant_id={data.tenant_id} "
            f"workflow_id={data.workflow_id} case_id={data.case_id} file_id={data.file_id} "
            f"incoming_docs={len(data.documents)}"
        )
        if not data.documents:
            logger.warning(
                "persist_classified_documents.empty_input "
                f"processing_job_uuid={data.processing_job_uuid} — no rows will be inserted "
                f"because the pipeline did not pass any ClassifiedDocumentRef"
            )

        async with self._session_maker() as session:
            existing = await self._fetch_existing(session, data.processing_job_uuid)
            if existing:
                logger.info(
                    "persist_classified_documents.idempotent_hit "
                    f"processing_job_uuid={data.processing_job_uuid} count={len(existing)}"
                )
                return _to_output(existing)

            staged: list[tuple[WorkflowDocumentORM, PersistedDocumentRef]] = []
            for ref in data.documents:
                new_uuid = uuid4()
                fallback_name = ref.document_type_name or f"document #{ref.document_index + 1}"
                # D6': versión del contrato sellada al despachar el run; NULL
                # para docs sin tipo ("Otros") o runs previos al versionado.
                sealed_version = (
                    data.document_type_versions.get(str(ref.document_type_id))
                    if ref.document_type_id is not None
                    else None
                )
                row = WorkflowDocumentORM(
                    uuid=new_uuid,
                    tenant_id=data.tenant_id,
                    workflow_id=data.workflow_id,
                    workflow_case_id=data.case_id,
                    document_id=data.file_id,
                    document_type_id=ref.document_type_id,
                    document_type_version=sealed_version,
                    name=fallback_name,
                    status=WorkflowDocumentStatus.PROCESSING.value,
                    source=WorkflowDocumentSource.BULK.value,
                    processing_job_id=data.processing_job_uuid,
                    document_index=ref.document_index,
                    page_range=ref.page_range,
                    processing_status=DocumentStatus.EXTRACTING.value,
                )
                session.add(row)
                staged.append(
                    (
                        row,
                        PersistedDocumentRef(
                            document_id=new_uuid,
                            document_type_id=ref.document_type_id,
                            document_type_name=ref.document_type_name,
                            document_index=ref.document_index,
                            page_range=ref.page_range,
                        ),
                    )
                )

            try:
                await session.commit()
            except IntegrityError as exc:
                # Race: another activity attempt won and inserted these
                # rows between our SELECT and our INSERT. The partial
                # UNIQUE index on (processing_job_id, document_index)
                # caught it. Roll back, re-read, and surface the winner's
                # rows so downstream activities see consistent UUIDs.
                await session.rollback()
                logger.warning(
                    f"persist_classified_documents.race_lost "
                    f"processing_job_uuid={data.processing_job_uuid} error={exc}"
                )
                existing = await self._fetch_existing(session, data.processing_job_uuid)
                return _to_output(existing)
            except Exception as exc:
                await session.rollback()
                logger.error(
                    f"persist_classified_documents.commit_failed "
                    f"processing_job_uuid={data.processing_job_uuid} "
                    f"error_type={type(exc).__name__} error={exc}"
                )
                raise

            logger.info(
                "persist_classified_documents.inserted "
                f"processing_job_uuid={data.processing_job_uuid} inserted_count={len(staged)} "
                f"document_ids={[str(ref.document_id) for _, ref in staged]}"
            )

            # Fan out a single dashboard signal for the whole batch. We
            # don't emit one per doc because the frontend's invalidation
            # is the same regardless of count, and Redis pub/sub fan-out
            # cost is real — one event keeps the system quiet.
            await self._publish_dashboard_event(
                tenant_id=data.tenant_id,
                document_ids=[ref.document_id for _, ref in staged],
            )

            return PersistClassifiedDocumentsOutput(documents=[ref for _, ref in staged])

    @staticmethod
    async def _fetch_existing(session: AsyncSession, processing_job_uuid) -> list[WorkflowDocumentORM]:
        return list(
            (
                await session.execute(
                    select(WorkflowDocumentORM)
                    .where(WorkflowDocumentORM.processing_job_id == processing_job_uuid)
                    .order_by(WorkflowDocumentORM.document_index.asc())
                )
            )
            .scalars()
            .all()
        )

    async def _publish_dashboard_event(
        self, *, tenant_id: UUID, document_ids: list[UUID]
    ) -> None:
        if self._event_publisher is None or not document_ids:
            return
        try:
            event = DashboardEvent.build(
                type="DOCUMENT_CREATED",
                tenant_id=tenant_id,
                affects=["overview", "processing"],
                payload={
                    "documentIds": [str(d) for d in document_ids],
                    "count": len(document_ids),
                    "source": "BULK",
                },
            )
            await self._event_publisher.publish(event)
        except Exception as exc:
            # Belt-and-braces: the publisher logs its own errors, but we
            # NEVER let a Redis blip crash the Temporal activity that
            # just successfully persisted the rows.
            logger.warning(
                f"persist_classified_documents.dashboard_publish_failed "
                f"processing_job_uuid=<unknown> error={exc}"
            )


def _to_output(rows: list[WorkflowDocumentORM]) -> PersistClassifiedDocumentsOutput:
    return PersistClassifiedDocumentsOutput(
        documents=[
            PersistedDocumentRef(
                document_id=row.uuid,
                document_type_id=row.document_type_id,
                document_type_name=row.name,
                document_index=row.document_index or 0,
                page_range=row.page_range,
            )
            for row in rows
        ]
    )
