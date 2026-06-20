"""E4 · payloads de los eventos case.needs_review / case.needs_clarification.

``build_case_event_payload`` mergea el payload rico de la fase (clarification
request §4.5 / contexto de aprobación) y ``_status_label`` produce labels NOT
NULL para ``WorkflowEvent.document_status`` (gotcha E2).
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from expects import equal, expect, have_keys

from src.common.domain.entities.workflows.analysis_run_processing import DispatchCaseEventInput
from src.common.domain.enums.webhooks import WebhookEventType
from src.workflows.infrastructure.services.webhooks.case_event_dispatcher import (
    _status_label,
    build_case_event_payload,
    select_destinations,
)

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_WORKFLOW = UUID("33333333-3333-3333-3333-333333333333")
_CASE = UUID("44444444-4444-4444-4444-444444444444")
_TASK = UUID("55555555-5555-5555-5555-555555555555")
_RUN = UUID("66666666-6666-6666-6666-666666666666")


def _input(event_type: str, payload: dict | None = None) -> DispatchCaseEventInput:
    return DispatchCaseEventInput(
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        case_id=_CASE,
        event_type=event_type,
        task_id=_TASK,
        payload=payload,
    )


def test_payload__needs_clarification_carries_full_request():
    request = {
        "caseId": str(_CASE),
        "taskId": str(_TASK),
        "items": [{"fieldPath": "total", "reason": "low_confidence"}],
        "resolveUrl": f"/v1/tasks/{_TASK}/resolve",
        "expiresAt": None,
    }

    envelope = build_case_event_payload(
        event_id="evt_1",
        data=_input(WebhookEventType.CASE_NEEDS_CLARIFICATION.value, request),
        summary=None,
    )

    expect(envelope["eventType"]).to(equal("case.needs_clarification"))
    expect(envelope["data"]).to(
        have_keys(
            caseId=str(_CASE),
            taskId=str(_TASK),
            items=[{"fieldPath": "total", "reason": "low_confidence"}],
            resolveUrl=f"/v1/tasks/{_TASK}/resolve",
        )
    )


def test_payload__needs_review_carries_verdict_summary_and_resolve_url():
    payload = {
        "caseId": str(_CASE),
        "taskId": str(_TASK),
        "verdict": "REVIEW",
        "summary": {"confidenceScore": 0.8},
        "resolveUrl": f"/v1/tasks/{_TASK}/resolve",
    }

    envelope = build_case_event_payload(
        event_id="evt_2",
        data=_input(WebhookEventType.CASE_NEEDS_REVIEW.value, payload),
        summary=None,
    )

    expect(envelope["data"]).to(have_keys(verdict="REVIEW", summary={"confidenceScore": 0.8}, taskId=str(_TASK)))


def test_payload__task_id_defaults_when_phase_payload_omits_it():
    envelope = build_case_event_payload(
        event_id="evt_3",
        data=_input(WebhookEventType.CASE_NEEDS_REVIEW.value, {"verdict": "PASS"}),
        summary=None,
    )

    expect(envelope["data"]["taskId"]).to(equal(str(_TASK)))


# ---------- phases-config · H3 · deliver.payload_projection ---------- #


def _summary(output):
    # build_case_event_payload lee summary.{output,verdict,confidence_score,
    # narrative_status,output_schema_snapshot}; verdict/narrative None evita enums.
    return SimpleNamespace(
        output=output,
        verdict=None,
        confidence_score=0.9,
        narrative_status=None,
        output_schema_snapshot=None,
    )


def _output_ready_input(payload_projection=None):
    return DispatchCaseEventInput(
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        case_id=_CASE,
        event_type=WebhookEventType.CASE_OUTPUT_READY.value,
        run_id=_RUN,
        payload_projection=payload_projection,
    )


def test_payload__output_ready_full_output_when_no_projection():
    # None ⇒ envelope completo (comportamiento de hoy, replay-safe).
    envelope = build_case_event_payload(
        event_id="evt_4",
        data=_output_ready_input(None),
        summary=_summary({"a": 1, "b": 2, "c": 3}),
    )

    expect(envelope["data"]["output"]).to(equal({"a": 1, "b": 2, "c": 3}))


def test_payload__output_ready_projection_trims_to_subset():
    envelope = build_case_event_payload(
        event_id="evt_5",
        data=_output_ready_input(["a", "c"]),
        summary=_summary({"a": 1, "b": 2, "c": 3}),
    )

    expect(envelope["data"]["output"]).to(equal({"a": 1, "c": 3}))


def test_payload__projection_with_unknown_keys_yields_empty_output():
    envelope = build_case_event_payload(
        event_id="evt_6",
        data=_output_ready_input(["zzz"]),
        summary=_summary({"a": 1}),
    )

    expect(envelope["data"]["output"]).to(equal({}))


# ---------- phases-config · H3 · deliver.channels allowlist ---------- #


def _dest(uuid_str, name):
    return SimpleNamespace(uuid=UUID(uuid_str), name=name)


_D1 = _dest("11111111-1111-1111-1111-111111111111", "slack-prod")
_D2 = _dest("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "email-ops")


def test_channels__none_returns_all_destinations():
    # None ⇒ todos los suscritos (comportamiento de hoy), misma lista.
    dests = [_D1, _D2]

    expect(select_destinations(dests, None)).to(equal(dests))


def test_channels__matches_by_uuid_string():
    result = select_destinations([_D1, _D2], [str(_D1.uuid)])

    expect(result).to(equal([_D1]))


def test_channels__matches_by_name():
    result = select_destinations([_D1, _D2], ["email-ops"])

    expect(result).to(equal([_D2]))


def test_channels__unknown_channel_yields_empty():
    expect(select_destinations([_D1, _D2], ["does-not-exist"])).to(equal([]))


def test_channels__empty_list_delivers_to_nobody():
    # Lista vacía es intencional y distinta de None: entrega a nadie.
    expect(select_destinations([_D1, _D2], [])).to(equal([]))


def test_channels__destination_without_name_does_not_crash():
    # Doble parcial sin .name: getattr evita AttributeError (prod siempre trae name).
    nameless = SimpleNamespace(uuid=UUID("99999999-9999-9999-9999-999999999999"))

    expect(select_destinations([nameless], [str(nameless.uuid)])).to(equal([nameless]))
    expect(select_destinations([nameless], ["whatever"])).to(equal([]))


def test_status_label__pause_events_use_not_null_labels():
    # WorkflowEvent.document_status es NOT NULL str — labels, no None.
    expect(_status_label(WebhookEventType.CASE_NEEDS_REVIEW, None)).to(equal("REVIEW"))
    expect(_status_label(WebhookEventType.CASE_NEEDS_CLARIFICATION, None)).to(equal("CLARIFICATION"))
    expect(_status_label(WebhookEventType.CASE_FAILED, None)).to(equal("FAILED"))
    expect(_status_label(WebhookEventType.CASE_CREATED, None)).to(equal("CREATED"))
    expect(_status_label(WebhookEventType.CASE_OUTPUT_READY, None)).to(equal("READY"))
