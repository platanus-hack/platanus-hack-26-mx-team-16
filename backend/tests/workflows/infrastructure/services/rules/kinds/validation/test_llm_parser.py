"""Unit tests for `ValidationParser`.

The parser wraps an `LLMRunner`, post-validates the structured output and
rejects payloads that reference unknown sub_check ids, unknown methods or
inputs not present in the prompt. We exercise the happy path with a
`StaticLLMRunner`, the empty/garbage fallback, and each rejection branch.
"""

import pytest
from expects import contain, equal, expect

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    StaticLLMRunner,
)
from src.workflows.infrastructure.services.rules.kinds.validation.llm_parser import (
    ValidationParser,
)


def _payload(tree=None, sub_checks=None):
    return {
        "tree": tree or {"ref": "c1"},
        "sub_checks": sub_checks
        or [
            {
                "id": "c1",
                "description": "rut formato",
                "inputs": ["@{dni}.rut"],
                "method": "FORMAT_CHECK",
                "params": {"regex": r"\d+"},
            }
        ],
    }


def _parser(payload):
    return ValidationParser(llm_runner=StaticLLMRunner(payload=payload))


async def test_parse__returns_normalized_result_for_valid_payload():
    parser = _parser(_payload())

    result = await parser.parse(
        prompt="check @{dni}.rut",
        available_slugs=["dni"],
        kb_slugs=[],
        tokens=[],
    )

    expect(result.tree).to(equal({"ref": "c1"}))
    expect(len(result.sub_checks)).to(equal(1))
    expect(result.sub_checks[0]["method"]).to(equal("FORMAT_CHECK"))
    expect(result.sub_checks[0]["tokens"]).to(equal([]))
    expect(result.sub_checks[0]["knowledge_refs"]).to(equal([]))


async def test_parse__falls_back_when_llm_payload_is_empty():
    # Fallback emits a single LLM_CHECK whose params.question is the verbatim prompt;
    # use a prompt with no doc refs so the param-ref cross-check stays trivially satisfied.
    parser = _parser({})

    result = await parser.parse(
        prompt="verifica que el documento sea correcto",
        available_slugs=[],
        kb_slugs=[],
        tokens=[],
    )

    expect(result.sub_checks[0]["method"]).to(equal("LLM_CHECK"))
    expect(result.sub_checks[0]["params"]["question"]).to(contain("verifica que el documento"))


async def test_parse__rejects_duplicate_sub_check_ids():
    parser = _parser(
        _payload(
            tree={"op": "AND", "children": [{"ref": "c1"}, {"ref": "c1"}]},
            sub_checks=[
                {"id": "c1", "method": "FORMAT_CHECK", "inputs": ["@{dni}.rut"], "params": {"regex": "x"}},
                {"id": "c1", "method": "FORMAT_CHECK", "inputs": ["@{dni}.rut"], "params": {"regex": "y"}},
            ],
        )
    )

    with pytest.raises(InvalidWorkflowRuleConfigError) as info:
        await parser.parse(prompt="check @{dni}.rut", available_slugs=["dni"], kb_slugs=[], tokens=[])
    expect(str(info.value)).to(contain("duplicate"))


async def test_parse__rejects_unknown_method():
    parser = _parser(
        _payload(
            sub_checks=[
                {"id": "c1", "method": "UNKNOWN_METHOD", "inputs": ["@{dni}.rut"], "params": {}},
            ]
        )
    )

    with pytest.raises(InvalidWorkflowRuleConfigError) as info:
        await parser.parse(prompt="check @{dni}.rut", available_slugs=["dni"], kb_slugs=[], tokens=[])
    expect(str(info.value)).to(contain("UNKNOWN_METHOD"))


async def test_parse__rejects_input_not_present_in_prompt():
    parser = _parser(
        _payload(
            sub_checks=[
                {
                    "id": "c1",
                    "method": "FORMAT_CHECK",
                    "inputs": ["@{dni}.numero_telefonico"],
                    "params": {"regex": "x"},
                },
            ]
        )
    )

    with pytest.raises(InvalidWorkflowRuleConfigError) as info:
        await parser.parse(prompt="check @{dni}.rut", available_slugs=["dni"], kb_slugs=[], tokens=[])
    expect(str(info.value)).to(contain("not present in prompt"))


async def test_parse__rejects_input_with_unknown_slug():
    parser = _parser(
        _payload(
            sub_checks=[
                {"id": "c1", "method": "FORMAT_CHECK", "inputs": ["@{pasaporte}.numero"], "params": {"regex": "x"}},
            ]
        )
    )

    with pytest.raises(InvalidWorkflowRuleConfigError) as info:
        await parser.parse(
            prompt="check @{pasaporte}.numero",
            available_slugs=["dni"],
            kb_slugs=[],
            tokens=[],
        )
    expect(str(info.value)).to(contain("pasaporte"))


