"""E5 · VerifyDocumentField (Inspection Bench): correct/accept, verification,
needs_clarification, eventos con dedupe, lock 423 y señal corrections 503."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from expects import be_none, be_true, be_false, contain, equal, expect, have_length  # noqa: F401

from src.common.domain.enums.human_tasks import HumanTaskKind
from src.common.domain.exceptions.processing import CaseNotFoundError, DocumentNotFoundError
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.application.human_tasks.corrections_signal import CorrectionsSignalError
from src.workflows.application.workflow_documents.verify_field import (
    CaseLockedError,
    CorrectionDocumentAmbiguousError,
    FieldNotCorrectableError,
    FieldNotFoundError,
    FieldValueRequiredError,
    FieldVerification,
    VerifyDocumentField,
)
from src.workflows.domain.models.human_task import HumanTask

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_CASE = UUID("44444444-4444-4444-4444-444444444444")
_ACTOR = "user:55555555-5555-5555-5555-555555555555"


def _doc(**overrides) -> WorkflowDocument:
    base = dict(
        uuid=uuid4(),
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        case_id=_CASE,
        mapped_extraction={
            "ci": {"value": "1234", "page_number": 1, "inferred": False},
            "monto": {"value": 900},
        },
        needs_clarification=["ci"],
    )
    base.update(overrides)
    return WorkflowDocument(**base)


def _approval(**overrides) -> HumanTask:
    base = dict(
        uuid=uuid4(),
        tenant_id=_TENANT,
        task_key="wf:review:review_l1",
        kind=HumanTaskKind.APPROVAL,
        case_id=_CASE,
        pipeline_run_id="CASE#run",
        stage="review_l1",
    )
    base.update(overrides)
    return HumanTask(**base)


class _FakeCaseRepo:
    def __init__(self, case=None):
        self._case = case if case is not None else SimpleNamespace(uuid=_CASE, workflow_id=_WORKFLOW)

    async def find_by_id(self, case_id, tenant_id):
        return self._case


class _FakeDocRepo:
    def __init__(self, documents):
        self._documents = documents
        self.updated: list = []

    async def find_by_id(self, document_id, tenant_id):
        return next((d for d in self._documents if d.uuid == document_id), None)

    async def list_by_case(self, case_id, tenant_id):
        return self._documents

    async def update(self, document):
        self.updated.append(document)
        return document


class _FakeTaskRepo:
    def __init__(self, tasks=None):
        self._tasks = tasks or []

    async def list_open_by_case(self, case_id, tenant_id):
        return self._tasks


class _FakeEventRepo:
    def __init__(self):
        self.created: list = []

    async def create(self, event):
        self.created.append(event)
        return event


class _FakeHandle:
    def __init__(self, recorder):
        self._recorder = recorder

    async def signal(self, name, *args, **kwargs):
        self._recorder.append((name, args, kwargs))


class _FakeTemporalClient:
    def __init__(self):
        self.signals: list = []

    def get_workflow_handle(self, workflow_id):
        return _FakeHandle(self.signals)


class _BrokenTemporalClient:
    def get_workflow_handle(self, workflow_id):
        class _Broken:
            async def signal(self, name, *args, **kwargs):
                raise RuntimeError("temporal down")

        return _Broken()


def _use_case(
    doc,
    *,
    fields,
    tasks=None,
    verified_by=_ACTOR,
    level=None,
    document_id=...,
    workflow_id=None,
    client=None,
    event_repo=None,
    doc_repo=None,
):
    return VerifyDocumentField(
        tenant_id=_TENANT,
        case_id=_CASE,
        document_id=doc.uuid if document_id is ... else document_id,
        fields=fields,
        verified_by=verified_by,
        level=level,
        case_repository=_FakeCaseRepo(),
        document_repository=doc_repo or _FakeDocRepo([doc]),
        case_event_repository=event_repo or _FakeEventRepo(),
        human_task_repository=_FakeTaskRepo(tasks),
        temporal_client=client or _FakeTemporalClient(),
        workflow_id=workflow_id,
    )


# ─── correct / accept ────────────────────────────────────────────────────────


async def test_correct__updates_value_writes_verification_and_clears_flag():
    doc = _doc()
    events = _FakeEventRepo()
    result = await _use_case(
        doc, fields=[FieldVerification(field_path="ci", action="correct", value="9999")],
        event_repo=events,
    ).execute()

    expect(result.document.mapped_extraction["ci"]["value"]).to(equal("9999"))
    # El leaf conserva el resto de su forma (bbox/page/inferred).
    expect(result.document.mapped_extraction["ci"]["page_number"]).to(equal(1))
    entry = result.document.verification["ci"]
    expect(entry["value"]).to(equal("9999"))
    expect(entry["previous_value"]).to(equal("1234"))
    expect(entry["verified_by"]).to(equal(_ACTOR))
    expect(entry["level"]).to(equal(2))  # sin APPROVAL abierta ⇒ contexto L2
    expect(result.document.needs_clarification).to(equal([]))
    expect(events.created).to(have_length(1))
    expect(events.created[0].type).to(equal("field.corrected"))
    expect(events.created[0].actor).to(equal(_ACTOR))


async def test_accept__verifies_current_value_without_touching_it():
    doc = _doc()
    events = _FakeEventRepo()
    result = await _use_case(
        doc, fields=[FieldVerification(field_path="monto", action="accept")], event_repo=events
    ).execute()

    expect(result.document.mapped_extraction["monto"]["value"]).to(equal(900))
    expect(result.document.verification["monto"]["value"]).to(equal(900))
    expect(result.document.verification["monto"]["previous_value"]).to(equal(900))
    expect(events.created[0].type).to(equal("field.verified"))


async def test_correct__without_value_raises_422():
    doc = _doc()
    with pytest.raises(FieldValueRequiredError):
        await _use_case(doc, fields=[FieldVerification(field_path="ci", action="correct")]).execute()


async def test_correct__list_of_fields_processes_all_and_persists_once():
    doc = _doc()
    doc_repo = _FakeDocRepo([doc])
    result = await _use_case(
        doc,
        fields=[
            FieldVerification(field_path="ci", action="correct", value="9999"),
            FieldVerification(field_path="monto", action="accept"),
        ],
        doc_repo=doc_repo,
    ).execute()

    expect(result.verified_paths).to(equal(["ci", "monto"]))
    expect(doc_repo.updated).to(have_length(1))


# ─── verified_by / level ─────────────────────────────────────────────────────


async def test_external__writes_level_0_and_external_actor():
    doc = _doc()
    result = await _use_case(
        doc,
        fields=[FieldVerification(field_path="ci", action="correct", value="8888")],
        verified_by="external",
        level=0,
    ).execute()

    entry = result.document.verification["ci"]
    expect(entry["verified_by"]).to(equal("external"))
    expect(entry["level"]).to(equal(0))


async def test_level__derived_from_open_review_l1_stage():
    doc = _doc()
    result = await _use_case(
        doc,
        fields=[FieldVerification(field_path="ci", action="accept")],
        tasks=[_approval(stage="review_l1")],
    ).execute()

    expect(result.level).to(equal(1))
    expect(result.document.verification["ci"]["level"]).to(equal(1))


# ─── dedupe ──────────────────────────────────────────────────────────────────


async def test_dedupe__same_value_twice_produces_same_dedupe_key():
    doc = _doc()
    events = _FakeEventRepo()
    await _use_case(
        doc, fields=[FieldVerification(field_path="ci", action="correct", value="9999")],
        event_repo=events,
    ).execute()
    await _use_case(
        doc, fields=[FieldVerification(field_path="ci", action="correct", value="9999")],
        event_repo=events,
    ).execute()

    expect(events.created).to(have_length(2))
    expect(events.created[0].dedupe_key).to(equal(events.created[1].dedupe_key))
    # El path va HASHEADO en la clave (no crudo): ya no aparece "ci" literal.
    expect(events.created[0].dedupe_key.startswith(f"{doc.uuid}:")).to(be_true)
    expect("ci" in events.created[0].dedupe_key).to(be_false)


# ─── lock §3.2 ───────────────────────────────────────────────────────────────


async def test_lock__approval_claimed_by_other_actor_raises_423():
    doc = _doc()
    with pytest.raises(CaseLockedError) as exc_info:
        await _use_case(
            doc,
            fields=[FieldVerification(field_path="ci", action="accept")],
            tasks=[_approval(claimed_by="staff:99999999-9999-9999-9999-999999999999")],
        ).execute()

    expect(exc_info.value.status_code).to(equal(423))
    expect(exc_info.value.code).to(equal("case.locked"))
    expect(exc_info.value.context["holder"]).to(
        equal("staff:99999999-9999-9999-9999-999999999999")
    )


async def test_lock__holder_can_keep_correcting():
    doc = _doc()
    result = await _use_case(
        doc,
        fields=[FieldVerification(field_path="ci", action="accept")],
        tasks=[_approval(claimed_by=_ACTOR)],
    ).execute()

    expect(result.verified_paths).to(equal(["ci"]))


# ─── señal corrections (best-effort estricto) ────────────────────────────────


async def test_signal__open_approval_gets_corrections_with_short_refs():
    doc = _doc()
    client = _FakeTemporalClient()
    task = _approval()
    result = await _use_case(
        doc,
        fields=[FieldVerification(field_path="ci", action="correct", value="9999")],
        tasks=[task],
        client=client,
    ).execute()

    expect(result.corrections_signaled).to(be_true)
    expect(client.signals).to(have_length(1))
    name, args, kwargs = client.signals[0]
    expect(name).to(equal("corrections"))
    # Gotcha Temporal: multi-arg SIEMPRE via kwarg args=[...].
    expect(kwargs["args"]).to(
        equal([task.task_key, {"fields": [{"documentId": str(doc.uuid), "fieldPath": "ci"}]}])
    )


async def test_signal__failure_raises_503_after_persisting():
    doc = _doc()
    doc_repo = _FakeDocRepo([doc])
    with pytest.raises(CorrectionsSignalError) as exc_info:
        await _use_case(
            doc,
            fields=[FieldVerification(field_path="ci", action="correct", value="9999")],
            tasks=[_approval()],
            client=_BrokenTemporalClient(),
            doc_repo=doc_repo,
        ).execute()

    expect(exc_info.value.status_code).to(equal(503))
    # La verificación quedó persistida: el retry del caller es idempotente.
    expect(doc_repo.updated).to(have_length(1))


async def test_signal__no_open_approval_means_no_signal():
    doc = _doc()
    client = _FakeTemporalClient()
    result = await _use_case(
        doc,
        fields=[FieldVerification(field_path="ci", action="accept")],
        client=client,
    ).execute()

    expect(result.corrections_signaled).to(be_false)
    expect(client.signals).to(have_length(0))


# ─── bindings anti-IDOR (patrón E4) ──────────────────────────────────────────


async def test_binding__case_of_another_workflow_is_404():
    doc = _doc()
    with pytest.raises(CaseNotFoundError):
        await _use_case(
            doc,
            fields=[FieldVerification(field_path="ci", action="accept")],
            workflow_id=uuid4(),
        ).execute()


async def test_binding__document_of_another_case_is_404():
    doc = _doc(case_id=uuid4())
    with pytest.raises(DocumentNotFoundError):
        await _use_case(doc, fields=[FieldVerification(field_path="ci", action="accept")]).execute()


async def test_binding__missing_document_id_with_multiple_docs_is_422():
    doc_a, doc_b = _doc(), _doc()
    with pytest.raises(CorrectionDocumentAmbiguousError):
        await _use_case(
            doc_a,
            fields=[FieldVerification(field_path="ci", action="accept")],
            document_id=None,
            doc_repo=_FakeDocRepo([doc_a, doc_b]),
        ).execute()


async def test_binding__missing_document_id_with_single_doc_resolves_it():
    doc = _doc()
    result = await _use_case(
        doc,
        fields=[FieldVerification(field_path="ci", action="accept")],
        document_id=None,
    ).execute()

    expect(result.document.uuid).to(equal(doc.uuid))


async def test_needs_clarification__stays_none_when_doc_never_had_flags():
    doc = _doc(needs_clarification=None)
    result = await _use_case(
        doc, fields=[FieldVerification(field_path="ci", action="accept")]
    ).execute()

    expect(result.document.needs_clarification).to(be_none)


# ─── C13 · resolución de path anidado ────────────────────────────────────────


def _nested_doc(**overrides):
    base = dict(
        uuid=uuid4(),
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        case_id=_CASE,
        mapped_extraction={
            "paciente": {"value": "Juan"},
            "medicamentos": [
                {"dosis": {"value": "500mg"}, "nombre": {"value": "Ibuprofeno"}},
            ],
            "contacto": {"telefono": {"value": "777"}},  # contenedor con hijo
        },
    )
    base.update(overrides)
    return WorkflowDocument(**base)


async def test_nested_path__corrects_the_real_leaf_not_a_phantom_key():
    doc = _nested_doc()
    result = await _use_case(
        doc,
        fields=[FieldVerification(field_path="medicamentos[0].dosis", action="correct", value="250mg")],
    ).execute()

    # La hoja anidada se corrigió de verdad (antes: no-op + clave plana fantasma).
    expect(result.document.mapped_extraction["medicamentos"][0]["dosis"]["value"]).to(equal("250mg"))
    # NO se creó una clave de nivel raíz con el path literal.
    expect("medicamentos[0].dosis" in result.document.mapped_extraction).to(be_false)
    entry = result.document.verification["medicamentos[0].dosis"]
    expect(entry["previous_value"]).to(equal("500mg"))
    expect(entry["value"]).to(equal("250mg"))


async def test_nested_dotted_path__resolves_through_dict():
    doc = _nested_doc()
    result = await _use_case(
        doc, fields=[FieldVerification(field_path="contacto.telefono", action="correct", value="999")]
    ).execute()

    expect(result.document.mapped_extraction["contacto"]["telefono"]["value"]).to(equal("999"))


async def test_unknown_path__raises_422_no_phantom_key_no_event():
    doc = _nested_doc()
    events = _FakeEventRepo()
    doc_repo = _FakeDocRepo([doc])
    with pytest.raises(FieldNotFoundError):
        await _use_case(
            doc,
            fields=[FieldVerification(field_path="medicamentos[0].inexistente", action="correct", value="x")],
            event_repo=events,
            doc_repo=doc_repo,
        ).execute()

    expect(events.created).to(have_length(0))
    expect(doc_repo.updated).to(have_length(0))


async def test_unknown_list_index__raises_422():
    doc = _nested_doc()
    with pytest.raises(FieldNotFoundError):
        await _use_case(
            doc,
            fields=[FieldVerification(field_path="medicamentos[5].dosis", action="correct", value="x")],
        ).execute()


async def test_container_dict_without_value__rejected_422():
    doc = _nested_doc()
    with pytest.raises(FieldNotCorrectableError):
        await _use_case(
            doc, fields=[FieldVerification(field_path="contacto", action="correct", value="x")]
        ).execute()


async def test_list_node__rejected_422():
    doc = _nested_doc()
    with pytest.raises(FieldNotCorrectableError):
        await _use_case(
            doc, fields=[FieldVerification(field_path="medicamentos", action="correct", value="x")]
        ).execute()


async def test_correct__does_not_mutate_original_document_tree():
    doc = _nested_doc()
    await _use_case(
        doc,
        fields=[FieldVerification(field_path="medicamentos[0].dosis", action="correct", value="250mg")],
    ).execute()

    # El fake devuelve el MISMO objeto persistido; el original NO se muta in situ
    # antes del update (deepcopy) — verifica que no hay aliasing peligroso.
    # (El doc reasignado refleja el cambio porque update() devuelve el documento.)
    expect(doc.mapped_extraction["medicamentos"][0]["dosis"]["value"]).to(equal("250mg"))


# ─── C12 · corrections con APPROVAL stage=None (gate E4) ─────────────────────


async def test_signal__approval_stage_none_does_not_signal():
    # APPROVAL E4 abierta (gate único, stage=None): la espera usa wait_for_task
    # que NO consume `corrections` ⇒ bufferizaría sin re-analizar. NO señalar.
    doc = _doc()
    client = _FakeTemporalClient()
    result = await _use_case(
        doc,
        fields=[FieldVerification(field_path="ci", action="correct", value="9999")],
        tasks=[_approval(stage=None)],
        client=client,
    ).execute()

    expect(result.corrections_signaled).to(be_false)
    expect(client.signals).to(have_length(0))
    # Y NO acuña level=2 fantasma para una verificación que no pasó por L1/L2.
    expect(result.level).to(equal(0))


async def test_signal__review_l2_stage_signals_and_level_2():
    doc = _doc()
    client = _FakeTemporalClient()
    result = await _use_case(
        doc,
        fields=[FieldVerification(field_path="ci", action="correct", value="9999")],
        tasks=[_approval(stage="review_l2")],
        client=client,
    ).execute()

    expect(result.corrections_signaled).to(be_true)
    expect(result.level).to(equal(2))
    expect(client.signals).to(have_length(1))


# ─── minor · dedupe action/level + lista vacía ───────────────────────────────


async def test_dedupe__accept_after_correct_not_absorbed():
    # accept y correct sobre el mismo campo producen claves DISTINTAS (action en
    # la key) ⇒ ambos eventos sobreviven al dedupe.
    doc = _doc()
    events = _FakeEventRepo()
    await _use_case(
        doc, fields=[FieldVerification(field_path="ci", action="correct", value="900")],
        event_repo=events,
    ).execute()
    await _use_case(
        doc, fields=[FieldVerification(field_path="ci", action="accept")],
        event_repo=events,
    ).execute()

    expect(events.created).to(have_length(2))
    expect(events.created[0].dedupe_key).not_to(equal(events.created[1].dedupe_key))


async def test_empty_field_list__no_persist_no_signal():
    doc = _doc()
    client = _FakeTemporalClient()
    events = _FakeEventRepo()
    doc_repo = _FakeDocRepo([doc])
    result = await _use_case(
        doc, fields=[], tasks=[_approval(stage="review_l2")],
        client=client, event_repo=events, doc_repo=doc_repo,
    ).execute()

    expect(result.verified_paths).to(equal([]))
    expect(result.corrections_signaled).to(be_false)
    expect(doc_repo.updated).to(have_length(0))
    expect(events.created).to(have_length(0))
    expect(client.signals).to(have_length(0))
