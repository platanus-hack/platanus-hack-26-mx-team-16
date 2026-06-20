"""Config tipada por kind de fase (propuesta phases-config · F0).

Los modelos ``PhaseConfig`` son la única fuente de verdad del schema de config:
validan al publicar/importar (validate-on-write) y los parsean los handlers
(validate-on-read). Estos tests fijan: defaults == comportamiento de hoy, el
contrato ``extra=forbid``, la coerción de enums y el error de validación.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from expects import be, be_false, be_none, be_true, contain, equal, expect, raise_error

from src.common.domain.enums.human_tasks import HumanTaskAssigneeMode
from src.common.domain.enums.pipelines import PhaseKind
from src.common.domain.enums.processing import DocumentExtractorType
from src.workflows.domain.models.phase_configs import (
    PHASE_CONFIG_MODELS,
    ClassifyPagesConfig,
    EnrichConfig,
    ExtractTextConfig,
    FinalizeConfig,
    HumanReviewConfig,
    InvalidPhaseConfigError,
    AssessConfig,
    DeliverConfig,
    FieldEmitConfig,
    completeness_dict_from_version,
    config_model_for,
    parse_duration,
    parse_phase_config,
    project_emit_fields,
    validate_phase_configs,
)
from src.workflows.domain.models.pipeline import PhaseSpec, PipelineVersion
from src.workflows.domain.services.field_confidence import DEFAULT_CONFIDENCE_THRESHOLD
from src.workflows.domain.services.pipeline_validation import DEFAULT_FAN_OUT_MAX_CHILDREN


def _phase(kind: str, config: dict | None = None) -> PhaseSpec:
    return PhaseSpec(id=kind, kind=PhaseKind(kind), config=config or {})


# ── registry completeness ────────────────────────────────────────────────────


def test_registry__covers_every_phase_kind():
    missing = {kind.value for kind in PhaseKind} - set(PHASE_CONFIG_MODELS)

    expect(missing).to(equal(set()))


def test_config_model_for__unknown_kind_is_none():
    expect(config_model_for("not_a_kind")).to(be_none)


# ── defaults == comportamiento de hoy ────────────────────────────────────────


def test_extract_text__default_extractor_is_textract_layout():
    cfg = ExtractTextConfig.model_validate({})

    expect(cfg.extractor).to(be(DocumentExtractorType.TEXTRACT_LAYOUT))
    expect(cfg.extractor.value).to(equal("textract_layout"))
    expect(cfg.timeout_seconds).to(be_none)


def test_finalize__default_dispatch_webhook_true():
    expect(FinalizeConfig.model_validate({}).dispatch_webhook).to(be_true)


def test_finalize__dispatch_webhook_false_preserved():
    expect(FinalizeConfig.model_validate({"dispatch_webhook": False}).dispatch_webhook).to(be_false)


def test_classify_pages__default_fan_out_max_children():
    cfg = ClassifyPagesConfig.model_validate({})

    expect(cfg.fan_out_max_children).to(equal(DEFAULT_FAN_OUT_MAX_CHILDREN))
    expect(cfg.fan_out).to(be_none)
    expect(cfg.fan_out_types).to(be_none)


def test_enrich__default_on_failure_is_review():
    cfg = EnrichConfig.model_validate({})

    expect(cfg.on_failure).to(equal("review"))
    expect(cfg.persist_degraded).to(be_false)
    expect(cfg.args).to(equal({}))


# ── coerción de enums (string sellado ↔ enum) ────────────────────────────────


def test_extract_text__coerces_extractor_string_to_enum():
    cfg = ExtractTextConfig.model_validate({"extractor": "vlm"})

    expect(cfg.extractor).to(be(DocumentExtractorType.VLM))
    expect(cfg.extractor.value).to(equal("vlm"))


def test_human_review__coerces_assignee_mode_string_to_enum():
    cfg = HumanReviewConfig.model_validate({"assignee_mode": "internal_queue"})

    expect(cfg.assignee_mode).to(be(HumanTaskAssigneeMode.INTERNAL_QUEUE))


# ── extra=forbid + tipos inválidos ───────────────────────────────────────────


def test_extract_text__rejects_unknown_key():
    expect(lambda: ExtractTextConfig.model_validate({"bogus": 1})).to(raise_error(Exception))


def test_extract_text__rejects_invalid_extractor():
    expect(lambda: ExtractTextConfig.model_validate({"extractor": "nope"})).to(raise_error(Exception))


@pytest.mark.parametrize("kind", ["review", "approval"])
def test_human_review__accepts_valid_kind(kind):
    expect(HumanReviewConfig.model_validate({"kind": kind}).kind).to(equal(kind))


def test_human_review__rejects_invalid_kind():
    expect(lambda: HumanReviewConfig.model_validate({"kind": "weird"})).to(raise_error(Exception))


def test_human_review__quorum_defaults_match_single_gate():
    cfg = HumanReviewConfig.model_validate({"kind": "approval"})

    expect(cfg.approvals_required).to(equal(1))
    expect(cfg.distinct_approvers).to(be_true)


def test_human_review__accepts_quorum_for_approval():
    cfg = HumanReviewConfig.model_validate(
        {"kind": "approval", "approvals_required": 2, "approvers": {"users": ["u1", "u2", "u3"]}}
    )

    expect(cfg.approvals_required).to(equal(2))
    expect(cfg.approvers.users).to(equal(["u1", "u2", "u3"]))


def test_human_review__quorum_on_review_kind_is_422():
    expect(lambda: HumanReviewConfig.model_validate({"kind": "review", "approvals_required": 2})).to(
        raise_error(Exception)
    )


# ── validate_phase_configs (validate-on-write) ───────────────────────────────


def test_validate_phase_configs__accepts_valid_recipe():
    phases = [
        _phase("ingest"),
        _phase("extract_text", {"extractor": "textract_layout"}),
        _phase("finalize", {"dispatch_webhook": False}),
    ]

    expect(lambda: validate_phase_configs(phases)).not_to(raise_error(Exception))


def test_validate_phase_configs__rejects_unknown_key_with_phase_context():
    phases = [_phase("extract_text", {"timeout_seconds": 90}), _phase("finalize", {"nope": True})]

    with pytest.raises(InvalidPhaseConfigError) as exc_info:
        validate_phase_configs(phases)

    expect(exc_info.value.phase_id).to(equal("finalize"))
    expect(exc_info.value.kind).to(equal("finalize"))
    expect(str(exc_info.value)).to(contain("finalize"))


# ── parse_phase_config (validate-on-read) ────────────────────────────────────


def test_parse_phase_config__returns_typed_model():
    cfg = parse_phase_config(_phase("classify_pages", {"fan_out": "child_cases"}))

    expect(cfg).to(be_a(ClassifyPagesConfig))
    expect(cfg.fan_out).to(equal("child_cases"))


# ── F1: per_type_overrides + completeness fold (D-A) ─────────────────────────


def test_extract_text__per_type_overrides_coerces_to_enum():
    cfg = ExtractTextConfig.model_validate({"per_type_overrides": {"receta": "vlm"}})

    expect(cfg.per_type_overrides["receta"]).to(be(DocumentExtractorType.VLM))


def _version(phases: list[PhaseSpec]) -> PipelineVersion:
    return PipelineVersion(
        uuid=uuid4(),
        pipeline_id=uuid4(),
        version=1,
        phases=phases,
    )


def test_completeness_dict__from_await_documents_phase_config():
    version = _version(
        [_phase("await_documents", {"required_types": {"oficio": 2}, "advance": "auto"})],
    )

    result = completeness_dict_from_version(version)

    expect(result).to(equal({"required_types": {"oficio": 2}, "auto_ready": True}))


def test_completeness_dict__none_when_phase_config_empty():
    # D-A: ya no hay fallback version-level — await_documents sin config ⇒ None.
    version = _version([_phase("await_documents", {})])

    expect(completeness_dict_from_version(version)).to(be_none)


def test_completeness_dict__none_when_no_await_documents_phase():
    version = _version([_phase("ingest", {})])

    expect(completeness_dict_from_version(version)).to(be_none)


# ── F1b: duration knobs (ISO-8601) + defaults == hoy ────────────────────────


def test_assess_config__defaults_match_today():
    cfg = AssessConfig.model_validate({})

    expect(cfg.timeout).to(equal("PT90S"))
    expect(cfg.max_attempts).to(equal(2))
    expect(cfg.provider).to(be_none)


def test_deliver_config__timeout_defaults_match_today():
    cfg = DeliverConfig.model_validate({})

    expect(cfg.dispatch_timeout).to(equal("PT60S"))
    expect(cfg.qa_audit_timeout).to(equal("PT30S"))


def test_duration_field__rejects_non_iso_string():
    expect(lambda: AssessConfig.model_validate({"timeout": "90 seconds"})).to(raise_error(Exception))


def test_parse_duration__iso_to_timedelta():
    expect(parse_duration("PT90S", timedelta(minutes=5))).to(equal(timedelta(seconds=90)))


def test_parse_duration__none_uses_default():
    expect(parse_duration(None, timedelta(minutes=5))).to(equal(timedelta(minutes=5)))


def test_parse_duration__none_default_is_none():
    expect(parse_duration(None)).to(be_none)


# ── F2: field projection to events (emit) + webhook_projection 422 ──────────


def test_project_emit_fields__default_emit_is_none():
    # fields="all" + sin metadatos ⇒ None ⇒ payload del evento byte-idéntico.
    result = project_emit_fields({"num": {"value": "X", "bbox": [1, 2]}}, {"num": 0.9}, FieldEmitConfig())

    expect(result).to(be_none)


def test_project_emit_fields__includes_bbox_and_confidence_when_enabled():
    mapped = {"num": {"value": "AB-12", "bbox": [1, 2, 3, 4]}}
    emit = FieldEmitConfig(include_bounding_boxes=True, include_ocr_confidence=True)

    result = project_emit_fields(mapped, {"num": 0.91}, emit)

    expect(result).to(equal({"num": {"value": "AB-12", "bbox": [1, 2, 3, 4], "confidence": 0.91}}))


def test_project_emit_fields__subset_filters_fields():
    mapped = {"a": {"value": 1}, "b": {"value": 2}}
    emit = FieldEmitConfig(fields=["a"])

    result = project_emit_fields(mapped, None, emit)

    expect(result).to(equal({"a": {"value": 1}}))


def test_webhook_projection__subset_of_emit_is_ok():
    phases = [
        _phase("extract_fields", {"emit": {"fields": ["num", "fecha"]}}),
        _phase("finalize", {"webhook_projection": ["num"]}),
    ]

    expect(lambda: validate_phase_configs(phases)).not_to(raise_error(Exception))


def test_webhook_projection__field_not_emitted_is_422():
    phases = [
        _phase("extract_fields", {"emit": {"fields": ["num"]}}),
        _phase("finalize", {"webhook_projection": ["num", "ghost"]}),
    ]

    with pytest.raises(InvalidPhaseConfigError) as exc_info:
        validate_phase_configs(phases)

    expect(str(exc_info.value)).to(contain("ghost"))


def be_a(cls):  # tiny matcher helper (expects has no built-in is-instance)
    from expects.matchers import Matcher

    class _BeA(Matcher):
        def _match(self, subject):
            return isinstance(subject, cls), [f"is a {cls.__name__}"]

    return _BeA()
