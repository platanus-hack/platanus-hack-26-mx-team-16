"""Activity de la fase ``assess`` (E3): 1 llamada LLM por documento.

Lee el artefacto extract_text de S3 (el texto nunca viaja por la history de
Temporal — 2 MiB, TMPRL1103), slicea las páginas del documento con los
helpers de ``payload_helpers``, pide al :class:`AssessAgent` la capa-2 de
confianza por campo y persiste vía UPDATE directo (patrón
``persist_document_texts``; ``mark_document_status`` queda intacto para el
camino de estado):

- ``workflow_documents.extract_confidence`` = ``{campo: float 0..1}``
- ``workflow_documents.signals`` = ``{campo: {signals, explanation, candidates}}``
- ``needs_clarification`` = MERGE (los campos con señales se añaden sin
  duplicar lo que ya flaggeó otra fase).

Label-only: cualquier problema (S3, LLM, payload malformado) ⇒ warning y
``assessed=False`` — la activity nunca debe reventar el run.
"""

from __future__ import annotations

import asyncio
import json

import boto3
from botocore.client import BaseClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity

from src.common.application.logging import get_logger
from src.common.database.models.workflow_document import WorkflowDocumentORM
from src.workflows.infrastructure.services.assess.agent import (
    AssessAgent,
    AssessInput,
    build_assess_agent,
)
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    AssessDocumentInput,
    AssessDocumentOutput,
)
from src.workflows.presentation.workflows.activities.read_s3_json import split_s3_uri

logger = get_logger(__name__)


class AssessDocumentActivity:
    def __init__(
        self,
        session_maker: async_sessionmaker,
        assess_agent: AssessAgent,
        boto3_client: BaseClient | None = None,
    ) -> None:
        self._session_maker = session_maker
        self._agent = assess_agent
        self._client = boto3_client or boto3.client("s3")

    @activity.defn(name="assess_document")
    async def assess_document(self, payload: AssessDocumentInput) -> AssessDocumentOutput:
        from src.workflows.presentation.workflows.payload_helpers import (  # noqa: PLC0415
            build_page_text_map,
            slice_document_text,
        )

        data = AssessDocumentInput.model_validate(payload)
        if not data.fields:
            return AssessDocumentOutput()

        bucket, key = split_s3_uri(data.extract_text_source)
        body_bytes = await asyncio.to_thread(self._fetch_blocking, bucket, key)
        page_text_map = build_page_text_map(json.loads(body_bytes))
        document_text = slice_document_text(page_text_map, data.page_range)
        if not document_text:
            logger.warning(
                f"assess_document.no_text document_id={data.document_id} "
                f"source={data.extract_text_source} page_range={data.page_range}"
            )
            return AssessDocumentOutput()

        # phases-config: provider override per-pipeline ⇒ agente per-call;
        # sin override usa el singleton del worker (env-default, comportamiento de hoy).
        agent = build_assess_agent(data.provider) if data.provider else self._agent
        result = await agent.assess(
            AssessInput(
                fields=data.fields,
                document_text=document_text,
                document_type_name=data.document_type_name,
            )
        )
        if not result.fields:
            # JSON malformado / LLM caído: documento sin assess, nunca excepción.
            logger.warning(f"assess_document.no_assessment document_id={data.document_id}")
            return AssessDocumentOutput()

        flagged = list(result.flagged_fields)
        # phases-config · assess.min_confidence: añade los campos por debajo del
        # umbral. None ⇒ solo el flag por signals del agente (comportamiento de hoy).
        if data.min_confidence is not None:
            below = [
                field
                for field, conf in (result.extract_confidence or {}).items()
                if conf is not None and conf < data.min_confidence
            ]
            flagged = list(dict.fromkeys([*flagged, *below]))
        async with self._session_maker() as session:
            current = (
                await session.execute(
                    select(WorkflowDocumentORM.needs_clarification).where(WorkflowDocumentORM.uuid == data.document_id)
                )
            ).scalar_one_or_none()
            merged = list(dict.fromkeys([*(current or []), *flagged]))
            values: dict = {
                "extract_confidence": result.extract_confidence,
                "signals": result.signals or None,
            }
            if merged:
                values["needs_clarification"] = merged
            await session.execute(
                update(WorkflowDocumentORM).where(WorkflowDocumentORM.uuid == data.document_id).values(**values)
            )
            await session.commit()

        logger.info(
            f"assess_document.done document_id={data.document_id} fields={len(result.fields)} flagged={len(flagged)}"
        )
        return AssessDocumentOutput(
            assessed=True,
            fields_assessed=len(result.fields),
            flagged=flagged,
        )

    def _fetch_blocking(self, bucket: str, key: str) -> bytes:
        response = self._client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()
