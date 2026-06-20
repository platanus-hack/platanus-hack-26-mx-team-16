from uuid import uuid4

import pytest
from expects import equal, expect, have_length
from sqlalchemy import select

from src.common.database.config import get_database_config
from src.common.database.models.document_type import DocumentTypeORM
from src.common.database.models.workflow_processing_job import WorkflowProcessingJobORM
from src.common.database.models.workflow_document import WorkflowDocumentORM
from src.common.domain.enums.processing_job_events import DocumentStatus
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    ClassifiedDocumentRef,
    PersistClassifiedDocumentsInput,
)
from src.workflows.presentation.workflows.activities.persist_classified_documents import (
    PersistClassifiedDocumentsActivity,
)


@pytest.fixture
def activity():
    return PersistClassifiedDocumentsActivity(session_maker=get_database_config().session_maker)


async def _seed_processing_job(async_session, tenant_orm, workflow_orm, case_orm, file_orm) -> WorkflowProcessingJobORM:
    orm = WorkflowProcessingJobORM(
        uuid=uuid4(),
        temporal_workflow_id=f"CASE#{case_orm.uuid.hex}_FILE#{file_orm.uuid.hex}",
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        workflow_case_id=case_orm.uuid,
        file_id=file_orm.uuid,
        last_seq=0,
    )
    async_session.add(orm)
    await async_session.commit()
    return orm


def _build_input(processing_job, tenant, workflow, case, file_orm) -> PersistClassifiedDocumentsInput:
    return PersistClassifiedDocumentsInput(
        processing_job_uuid=processing_job.uuid,
        tenant_id=tenant.uuid,
        workflow_id=workflow.uuid,
        case_id=case.uuid,
        file_id=file_orm.uuid,
        documents=[
            ClassifiedDocumentRef(
                document_type_id=None,
                document_type_name="Cédula",
                document_index=0,
                page_range={"from": 1, "to": 1},
            ),
            ClassifiedDocumentRef(
                document_type_id=None,
                document_type_name="Póliza",
                document_index=1,
                page_range={"from": 2, "to": 5},
            ),
        ],
    )


async def test_persist__creates_one_row_per_classified_doc(
    activity, async_session, tenant_orm, workflow_orm, case_orm, file_orm
):
    processing_job = await _seed_processing_job(async_session, tenant_orm, workflow_orm, case_orm, file_orm)

    output = await activity.persist_classified_documents(
        _build_input(processing_job, tenant_orm, workflow_orm, case_orm, file_orm)
    )

    expect(output.documents).to(have_length(2))

    rows = (
        (
            await async_session.execute(
                select(WorkflowDocumentORM)
                .where(WorkflowDocumentORM.processing_job_id == processing_job.uuid)
                .order_by(WorkflowDocumentORM.document_index.asc())
            )
        )
        .scalars()
        .all()
    )

    expect(rows).to(have_length(2))
    expect(rows[0].document_index).to(equal(0))
    expect(rows[1].document_index).to(equal(1))
    expect(rows[0].processing_status).to(equal(DocumentStatus.EXTRACTING.value))
    expect(rows[0].page_range).to(equal({"from": 1, "to": 1}))
    expect(rows[1].page_range).to(equal({"from": 2, "to": 5}))


async def test_persist__idempotent_on_replay(activity, async_session, tenant_orm, workflow_orm, case_orm, file_orm):
    processing_job = await _seed_processing_job(async_session, tenant_orm, workflow_orm, case_orm, file_orm)
    payload = _build_input(processing_job, tenant_orm, workflow_orm, case_orm, file_orm)

    first = await activity.persist_classified_documents(payload)
    second = await activity.persist_classified_documents(payload)

    rows = (
        (
            await async_session.execute(
                select(WorkflowDocumentORM).where(WorkflowDocumentORM.processing_job_id == processing_job.uuid)
            )
        )
        .scalars()
        .all()
    )

    expect(rows).to(have_length(2))
    expect(second.documents).to(have_length(2))
    # The replay returns the same UUIDs as the original insert.
    first_ids = sorted(d.document_id for d in first.documents)
    second_ids = sorted(d.document_id for d in second.documents)
    expect(second_ids).to(equal(first_ids))


