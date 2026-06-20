"""Unit tests for evaluate_sub_check across FORMAT/RANGE/CHECKSUM methods."""

from uuid import uuid4

import pytest
from expects import be_false, be_true, equal, expect

from src.workflows.domain.rules.kind_protocol import EvalDocumentInput
from src.workflows.infrastructure.services.rules.bootstrap import (
    register_default_checksums,
)
from src.workflows.infrastructure.services.rules.checksums import (
    registry as checksum_registry,
)
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    StaticLLMRunner,
)
from src.workflows.infrastructure.services.rules.kinds._shared.path_resolver import (
    resolve as resolve_doc_ref,
)
from src.workflows.infrastructure.services.rules.kinds._shared.refs import parse_doc_refs
from src.workflows.infrastructure.services.rules.kinds.validation.dispatcher import (
    evaluate_sub_check,
)


@pytest.fixture(autouse=True)
def _checksums():
    checksum_registry.clear()
    register_default_checksums()
    yield
    checksum_registry.clear()
    register_default_checksums()


@pytest.fixture
def cedula_doc():
    return EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug="cedula",
        extracted_fields={"rut": "12.345.678-5"},
    )


def _resolve_inputs(refs: list[str], docs: list[EvalDocumentInput]) -> dict[str, list]:
    out: dict[str, list] = {}
    for raw in refs:
        ref = parse_doc_refs(raw)[0]
        out[raw] = resolve_doc_ref(ref, docs)
    return out


async def test_evaluate_sub_check__format_check_passes(cedula_doc):
    sub_check = {
        "id": "c1",
        "method": "FORMAT_CHECK",
        "inputs": ["@{cedula}.rut"],
        "tokens": [],
        "params": {"regex": r"\d{1,2}\.\d{3}\.\d{3}-[\dkK]"},
    }

    result = await evaluate_sub_check(
        sub_check,
        resolved_inputs=_resolve_inputs(sub_check["inputs"], [cedula_doc]),
        resolved_tokens={},
        llm_runner=StaticLLMRunner(payload={}),
    )

    expect(result.passed).to(be_true)
    expect(len(result.citations)).to(equal(1))


async def test_evaluate_sub_check__format_check_fails_for_bad_value():
    bad_doc = EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug="cedula",
        extracted_fields={"rut": "not-a-rut"},
    )
    sub_check = {
        "id": "c1",
        "method": "FORMAT_CHECK",
        "inputs": ["@{cedula}.rut"],
        "tokens": [],
        "params": {"regex": r"\d{1,2}\.\d{3}\.\d{3}-[\dkK]"},
    }

    result = await evaluate_sub_check(
        sub_check,
        resolved_inputs=_resolve_inputs(sub_check["inputs"], [bad_doc]),
        resolved_tokens={},
        llm_runner=StaticLLMRunner(payload={}),
    )

    expect(result.passed).to(be_false)


async def test_evaluate_sub_check__range_check_within_bounds():
    invoice = EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug="invoice",
        extracted_fields={"total": 500},
    )
    sub_check = {
        "id": "c1",
        "method": "RANGE_CHECK",
        "inputs": ["@{invoice}.total"],
        "tokens": [],
        "params": {"min": 100, "max": 1000, "inclusive": True},
    }

    result = await evaluate_sub_check(
        sub_check,
        resolved_inputs=_resolve_inputs(sub_check["inputs"], [invoice]),
        resolved_tokens={},
        llm_runner=StaticLLMRunner(payload={}),
    )

    expect(result.passed).to(be_true)


async def test_evaluate_sub_check__range_check_below_min_fails():
    invoice = EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug="invoice",
        extracted_fields={"total": 50},
    )
    sub_check = {
        "id": "c1",
        "method": "RANGE_CHECK",
        "inputs": ["@{invoice}.total"],
        "tokens": [],
        "params": {"min": 100, "max": 1000, "inclusive": True},
    }

    result = await evaluate_sub_check(
        sub_check,
        resolved_inputs=_resolve_inputs(sub_check["inputs"], [invoice]),
        resolved_tokens={},
        llm_runner=StaticLLMRunner(payload={}),
    )

    expect(result.passed).to(be_false)


async def test_evaluate_sub_check__checksum_check_valid_rut(cedula_doc):
    sub_check = {
        "id": "c1",
        "method": "CHECKSUM_CHECK",
        "inputs": ["@{cedula}.rut"],
        "tokens": [],
        "params": {"algorithm": "rut_chile_mod11"},
    }

    result = await evaluate_sub_check(
        sub_check,
        resolved_inputs=_resolve_inputs(sub_check["inputs"], [cedula_doc]),
        resolved_tokens={},
        llm_runner=StaticLLMRunner(payload={}),
    )

    expect(result.passed).to(be_true)


async def test_evaluate_sub_check__checksum_check_invalid_rut():
    bad = EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug="cedula",
        extracted_fields={"rut": "12.345.678-9"},
    )
    sub_check = {
        "id": "c1",
        "method": "CHECKSUM_CHECK",
        "inputs": ["@{cedula}.rut"],
        "tokens": [],
        "params": {"algorithm": "rut_chile_mod11"},
    }

    result = await evaluate_sub_check(
        sub_check,
        resolved_inputs=_resolve_inputs(sub_check["inputs"], [bad]),
        resolved_tokens={},
        llm_runner=StaticLLMRunner(payload={}),
    )

    expect(result.passed).to(be_false)


# ---------------- handler crash → ERRORED, never silent FAIL (C-minor) ---------------- #


async def test_evaluate_sub_check__handler_crash_raises_config_error(cedula_doc):
    # A crashing handler used to return passed=False (silent FAIL → flips to a
    # bogus PASS under NOT). It must raise so the rule result becomes ERRORED.
    from src.common.domain.exceptions.workflow_rules import (
        InvalidWorkflowRuleConfigError,
    )

    sub_check = {
        "id": "c1",
        "method": "FORMAT_CHECK",
        "inputs": ["@{cedula}.rut"],
        "tokens": [],
        "params": {"regex": "("},  # invalid regex → re.error inside the handler
    }
    resolved = _resolve_inputs(sub_check["inputs"], [cedula_doc])

    with pytest.raises(InvalidWorkflowRuleConfigError):
        await evaluate_sub_check(
            sub_check,
            resolved_inputs=resolved,
            resolved_tokens={},
            llm_runner=StaticLLMRunner(payload={}),
        )
