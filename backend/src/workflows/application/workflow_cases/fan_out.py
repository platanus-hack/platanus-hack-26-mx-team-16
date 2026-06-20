"""Fan-out a child cases (E5 · diseño §2.1).

:class:`CreateChildCases` materializa un child case por documento clasificado
cuando ``classify_pages`` corre con ``fan_out: "child_cases"``. Idempotente
ante retries de la activity: la clave determinista es
``(parent_case_id, document_index)``, materializada como ``external_ref``
(``{base}-{idx+1:03d}``, unique por workflow) — check-then-insert con
recuperación de carrera por ``IntegrityError`` (patrón ``FindOrCreateCaseM2M``).

Cada child hereda SELLADO del padre: ``pipeline_id``/``pipeline_version_id``
(la misma receta — jamás re-resuelta a current) y ``created_by``. El doc
clasificado se reasigna a su child (``case_id=child``, ``source=SPLIT_CHILD``);
``parent_document_id`` solo se estampa si existe un doc bulk original
(en el flujo estándar el doc clasificado ES el original ⇒ NULL).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from temporalio.exceptions import ApplicationError

from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.case_runtime import ChildCaseDocumentRef
from src.common.domain.enums.workflow_cases import WorkflowCaseStatus
from src.common.domain.enums.workflows import WorkflowDocumentSource
from src.common.domain.exceptions.processing import CaseNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository

logger = get_logger(__name__)

# E5 · fan-out: errores non-retryable que dejan el run en fallo visible en vez
# de corromper expedientes (C1 — adopción de caso ajeno por colisión de ref).
EXTERNAL_REF_COLLISION_TYPE = "fan_out.external_ref_collision"

# ``workflow_cases.external_ref`` es String(255): el ref del child jamás puede
# desbordarla (C1 — minor). Reservamos espacio para los sufijos namespace+índice.
_EXTERNAL_REF_MAX_LEN = 255


def child_external_ref(
    parent: WorkflowCase, document_index: int, origin_key: str | None = None
) -> str:
    """Clave determinista del child (unique por workflow).

    Forma ``{base}-{origin}-{idx+1:03d}`` cuando hay ``origin_key`` (C2: el
    file_id/processing_job del run, estable dentro del run ⇒ idempotente ante
    retries, pero un 2º archivo genera HERMANOS nuevos en vez de reusar los del
    primer split). Sin origin: ``{base}-{idx+1:03d}`` (compat). El ref se recorta
    a String(255) reservando espacio para los sufijos (C1 minor).
    """
    base = parent.external_ref or parent.uuid.hex[:8]
    suffix = f"-{origin_key}-{document_index + 1:03d}" if origin_key else f"-{document_index + 1:03d}"
    max_base = _EXTERNAL_REF_MAX_LEN - len(suffix)
    if max_base < 1:
        # origin_key patológicamente largo (no debería ocurrir: derivado de un
        # hex[:8]); cae a la base mínima estable.
        base = parent.uuid.hex[:8]
        max_base = _EXTERNAL_REF_MAX_LEN - len(suffix)
    return f"{base[:max_base]}{suffix}"


def child_case_name(ref: ChildCaseDocumentRef) -> str:
    """Etiqueta del doc clasificado: ``"{tipo} {índice+1}"``."""
    label = ref.document_type_name or "Documento"
    return f"{label} {ref.document_index + 1}"[:255]


@dataclass
class CreatedChildCase:
    case: WorkflowCase
    document_index: int
    created: bool


@dataclass
class CreateChildCasesResult:
    children: list[CreatedChildCase] = field(default_factory=list)

    @property
    def created_count(self) -> int:
        return sum(1 for child in self.children if child.created)


@dataclass
class CreateChildCases(UseCase):
    tenant_id: UUID
    workflow_id: UUID
    parent_case_id: UUID
    documents: list[ChildCaseDocumentRef]
    case_repository: WorkflowCaseRepository
    document_repository: WorkflowDocumentRepository
    # C2: discrimina la clave del child por origen (file/processing_job del run).
    file_id: UUID | None = None
    processing_job_uuid: UUID | None = None

    @property
    def origin_key(self) -> str | None:
        """Namespace estable del run para la clave del child (C2)."""
        origin = self.file_id or self.processing_job_uuid
        return origin.hex[:8] if origin is not None else None

    async def execute(self) -> CreateChildCasesResult:
        parent = await self.case_repository.find_by_id(self.parent_case_id, self.tenant_id)
        if parent is None:
            raise CaseNotFoundError(str(self.parent_case_id))

        result = CreateChildCasesResult()
        for ref in sorted(self.documents, key=lambda d: d.document_index):
            child, created = await self._find_or_create_child(parent, ref)
            await self._reassign_document(ref, child)
            result.children.append(
                CreatedChildCase(case=child, document_index=ref.document_index, created=created)
            )
        return result

    def _assert_lineage(self, existing: WorkflowCase, parent: WorkflowCase, external_ref: str) -> None:
        """C1: jamás adoptar un caso cuyo padre no sea ESTE padre.

        ``external_ref`` es controlado por el cliente (find-or-create M2M /
        x-source ingest), así que una colisión puede hacer que el fan-out se
        apropie de un expediente ajeno (sin parent, o con otro parent) y le
        reasigne documentos. Si el lineage no coincide, fallamos el run con un
        error non-retryable visible en vez de corromper expedientes.
        """
        if existing.parent_case_id != parent.uuid:
            raise ApplicationError(
                f"[fan_out] external_ref {external_ref!r} ya pertenece a un caso "
                f"({existing.uuid}) cuyo parent_case_id ({existing.parent_case_id}) "
                f"no es el padre del split ({parent.uuid}); no se adopta.",
                type=EXTERNAL_REF_COLLISION_TYPE,
                non_retryable=True,
            )

    async def _find_or_create_child(
        self, parent: WorkflowCase, ref: ChildCaseDocumentRef
    ) -> tuple[WorkflowCase, bool]:
        external_ref = child_external_ref(parent, ref.document_index, self.origin_key)
        # Check-then-insert (idempotencia ante retries de la activity).
        existing = await self.case_repository.find_by_external_ref(
            self.workflow_id, external_ref, self.tenant_id
        )
        if existing is not None:
            self._assert_lineage(existing, parent, external_ref)
            return existing, False

        child = WorkflowCase(
            uuid=uuid4(),
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            name=child_case_name(ref),
            # El child nace completo (diseño §2.1) — su await_documents lo
            # auto-readea; PROCESSING desde el nacimiento evita el limbo RECEIVING.
            status=WorkflowCaseStatus.PROCESSING,
            external_ref=external_ref,
            # Herencia SELLADA del padre: misma receta, jamás current.
            pipeline_id=parent.pipeline_id,
            pipeline_version_id=parent.pipeline_version_id,
            parent_case_id=parent.uuid,
            created_by=parent.created_by,
        )
        try:
            created = await self.case_repository.create(child)
            return created, True
        except IntegrityError:
            # Carrera sobre el unique (workflow, external_ref): otro attempt
            # de la activity ganó entre el find y el insert — adoptarlo SOLO si
            # es lineage nuestro (C1: una colisión con un caso ajeno también se
            # manifiesta aquí cuando el cliente insertó el ref entre el find y el
            # insert).
            winner = await self.case_repository.find_by_external_ref(
                self.workflow_id, external_ref, self.tenant_id
            )
            if winner is None:
                raise
            self._assert_lineage(winner, parent, external_ref)
            return winner, False

    async def _reassign_document(self, ref: ChildCaseDocumentRef, child: WorkflowCase) -> None:
        document = await self.document_repository.find_by_id(ref.document_id, self.tenant_id)
        if document is None:
            logger.warning(
                "fan_out.document_missing",
                document_id=str(ref.document_id),
                child_case_id=str(child.uuid),
            )
            return
        if (
            document.case_id == child.uuid
            and document.source == WorkflowDocumentSource.SPLIT_CHILD
        ):
            return  # retry idempotente: ya reasignado
        document.case_id = child.uuid
        document.source = WorkflowDocumentSource.SPLIT_CHILD
        await self.document_repository.update(document)