async def test_parse__rejects_tree_leaf_referencing_missing_sub_check():
    parser = _parser(
        _payload(
            tree={"ref": "missing"},
            sub_checks=[
                {"id": "c1", "method": "FORMAT_CHECK", "inputs": ["@{dni}.rut"], "params": {"regex": "x"}},
            ],
        )
    )

    with pytest.raises(InvalidWorkflowRuleConfigError) as info:
        await parser.parse(prompt="check @{dni}.rut", available_slugs=["dni"], kb_slugs=[], tokens=[])
    expect(str(info.value)).to(contain("missing"))


async def test_parse__rejects_NOT_node_with_more_than_one_child():
    parser = _parser(
        _payload(
            tree={"op": "NOT", "children": [{"ref": "c1"}, {"ref": "c1"}]},
            sub_checks=[
                {"id": "c1", "method": "FORMAT_CHECK", "inputs": ["@{dni}.rut"], "params": {"regex": "x"}},
            ],
        )
    )

    with pytest.raises(InvalidWorkflowRuleConfigError) as info:
        await parser.parse(prompt="check @{dni}.rut", available_slugs=["dni"], kb_slugs=[], tokens=[])
    expect(str(info.value)).to(contain("NOT"))


async def test_parse__rejects_param_ref_with_unknown_slug():
    """Param refs are allowed even if absent from `inputs`, but their slug must be known."""
    parser = _parser(
        _payload(
            sub_checks=[
                {
                    "id": "c1",
                    "method": "CROSS_REF_CHECK",
                    "inputs": ["@{dni}.rut"],
                    "params": {"against": "@{pasaporte}.numero", "mode": "equal"},
                },
            ]
        )
    )

    with pytest.raises(InvalidWorkflowRuleConfigError) as info:
        await parser.parse(
            prompt="check @{dni}.rut",
            available_slugs=["dni"],
            kb_slugs=[],
            tokens=[],
        )
    expect(str(info.value)).to(contain("pasaporte"))


async def test_parse__accepts_param_ref_not_declared_in_inputs_when_slug_is_known():
    """The PARSER frequently synthesises iterator refs from array fields. Compile must accept that."""
    parser = _parser(
        _payload(
            sub_checks=[
                {
                    "id": "c1",
                    "method": "AGGREGATE_CHECK",
                    "inputs": ["@{invoice}.items[].subtotal"],
                    "params": {
                        "iterator": "@{invoice}.items[]",
                        "predicate": "ALL",
                        "expression": "abs(subtotal - cantidad * precio_unitario) <= 1",
                    },
                },
            ]
        )
    )

    result = await parser.parse(
        prompt="check @{invoice}.items[].subtotal",
        available_slugs=["invoice"],
        kb_slugs=[],
        tokens=[],
    )

    expect(result.sub_checks[0]["params"]["iterator"]).to(equal("@{invoice}.items[]"))


async def test_parse__rejects_token_not_declared_in_prompt():
    parser = _parser(
        _payload(
            sub_checks=[
                {
                    "id": "c1",
                    "method": "FORMAT_CHECK",
                    "inputs": ["@{dni}.rut"],
                    "tokens": ["now"],
                    "params": {"regex": "x"},
                },
            ]
        )
    )

    with pytest.raises(InvalidWorkflowRuleConfigError) as info:
        await parser.parse(prompt="check @{dni}.rut", available_slugs=["dni"], kb_slugs=[], tokens=[])
    expect(str(info.value)).to(contain("now"))


async def test_parse__strips_null_params_so_optional_string_fields_dont_trip_schema():
    """The PARSER LLM often emits optional params (`criteria`, `topic`, …) as JSON
    null. Those are typed `{"type": "string"}` in the method schema, so without
    stripping they raise `None is not of type 'string'`. Normalization must drop
    them, leaving only the populated params."""
    parser = _parser(
        _payload(
            sub_checks=[
                {
                    "id": "c1",
                    "method": "LLM_CHECK",
                    "inputs": [],
                    "params": {"question": "¿es correcto?", "criteria": None, "topic": None},
                },
            ]
        )
    )

    result = await parser.parse(
        prompt="verifica que el documento sea correcto",
        available_slugs=[],
        kb_slugs=[],
        tokens=[],
    )

    params = result.sub_checks[0]["params"]
    expect(params).to(equal({"question": "¿es correcto?"}))


async def test_parse__rejects_payload_without_required_top_level_keys():
    parser = _parser({"tree": "not-a-dict", "sub_checks": []})

    with pytest.raises(InvalidWorkflowRuleConfigError):
        await parser.parse(prompt="check @{dni}.rut", available_slugs=["dni"], kb_slugs=[], tokens=[])
