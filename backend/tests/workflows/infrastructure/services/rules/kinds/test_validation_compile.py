"""Golden tests for `ValidationKind.compile()` against V1–V13 fixtures.

Each fixture lives at `tests/fixtures/workflow_rules/validation/v{N}/` and
contains:

- `rule.json` — `{rule, available_doctypes, kb_slugs}`
- `parser_response.json` — the deterministic payload returned by a stub
  `LLMRunner` so the parser is exercised end-to-end without a real model.
- `expected_artifact.json` — structural expectations (tree shape, sub_check
  count + methods, inputs per sub_check, knowledge_refs count).

Assertions are structural, not literal — sub_check descriptions and params
values are LLM-authored and excluded from the diff.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.common.domain.models.knowledge_base.kb_document import KBDocument
from src.common.domain.models.processing.document_type import DocumentType
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.domain.rules.kind_protocol import CompileContext
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    StaticLLMRunner,
)
from src.workflows.infrastructure.services.rules.kinds.validation.kind import (
    ValidationKind,
)
from src.workflows.infrastructure.services.rules.kinds.validation.llm_parser import (
    ValidationParser,
)


FIXTURE_DIR = Path(__file__).resolve().parents[5] / "fixtures" / "workflow_rules" / "validation"


@dataclass
class _StubKBResolver:
    slug_to_uuid: dict[str, str]

    async def resolve(self, tenant_id, workflow_id, slugs):  # noqa: ARG002
        return {
            slug: KBDocument(
                uuid=self.slug_to_uuid[slug],
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                slug=slug,
                file_name=f"{slug}.txt",
                mime="text/plain",
            )
            for slug in slugs
            if slug in self.slug_to_uuid
        }


def _doctypes(slugs, workflow_id, tenant_id):
    return [
        DocumentType(
            uuid=uuid4(),
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            name=slug.title(),
            slug=slug,
        )
        for slug in slugs
    ]


def _build_kind(parser_payload):
    parser = ValidationParser(llm_runner=StaticLLMRunner(payload=parser_payload))
    return ValidationKind(parser=parser)


def _load(stem: str):
    fdir = FIXTURE_DIR / stem
    return (
        json.loads((fdir / "rule.json").read_text()),
        json.loads((fdir / "parser_response.json").read_text()),
        json.loads((fdir / "expected_artifact.json").read_text()),
    )


V_FIXTURES = sorted(
    (p.name for p in FIXTURE_DIR.glob("v*") if p.is_dir()),
    key=lambda s: int(s[1:]),
)


def _tree_op(tree):
    return tree.get("op")


def _tree_children_count(tree):
    return len(tree.get("children") or [])


@pytest.mark.parametrize("fixture_name", V_FIXTURES)
async def test_validation_compile__matches_golden(fixture_name):
    rule_data, parser_payload, expected = _load(fixture_name)
    tenant_id, workflow_id = uuid4(), uuid4()

    rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name=rule_data["name"],
        kind="VALIDATION",
        prompt=rule_data["rule"]["prompt"],
        config=rule_data["rule"]["config"],
    )

    kb_slugs = rule_data.get("kb_slugs") or []
    kb_resolver = _StubKBResolver({slug: str(uuid4()) for slug in kb_slugs}) if kb_slugs else None

    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=_doctypes(rule_data["available_doctypes"], workflow_id, tenant_id),
        kb_resolver=kb_resolver,
    )

    outcome = await _build_kind(parser_payload).compile(rule, ctx)
    artifact = outcome.artifact

    expect(_tree_op(artifact["tree"])).to(equal(expected["tree_op"]))
    expect(_tree_children_count(artifact["tree"])).to(equal(expected["tree_children_count"]))

    sub_checks = artifact["sub_checks"]
    expect(len(sub_checks)).to(equal(expected["sub_check_count"]))
    actual_methods = [sc["method"] for sc in sub_checks]
    expect(actual_methods).to(equal(expected["methods"]))

    by_id = {sc["id"]: sc for sc in sub_checks}
    expected_inputs = expected["sub_check_inputs_by_id"]
    expect(set(by_id.keys())).to(equal(set(expected_inputs.keys())))
    for sc_id, ins in expected_inputs.items():
        expect(set(by_id[sc_id]["inputs"])).to(equal(set(ins)))

    expect(len(artifact["knowledge_refs"])).to(equal(expected["knowledge_refs_count"]))

    expect(artifact["version"]).to(equal(1))
    expect(artifact["prompt"]).to(equal(rule.prompt))
    expect(outcome.compiled_with["kind"]).to(equal("VALIDATION"))
    expect(outcome.compiled_with["compiler"]).to(equal("validation.compile"))
    expect(sorted(artifact["available_slugs"])).to(equal(sorted(rule_data["available_doctypes"])))


async def test_validation_compile__rejects_unknown_kb_slug_when_kb_resolver_missing():
    tenant_id, workflow_id = uuid4(), uuid4()
    rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="kb-rule",
        kind="VALIDATION",
        prompt="comuna debe estar en #{comunas_region_metropolitana}.",
        config={"severity": "MAJOR"},
    )
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=[],
        kb_resolver=None,
    )

    with pytest.raises(InvalidWorkflowRuleConfigError) as info:
        await ValidationKind().compile(rule, ctx)
    expect("kb_resolver" in str(info.value)).to(equal(True))
