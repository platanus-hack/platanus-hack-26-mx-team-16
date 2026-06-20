"""E4 · D5: validación pydantic de CompletenessPolicy / ActivationPolicy."""

from __future__ import annotations

import pytest
from expects import be_false, be_none, equal, expect, have_length
from pydantic import ValidationError

from src.workflows.domain.models.policies import (
    ActivationPolicy,
    CompletenessPolicy,
)


def test_completeness_policy__defaults():
    policy = CompletenessPolicy()

    expect(policy.required_types).to(equal({}))
    expect(policy.auto_ready).to(be_false)


def test_completeness_policy__rejects_zero_counts():
    with pytest.raises(ValidationError):
        CompletenessPolicy(required_types={"anexo": 0})


def test_completeness_policy__rejects_unknown_keys():
    with pytest.raises(ValidationError):
        CompletenessPolicy(required_typo={"anexo": 1})


def test_activation_policy__defaults_match_design():
    policy = ActivationPolicy()

    expect(policy.field_thresholds).to(equal({}))
    expect(policy.on_low_confidence).to(equal("clarify"))
    expect(policy.blocking_rule_severities).to(equal(["BLOCKER"]))
    expect(policy.sample_rate).to(equal(0.0))
    # E6 · §3: auditoría QA post-aprobación apagada por defecto.
    expect(policy.qa_sample_rate).to(equal(0.0))
    expect(policy.mode).to(equal("mandatory"))
    # E5 compat: sin stages ⇒ gate único E4 intacto.
    expect(policy.stages).to(be_none)


# ─── E5 §3.1: stages de revisión multinivel ──────────────────────────────────


def test_activation_policy__stages_valid_sequence_parses():
    policy = ActivationPolicy(
        stages=[
            {"stage": "review_l1", "mode": "by_exception"},
            {"stage": "review_l2", "mode": "mandatory"},
        ]
    )

    expect([s.stage for s in policy.stages]).to(equal(["review_l1", "review_l2"]))
    expect([s.mode for s in policy.stages]).to(equal(["by_exception", "mandatory"]))


def test_activation_policy__single_stage_is_legal():
    policy = ActivationPolicy(stages=[{"stage": "review_l2", "mode": "mandatory"}])

    expect(policy.stages).to(have_length(1))


def test_activation_policy__stages_reject_duplicates():
    with pytest.raises(ValidationError):
        ActivationPolicy(
            stages=[
                {"stage": "review_l1", "mode": "mandatory"},
                {"stage": "review_l1", "mode": "by_exception"},
            ]
        )


def test_activation_policy__stages_reject_l2_before_l1():
    with pytest.raises(ValidationError):
        ActivationPolicy(
            stages=[
                {"stage": "review_l2", "mode": "mandatory"},
                {"stage": "review_l1", "mode": "mandatory"},
            ]
        )


def test_activation_policy__stages_reject_empty_list():
    with pytest.raises(ValidationError):
        ActivationPolicy(stages=[])


def test_activation_policy__stages_reject_unknown_stage_or_mode():
    with pytest.raises(ValidationError):
        ActivationPolicy(stages=[{"stage": "review_l3", "mode": "mandatory"}])
    with pytest.raises(ValidationError):
        ActivationPolicy(stages=[{"stage": "review_l1", "mode": "sometimes"}])


@pytest.mark.parametrize("threshold", [-0.1, 1.1, 2.0])
def test_activation_policy__rejects_thresholds_outside_unit_interval(threshold):
    with pytest.raises(ValidationError):
        ActivationPolicy(field_thresholds={"default": threshold})


@pytest.mark.parametrize("sample_rate", [-0.01, 1.01])
def test_activation_policy__rejects_sample_rate_outside_unit_interval(sample_rate):
    with pytest.raises(ValidationError):
        ActivationPolicy(sample_rate=sample_rate)


# ─── E6 §3: qa_sample_rate (auditoría QA post-aprobación) ─────────────────────


@pytest.mark.parametrize("qa_sample_rate", [0.0, 0.25, 1.0])
def test_activation_policy__accepts_qa_sample_rate_in_unit_interval(qa_sample_rate):
    policy = ActivationPolicy(qa_sample_rate=qa_sample_rate)

    expect(policy.qa_sample_rate).to(equal(qa_sample_rate))


@pytest.mark.parametrize("qa_sample_rate", [-0.01, 1.01, 2.0])
def test_activation_policy__rejects_qa_sample_rate_outside_unit_interval(qa_sample_rate):
    with pytest.raises(ValidationError):
        ActivationPolicy(qa_sample_rate=qa_sample_rate)


def test_activation_policy__rejects_unknown_mode():
    with pytest.raises(ValidationError):
        ActivationPolicy(mode="sometimes")


def test_activation_policy__rejects_unknown_on_low_confidence():
    with pytest.raises(ValidationError):
        ActivationPolicy(on_low_confidence="ignore")


# D-A: la validación version-level de la ActivationPolicy (validate_policies /
# normalize_policies) se eliminó — la activación va plegada en
# ``extraction_gate.config.activation`` y la valida ``validate_phase_configs`` al
# publicar (cubierto por ``test_phase_configs`` / ``test_pipeline_admin_endpoints``).
# Aquí queda solo la validación del MODELO ``ActivationPolicy`` (arriba).