async def test_persist__empty_input_creates_no_rows(
    activity, async_session, tenant_orm, workflow_orm, case_orm, file_orm
):
    processing_job = await _seed_processing_job(async_session, tenant_orm, workflow_orm, case_orm, file_orm)

    output = await activity.persist_classified_documents(
        PersistClassifiedDocumentsInput(
            processing_job_uuid=processing_job.uuid,
            tenant_id=tenant_orm.uuid,
            workflow_id=workflow_orm.uuid,
            case_id=case_orm.uuid,
            file_id=file_orm.uuid,
            documents=[],
        )
    )

    expect(output.documents).to(have_length(0))

    rows = (
        (
            await async_session.execute(
                select(WorkflowDocumentORM).where(WorkflowDocumentORM.processing_job_id == processing_job.uuid)
            )
        )
        .scalars()
        .all()
    )
    expect(rows).to(have_length(0))


async def test_persist__stamps_sealed_document_type_version(
    activity, async_session, tenant_orm, workflow_orm, case_orm, file_orm
):
    processing_job = await _seed_processing_job(async_session, tenant_orm, workflow_orm, case_orm, file_orm)
    doctype = DocumentTypeORM(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        name="Cédula",
        current_version=3,
    )
    async_session.add(doctype)
    await async_session.commit()

    await activity.persist_classified_documents(
        PersistClassifiedDocumentsInput(
            processing_job_uuid=processing_job.uuid,
            tenant_id=tenant_orm.uuid,
            workflow_id=workflow_orm.uuid,
            case_id=case_orm.uuid,
            file_id=file_orm.uuid,
            documents=[
                ClassifiedDocumentRef(
                    document_type_id=doctype.uuid,
                    document_type_name="Cédula",
                    document_index=0,
                    page_range=None,
                ),
                # Doc sin tipo ("Otros") ⇒ versión NULL.
                ClassifiedDocumentRef(
                    document_type_id=None,
                    document_type_name="Otro",
                    document_index=1,
                    page_range=None,
                ),
            ],
            document_type_versions={str(doctype.uuid): 3},
        )
    )

    rows = (
        (
            await async_session.execute(
                select(WorkflowDocumentORM)
                .where(WorkflowDocumentORM.processing_job_id == processing_job.uuid)
                .order_by(WorkflowDocumentORM.document_index.asc())
            )
        )
        .scalars()
        .all()
    )

    expect(rows).to(have_length(2))
    expect(rows[0].document_type_version).to(equal(3))
    expect(rows[1].document_type_version).to(equal(None))


async def test_persist__page_range_none_persists_as_null(
    activity, async_session, tenant_orm, workflow_orm, case_orm, file_orm
):
    processing_job = await _seed_processing_job(async_session, tenant_orm, workflow_orm, case_orm, file_orm)

    await activity.persist_classified_documents(
        PersistClassifiedDocumentsInput(
            processing_job_uuid=processing_job.uuid,
            tenant_id=tenant_orm.uuid,
            workflow_id=workflow_orm.uuid,
            case_id=case_orm.uuid,
            file_id=file_orm.uuid,
            documents=[
                ClassifiedDocumentRef(
                    document_type_id=None,
                    document_type_name="Cédula",
                    document_index=0,
                    page_range=None,
                ),
            ],
        )
    )

    rows = (
        (
            await async_session.execute(
                select(WorkflowDocumentORM).where(WorkflowDocumentORM.processing_job_id == processing_job.uuid)
            )
        )
        .scalars()
        .all()
    )

    expect(rows).to(have_length(1))
    expect(rows[0].page_range).to(equal(None))
