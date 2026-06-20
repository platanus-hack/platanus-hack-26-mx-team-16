"""Helpers compartidos para el dispatch de extracción.

El use case original `ExtractFileIntoCaseDocuments` se eliminó al
refactorizar la persistencia (ver product/plans/processing-jobs/workflow_persistence.md). Su lógica
vive ahora en `dispatch_extraction_job` (presentation) +
`RunAndPersistDocumentProcessing` (application). Solo conservamos los dos
helpers utilitarios que el endpoint sigue necesitando.
"""

from uuid import UUID

from src.common.domain.models.processing.document_type import DocumentType


def build_job_id(case_id: UUID, file_id: UUID) -> str:
    return f"CASE#{case_id.hex}_FILE#{file_id.hex}"


def doctype_to_temporal_dict(dt: DocumentType) -> dict:
    """Seal a doc type into the lambda contract dict (D6').

    ``slug`` + ``schema_version`` formalize the de-facto sealing: the dict
    travels in ``DocumentProcessingInput.document_types`` and pins the
    CURRENT version at dispatch time — later doc type edits never affect an
    in-flight run. ``schema_version`` is what ``persist_classified_documents``
    stamps onto ``workflow_documents.document_type_version``.
    """
    schema = dt.fields or {}
    fields = schema.get("fields") if isinstance(schema, dict) and "fields" in schema else schema
    return {
        "uuid": str(dt.uuid),
        "name": dt.name,
        "slug": dt.slug,
        "description": dt.description or "",
        "fields": fields if fields is not None else schema,
        "validation_rules": dt.validation_rules or [],
        "schema_version": dt.current_version,
    }


def doctype_versions_from_temporal_dicts(document_types: list[dict]) -> dict[str, int]:
    """``{document_type_uuid: schema_version}`` from already-sealed dicts.

    Helper for the persist phase: derives the version map that
    ``PersistClassifiedDocumentsInput.document_type_versions`` carries from
    the dicts sealed in ``DocumentProcessingInput.document_types``.
    """
    return {
        str(d["uuid"]): int(d["schema_version"])
        for d in document_types
        if d.get("uuid") and d.get("schema_version") is not None
    }
