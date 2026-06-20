"""Inputs for the generic pipeline interpreter (F1).

``PipelineRunInput`` seals ``pipeline_id`` + ``version`` at start time so the
recipe an in-flight run walks can never change underneath it (Temporal
determinism). The first wave reuses the existing extraction input verbatim as
the run's seed ``document``; later phase families read/write their own state.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from src.common.domain.entities.workflows.document_processing import (
    DocumentProcessingInput,
)


class PipelineRunInput(BaseModel):
    pipeline_id: UUID
    version: int
    document: DocumentProcessingInput
    # Artefactos pre-sembrados para runs que arrancan a mitad de receta
    # (re-extracción E1: `classify_pages` + `persisted_docs` ya existen).
    # Solo refs S3 + metadatos compactos — límite 2 MiB de Temporal.
    initial_artifacts: dict = Field(default_factory=dict)
    # Continúa el seq monotónico del set para que el replay/dedupe del FE
    # no descarte los eventos del nuevo run (re-extracción).
    starting_seq: int = 0
    # E4 · diseño §3: filtra las fases de la receta por su scope ANTES del
    # loop. None = full (comportamiento E1–E3 intacto); "document" ⇒ solo
    # fases document-scope (upload/llegada); "case" ⇒ solo case-scope (CASE#).
    scope: str | None = None
    # ADR 0002 · §3.3: sub-segmento del único pipeline del workflow por punto de
    # entrada. None/"ingest" = todas las fases; "reextract" = cola de extracción
    # (sin OCR/clasify, sin webhook); "data" = desde la primera ``analyze``.
    entry_point: str | None = None


class LoadPipelineVersionInput(BaseModel):
    pipeline_id: UUID
    version: int


class LoadPipelineVersionOutput(BaseModel):
    pipeline_id: UUID
    version: int
    phases: list[dict] = Field(default_factory=list)
    output_schema: dict | None = None
    # D-A: el intérprete deriva activación + completitud de la config de fase
    # (extraction_gate.config.activation / await_documents.config) vía los helpers.
