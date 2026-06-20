"""Golden tests for `DerivationKind.compile()` against the D1–D10 fixtures.

Each fixture in `tests/fixtures/workflow_rules/derivation/d{N}.json` declares
the rule prompt, the user's `output_shape`, the available doctypes (and
optional KB slugs) and the expectations on the produced artifact.

The test parses refs/tokens/kb_refs from the prompt and asserts the
derivation compiler emits the same `inputs/tokens/knowledge_refs` plus
`output_shape_validated=True` — the wrapper fields (`version`, `prompt`,
`compiled_with`) are checked separately so a future bump doesn't ripple
through every fixture.
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
from src.workflows.infrastructure.services.rules.kinds.derivation import DerivationKind


FIXTURE_DIR = Path(__file__).resolve().parents[5] / "fixtures" / "workflow_rules" / "derivation"


@dataclass
class _StubKBResolver:
    """KBDocumentResolver-shaped stub returning a fixed UUID per slug."""

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


def _doctypes(slugs: list[str], workflow_id, tenant_id) -> list[DocumentType]:
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


def _build_rule(prompt: str, config: dict, *, tenant_id, workflow_id) -> WorkflowRule:
    return WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="d-fixture",
        kind="DERIVATION",
        prompt=prompt,
        config=config,
    )


def _load_fixture(stem: str) -> dict:
    return json.loads((FIXTURE_DIR / f"{stem}.json").read_text())


D_FIXTURES = sorted(p.stem for p in FIXTURE_DIR.glob("d*.json"))


@pytest.mark.parametrize("fixture_name", D_FIXTURES)
async def test_derivation_compile__matches_golden(fixture_name):
    fixture = _load_fixture(fixture_name)
    tenant_id = uuid4()
    workflow_id = uuid4()
    rule = _build_rule(
        fixture["rule"]["prompt"],
        fixture["rule"]["config"],
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )

    kb_slugs = fixture.get("kb_slugs") or []
    kb_resolver = _StubKBResolver({slug: str(uuid4()) for slug in kb_slugs}) if kb_slugs else None
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=_doctypes(fixture["available_doctypes"], workflow_id, tenant_id),
        kb_resolver=kb_resolver,
    )

    outcome = await DerivationKind().compile(rule, ctx)

    expected = fixture["expected_artifact"]
    artifact = outcome.artifact

    expect(artifact["inputs"]).to(equal(expected["inputs"]))
    expect(artifact["tokens"]).to(equal(expected["tokens"]))
    expect(artifact["output_shape_validated"]).to(equal(expected["output_shape_validated"]))

    if "knowledge_refs_count" in expected:
        expect(len(artifact["knowledge_refs"])).to(equal(expected["knowledge_refs_count"]))
    else:
        expect(artifact["knowledge_refs"]).to(equal(expected["knowledge_refs"]))

    expect(artifact["version"]).to(equal(1))
    expect(artifact["prompt"]).to(equal(rule.prompt))
    expect(outcome.compiled_with["kind"]).to(equal("DERIVATION"))
    expect(outcome.compiled_with["compiler"]).to(equal("derivation.compile"))


async def test_derivation_compile__rejects_unknown_doctype():
    tenant_id, workflow_id = uuid4(), uuid4()
    rule = _build_rule(
        "Extraer @{pasaporte}.numero del titular.",
        {"output_shape": {"type": "object", "properties": {}, "additionalProperties": True}},
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=_doctypes(["dni"], workflow_id, tenant_id),
    )

    with pytest.raises(InvalidWorkflowRuleConfigError) as info:
        await DerivationKind().compile(rule, ctx)
    expect("pasaporte" in str(info.value)).to(equal(True))


async def test_derivation_compile__rejects_unknown_token():
    tenant_id, workflow_id = uuid4(), uuid4()
    rule = _build_rule(
        "Saludar a {{user.preferences.locale}}.",
        {"output_shape": {"type": "object", "properties": {}, "additionalProperties": True}},
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )
    ctx = CompileContext(workflow_id=workflow_id, tenant_id=tenant_id, document_types=[])

    with pytest.raises(InvalidWorkflowRuleConfigError) as info:
        await DerivationKind().compile(rule, ctx)
    expect("user.preferences.locale" in str(info.value)).to(equal(True))


async def test_derivation_compile__rejects_invalid_output_shape():
    tenant_id, workflow_id = uuid4(), uuid4()
    rule = _build_rule(
        "Extraer datos.",
        {"output_shape": "not-a-schema"},
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )
    ctx = CompileContext(workflow_id=workflow_id, tenant_id=tenant_id, document_types=[])

    with pytest.raises(InvalidWorkflowRuleConfigError):
        await DerivationKind().compile(rule, ctx)
