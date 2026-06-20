"""E5 · diseño §2.1: CreateChildCases — fan-out idempotente a child cases.

Clave determinista ``(parent_case_id, document_index)`` materializada como
``external_ref`` (``{base}-{idx+1:03d}``, unique por workflow): check-then-insert
con recuperación de carrera por IntegrityError (patrón FindOrCreateCaseM2M).
Cada child hereda SELLADO ``pipeline_id``/``pipeline_version_id``/``created_by``
del padre y su doc clasificado se reasigna (``source=SPLIT_CHILD``).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from expects import be_none, be_true, contain, equal, expect, have_length
from sqlalchemy.exc import IntegrityError
from temporalio.exceptions import ApplicationError

from src.common.domain.entities.workflows.case_runtime import ChildCaseDocumentRef
from src.common.domain.enums.workflow_cases import WorkflowCaseStatus
from src.common.domain.enums.workflows import WorkflowDocumentSource
from src.common.domain.exceptions.processing import CaseNotFoundError
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.application.workflow_cases.fan_out import (
    EXTERNAL_REF_COLLISION_TYPE,
    CreateChildCases,
    child_case_name,
    child_external_ref,
)

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_PIPELINE = UUID("66666666-6666-6666-6666-666666666666")
_VERSION = UUID("77777777-7777-7777-7777-777777777777")
_CREATOR = UUID("88888888-8888-8888-8888-888888888888")


def _parent(external_ref: str | None = "CIRC-9") -> WorkflowCase:
    return WorkflowCase(
        uuid=uuid4(),
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        name="Circular Judicial 9",
        status=WorkflowCaseStatus.RECEIVING,
        external_ref=external_ref,
        pipeline_id=_PIPELINE,
        pipeline_version_id=_VERSION,
        created_by=_CREATOR,
    )


def _doc_ref(index: int, doc_id: UUID | None = None, type_name: str = "Persona") -> ChildCaseDocumentRef:
    return ChildCaseDocumentRef(
        document_id=doc_id or uuid4(),
        document_index=index,
        document_type_name=type_name,
    )


def _document(doc_id: UUID, case_id: UUID) -> WorkflowDocument:
    return WorkflowDocument(
        uuid=doc_id,
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        case_id=case_id,
        source=WorkflowDocumentSource.BULK,
    )


class _FakeCaseRepo:
    def __init__(self, parent: WorkflowCase | None, fail_creates: int = 0):
        self._cases: dict[UUID, WorkflowCase] = {}
        if parent is not None:
            self._cases[parent.uuid] = parent
        self.created: list[WorkflowCase] = []
        self._fail_creates = fail_creates

    async def find_by_id(self, case_id, tenant_id):
        return self._cases.get(case_id)

    async def find_by_external_ref(self, workflow_id, external_ref, tenant_id):
        for case in self._cases.values():
            if case.workflow_id == workflow_id and case.external_ref == external_ref:
                return case
        return None

    def seed(self, case: WorkflowCase) -> None:
        """Inserta un caso preexistente (p. ej. ajeno) sin pasar por create()."""
        self._cases[case.uuid] = case

    async def create(self, case):
        if self._fail_creates > 0:
            self._fail_creates -= 1
            # Simula que OTRO attempt ganó la carrera del unique: la fila ya
            # existe. El ganador es un child legítimo (mismo parent_case_id).
            self._cases[case.uuid] = case.model_copy(update={"name": "winner"})
            raise IntegrityError("INSERT", {}, Exception("uq_workflow_cases_workflow_external_ref"))
        self._cases[case.uuid] = case
        self.created.append(case)
        return case


class _FakeDocRepo:
    def __init__(self, documents: list[WorkflowDocument]):
        self._docs = {d.uuid: d for d in documents}
        self.updated: list[WorkflowDocument] = []

    async def find_by_id(self, document_id, tenant_id):
        return self._docs.get(document_id)

    async def update(self, document):
        self._docs[document.uuid] = document
        self.updated.append(document)
        return document


def _use_case(parent, case_repo, doc_repo, refs, *, file_id=None, processing_job_uuid=None) -> CreateChildCases:
    return CreateChildCases(
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        parent_case_id=parent.uuid,
        documents=refs,
        case_repository=case_repo,
        document_repository=doc_repo,
        file_id=file_id,
        processing_job_uuid=processing_job_uuid,
    )


async def test_create_child_cases__creates_one_child_per_doc_with_sealed_lineage():
    parent = _parent()
    doc_ids = [uuid4(), uuid4(), uuid4()]
    refs = [_doc_ref(i, doc_ids[i]) for i in range(3)]
    case_repo = _FakeCaseRepo(parent)
    doc_repo = _FakeDocRepo([_document(d, parent.uuid) for d in doc_ids])

    result = await _use_case(parent, case_repo, doc_repo, refs).execute()

    expect(result.children).to(have_length(3))
    expect(result.created_count).to(equal(3))
    for i, child in enumerate(result.children):
        expect(child.created).to(be_true)
        expect(child.case.parent_case_id).to(equal(parent.uuid))
        expect(child.case.external_ref).to(equal(f"CIRC-9-{i + 1:03d}"))
        expect(child.case.name).to(equal(f"Persona {i + 1}"))
        expect(child.case.status).to(equal(WorkflowCaseStatus.PROCESSING))
        # Herencia SELLADA: misma receta del padre, jamás re-resuelta a current.
        expect(child.case.pipeline_id).to(equal(_PIPELINE))
        expect(child.case.pipeline_version_id).to(equal(_VERSION))
        expect(child.case.created_by).to(equal(_CREATOR))


async def test_create_child_cases__reassigns_docs_to_child_as_split_child():
    parent = _parent()
    doc_id = uuid4()
    case_repo = _FakeCaseRepo(parent)
    doc_repo = _FakeDocRepo([_document(doc_id, parent.uuid)])

    result = await _use_case(parent, case_repo, doc_repo, [_doc_ref(0, doc_id)]).execute()

    expect(doc_repo.updated).to(have_length(1))
    moved = doc_repo.updated[0]
    expect(moved.case_id).to(equal(result.children[0].case.uuid))
    expect(moved.source).to(equal(WorkflowDocumentSource.SPLIT_CHILD))
    # Sin doc bulk original en el flujo estándar ⇒ parent_document_id NULL.
    expect(moved.parent_document_id).to(be_none)


async def test_create_child_cases__is_idempotent_on_retry():
    parent = _parent()
    doc_ids = [uuid4(), uuid4()]
    refs = [_doc_ref(i, doc_ids[i]) for i in range(2)]
    case_repo = _FakeCaseRepo(parent)
    doc_repo = _FakeDocRepo([_document(d, parent.uuid) for d in doc_ids])

    first = await _use_case(parent, case_repo, doc_repo, refs).execute()
    second = await _use_case(parent, case_repo, doc_repo, refs).execute()

    # Mismos children (clave determinista), sin duplicados.
    expect(second.created_count).to(equal(0))
    expect([c.case.uuid for c in second.children]).to(equal([c.case.uuid for c in first.children]))
    expect(case_repo.created).to(have_length(2))
    # Reasignación idempotente: el doc ya estaba en su child ⇒ sin re-update.
    expect(doc_repo.updated).to(have_length(2))


async def test_create_child_cases__integrity_race_adopts_winner():
    parent = _parent()
    doc_id = uuid4()
    case_repo = _FakeCaseRepo(parent, fail_creates=1)
    doc_repo = _FakeDocRepo([_document(doc_id, parent.uuid)])

    result = await _use_case(parent, case_repo, doc_repo, [_doc_ref(0, doc_id)]).execute()

    expect(result.children).to(have_length(1))
    expect(result.children[0].created).to(equal(False))
    expect(result.children[0].case.name).to(equal("winner"))


async def test_create_child_cases__parent_without_external_ref_uses_uuid_prefix():
    parent = _parent(external_ref=None)
    doc_id = uuid4()
    case_repo = _FakeCaseRepo(parent)
    doc_repo = _FakeDocRepo([_document(doc_id, parent.uuid)])

    result = await _use_case(parent, case_repo, doc_repo, [_doc_ref(4, doc_id)]).execute()

    expect(result.children[0].case.external_ref).to(equal(f"{parent.uuid.hex[:8]}-005"))


async def test_create_child_cases__parent_not_found_raises():
    parent = _parent()
    case_repo = _FakeCaseRepo(None)
    doc_repo = _FakeDocRepo([])

    with pytest.raises(CaseNotFoundError):
        await _use_case(parent, case_repo, doc_repo, [_doc_ref(0)]).execute()


def test_child_external_ref__is_deterministic_per_document_index():
    parent = _parent()

    expect(child_external_ref(parent, 0)).to(equal("CIRC-9-001"))
    expect(child_external_ref(parent, 0)).to(equal(child_external_ref(parent, 0)))
    expect(child_external_ref(parent, 11)).to(equal("CIRC-9-012"))


def test_child_case_name__falls_back_without_type_name():
    expect(child_case_name(ChildCaseDocumentRef(document_id=uuid4(), document_index=2))).to(
        equal("Documento 3")
    )


# ─── C1 · lineage: jamás adoptar un caso ajeno por colisión de external_ref ───


async def test_fan_out__preexisting_case_without_parent_collides__not_adopted():
    """C1: un caso NO-child preexistente con el ref colisionante ⇒ no se adopta
    (lanza ApplicationError non-retryable), su doc NO se reasigna."""
    parent = _parent()
    doc_id = uuid4()
    case_repo = _FakeCaseRepo(parent)
    # Caso ajeno (parent_case_id=None) que ya ocupa el ref que generaría el child 0.
    foreign = WorkflowCase(
        uuid=uuid4(),
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        name="Caso ajeno del cliente",
        status=WorkflowCaseStatus.PROCESSING,
        external_ref="CIRC-9-001",  # colisiona con child_external_ref(parent, 0)
        parent_case_id=None,
    )
    case_repo.seed(foreign)
    doc_repo = _FakeDocRepo([_document(doc_id, parent.uuid)])

    with pytest.raises(ApplicationError) as exc:
        await _use_case(parent, case_repo, doc_repo, [_doc_ref(0, doc_id)]).execute()

    expect(exc.value.type).to(equal(EXTERNAL_REF_COLLISION_TYPE))
    expect(exc.value.non_retryable).to(be_true)
    expect(str(exc.value)).to(contain("CIRC-9-001"))
    # El doc del caso ajeno NUNCA fue reasignado: cero fugas entre expedientes.
    expect(doc_repo.updated).to(equal([]))


async def test_fan_out__preexisting_case_with_other_parent_collides__not_adopted():
    """C1: ref colisionante con un child de OTRO padre ⇒ tampoco se adopta."""
    parent = _parent()
    other_parent_id = uuid4()
    case_repo = _FakeCaseRepo(parent)
    foreign_child = WorkflowCase(
        uuid=uuid4(),
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        name="Child de otro padre",
        status=WorkflowCaseStatus.PROCESSING,
        external_ref="CIRC-9-001",
        parent_case_id=other_parent_id,
    )
    case_repo.seed(foreign_child)
    doc_repo = _FakeDocRepo([_document(uuid4(), parent.uuid)])

    with pytest.raises(ApplicationError) as exc:
        await _use_case(parent, case_repo, doc_repo, [_doc_ref(0)]).execute()

    expect(exc.value.type).to(equal(EXTERNAL_REF_COLLISION_TYPE))


async def test_fan_out__own_child_with_matching_lineage_is_adopted_idempotently():
    """C1: un child legítimo del MISMO padre sí se adopta (idempotencia)."""
    parent = _parent()
    case_repo = _FakeCaseRepo(parent)
    own_child = WorkflowCase(
        uuid=uuid4(),
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        name="Mi child",
        status=WorkflowCaseStatus.PROCESSING,
        external_ref="CIRC-9-001",
        parent_case_id=parent.uuid,
    )
    case_repo.seed(own_child)
    doc_id = uuid4()
    doc_repo = _FakeDocRepo([_document(doc_id, parent.uuid)])

    result = await _use_case(parent, case_repo, doc_repo, [_doc_ref(0, doc_id)]).execute()

    expect(result.children).to(have_length(1))
    expect(result.children[0].created).to(equal(False))
    expect(result.children[0].case.uuid).to(equal(own_child.uuid))


# ─── C2 · un 2º archivo crea HERMANOS nuevos (no absorbe children ajenos) ─────


async def test_fan_out__second_file_creates_new_siblings_not_reusing_first_split():
    """C2: el mismo padre + un file_id distinto ⇒ refs distintos ⇒ children
    NUEVOS (no reasigna docs del archivo nuevo a children del primer split)."""
    parent = _parent()
    file_a, file_b = uuid4(), uuid4()
    case_repo = _FakeCaseRepo(parent)

    # Primer archivo: crea 2 children con namespace de file_a.
    doc_a = [uuid4(), uuid4()]
    doc_repo_a = _FakeDocRepo([_document(d, parent.uuid) for d in doc_a])
    first = await _use_case(
        parent, case_repo, doc_repo_a, [_doc_ref(i, doc_a[i]) for i in range(2)], file_id=file_a
    ).execute()

    # Segundo archivo: mismo padre, file_b ⇒ refs distintos ⇒ children nuevos.
    doc_b = [uuid4(), uuid4()]
    doc_repo_b = _FakeDocRepo([_document(d, parent.uuid) for d in doc_b])
    second = await _use_case(
        parent, case_repo, doc_repo_b, [_doc_ref(i, doc_b[i]) for i in range(2)], file_id=file_b
    ).execute()

    first_ids = {c.case.uuid for c in first.children}
    second_ids = {c.case.uuid for c in second.children}
    expect(first_ids & second_ids).to(equal(set()))  # cero solapamiento
    expect(second.created_count).to(equal(2))  # hermanos REALMENTE creados
    # Cada ref del segundo split lleva el namespace de file_b (no de file_a).
    for child in second.children:
        expect(child.case.external_ref).to(contain(file_b.hex[:8]))
        expect(child.case.external_ref).not_to(contain(file_a.hex[:8]))


async def test_fan_out__same_file_retry_is_idempotent_with_origin_namespace():
    """C2: el MISMO file_id (retry del mismo run) reusa los children — la
    idempotencia se conserva pese al namespace."""
    parent = _parent()
    file_a = uuid4()
    case_repo = _FakeCaseRepo(parent)
    doc_ids = [uuid4(), uuid4()]
    refs = [_doc_ref(i, doc_ids[i]) for i in range(2)]
    doc_repo = _FakeDocRepo([_document(d, parent.uuid) for d in doc_ids])

    first = await _use_case(parent, case_repo, doc_repo, refs, file_id=file_a).execute()
    second = await _use_case(parent, case_repo, doc_repo, refs, file_id=file_a).execute()

    expect(second.created_count).to(equal(0))
    expect([c.case.uuid for c in second.children]).to(equal([c.case.uuid for c in first.children]))


def test_child_external_ref__namespaces_by_origin_key():
    parent = _parent()
    ref = child_external_ref(parent, 0, "deadbeef")
    expect(ref).to(equal("CIRC-9-deadbeef-001"))
    # Sin origin: forma compat E4.
    expect(child_external_ref(parent, 0)).to(equal("CIRC-9-001"))


def test_child_external_ref__truncates_to_column_limit():
    """C1 minor: el ref jamás desborda String(255).

    El padre puede tener un external_ref de hasta 255 chars (límite de la
    columna); el sufijo namespace+índice del child empujaría por encima ⇒ se
    recorta la base para que el ref del child quepa en String(255)."""
    parent = _parent(external_ref="X" * 255)
    ref = child_external_ref(parent, 0, "deadbeef")
    expect(len(ref)).to(equal(255))
    expect(ref.endswith("-deadbeef-001")).to(be_true)
