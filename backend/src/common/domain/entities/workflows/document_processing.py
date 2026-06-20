from uuid import UUID

from pydantic import BaseModel, Field

# ─── Temporal Lambda Processing ────────────────────────────


class InvokeLambdaInput(BaseModel):
    function_name: str
    payload: dict


class ReadS3JsonInput(BaseModel):
    source: str


class DocumentProcessingInput(BaseModel):
    """Input del DocumentProcessingWorkflow.

    Campos requeridos: ruta del archivo en S3, lista de document_types
    (JSON del contrato de la lambda) y el `job_id` (string usado como
    Temporal workflow id).

    Campos opcionales para feedback live: `case_id`, `workflow_id`,
    `tenant_id`, `file_id` y `processing_job_uuid` permiten al workflow
    publicar eventos en Redis y persistir incrementalmente. Cuando
    `persist=False` el workflow corre standalone (debugging) sin tocar
    DB y sin emitir eventos — útil para `just start-workflow`.
    """

    object_key: str
    document_types: list[dict] = Field(default_factory=list)
    job_id: str

    case_id: UUID | None = None
    workflow_id: UUID | None = None
    tenant_id: UUID | None = None
    file_id: UUID | None = None
    file_name: str | None = None
    processing_job_uuid: UUID | None = None
    persist: bool = True


class BBoxHit(BaseModel):
    """Bounding box resuelto por la lambda `extract_fields` para una hoja escalar."""

    page_number: int
    polygon: list[dict]  # [{x,y}, {x,y}, {x,y}, {x,y}] — polígono 0..1
    matched_text: str
    confidence: float | None = None


class MappedLeaf(BaseModel):
    """Shape de cada hoja escalar dentro de `mapped_output` de la lambda."""

    value: str | int | float | bool | None = None
    source_text: str | None = None
    page_number: int | None = None
    bbox: list[BBoxHit] = Field(default_factory=list)
    inferred: bool = False


class DocumentProcessingOutput(BaseModel):
    """Resultado consolidado del pipeline. Sin persistencia — la capa de
    consumo posterior decide qué hacer con cada pieza.

    - `extract_text_source` / `classify_pages_source`: rutas S3 de los artefactos
      intermedios (OCR y clasificación). El contenido real se deja en S3 para
      auditoría/debug; los consumidores leen de ahí cuando lo necesitan.
    - `extract_fields` / `validate_extraction`: respuesta completa de la lambda
      batch (`{status, extractions|validations, errors, metadata}`) embebida
      inline para que la capa de persistencia no tenga que volver a S3.
    """

    job_id: str
    extract_text_source: str
    classify_pages_source: str
    extract_fields: dict = Field(default_factory=dict)
    validate_extraction: dict = Field(default_factory=dict)


# ─── Field Re-Extraction (run extract-only del intérprete, E1) ────────────────


class WorkflowDocumentRef(BaseModel):
    """Identity of a previously-persisted WorkflowDocument inside a set.

    El run de re-extracción no vuelve a correr `persist_classified_documents`,
    así que recibe los documentos ya persistidos como artefacto sembrado
    (`PipelineRunInput.initial_artifacts["persisted_docs"]`) — keyed by
    `document_index` so the lambda responses can be matched back to a row.
    """

    document_id: UUID
    document_type_id: UUID | None = None
    document_type_name: str | None = None
    document_index: int
    page_range: dict | None = None
