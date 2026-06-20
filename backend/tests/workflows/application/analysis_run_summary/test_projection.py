"""E2 · spec case-output §4.1: deterministic x-source projection."""

from uuid import UUID, uuid4

from expects import be_none, contain, equal, expect, have_key, have_len

from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.application.analysis_run_summary.projection import (
    ProjectionContext,
    apply_resolved,
    project_schema,
)
from src.workflows.domain.rules.kind_protocol import EvalDocumentInput


def _doc(slug: str = "invoice", fields: dict | None = None) -> EvalDocumentInput:
    return EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug=slug,
        extracted_fields=fields or {},
    )


def _rule_result(output: dict | None, document_refs: dict | None = None) -> WorkflowRuleResult:
    return WorkflowRuleResult(
        tenant_id=uuid4(),
        workflow_analysis_run_id=uuid4(),
        rule_id=uuid4(),
        case_id=uuid4(),
        kind="VALIDATION",
        output=output,
        document_refs=document_refs or {},
        document_refs_hash="h",
    )


def _schema(properties: dict) -> dict:
    return {"type": "object", "properties": properties}


# ── system tokens ────────────────────────────────────────────────────────────


def test_project_schema__system_token_resolves_without_citation():
    schema = _schema({"decision": {"type": "string", "x-source": "{{verdict}}"}})
    context = ProjectionContext(system_tokens={"verdict": "PASS"})

    result = project_schema(schema, context)

    expect(result.resolved).to(equal({"/decision": "PASS"}))
    expect(result.citations).to(equal({}))
    expect(result.warnings).to(have_len(0))
    expect(result.llm_pointers).to(have_len(0))


def test_project_schema__unknown_token_resolves_null_with_warning():
    schema = _schema({"decision": {"type": "string", "x-source": "{{nope}}"}})

    result = project_schema(schema, ProjectionContext(system_tokens={"verdict": "PASS"}))

    expect(result.resolved["/decision"]).to(be_none)
    expect(result.warnings).to(have_len(1))


# ── @slug.path (document refs) ───────────────────────────────────────────────


def test_project_schema__doc_scalar_resolves_value_and_citation():
    doc = _doc(fields={"total": 150})
    schema = _schema({"total": {"type": "number", "x-source": "@invoice.total"}})

    result = project_schema(schema, ProjectionContext(documents=[doc]))

    expect(result.resolved).to(equal({"/total": 150}))
    citation = result.citations["/total"][0]
    expect(citation.document_id).to(equal(doc.document_id))
    expect(citation.document_type_slug).to(equal("invoice"))
    expect(citation.field_path).to(equal("total"))


def test_project_schema__doc_array_path_resolves_list_with_citations():
    doc = _doc(fields={"items": [{"amount": 1}, {"amount": 2}]})
    schema = _schema({"amounts": {"type": "array", "x-source": "@invoice.items[].amount"}})

    result = project_schema(schema, ProjectionContext(documents=[doc]))

    expect(result.resolved).to(equal({"/amounts": [1, 2]}))
    expect(result.citations["/amounts"]).to(have_len(2))
    expect(result.citations["/amounts"][1].field_path).to(equal("items[1].amount"))


def test_project_schema__missing_document_type_resolves_null_with_warning():
    schema = _schema({"total": {"type": "number", "x-source": "@receipt.total"}})

    result = project_schema(schema, ProjectionContext(documents=[_doc(slug="invoice")]))

    expect(result.resolved["/total"]).to(be_none)
    expect(result.warnings).to(have_len(1))
    expect(result.llm_pointers).to(have_len(0))


def test_project_schema__missing_field_resolves_null_with_warning():
    schema = _schema({"total": {"type": "number", "x-source": "@invoice.subtotal"}})

    result = project_schema(schema, ProjectionContext(documents=[_doc(fields={"total": 1})]))

    expect(result.resolved["/total"]).to(be_none)
    expect(result.warnings).to(have_len(1))


# ── nested pointers ──────────────────────────────────────────────────────────


def test_project_schema__nested_objects_produce_nested_pointers():
    schema = _schema(
        {
            "totals": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "x-source": "@invoice.total"},
                    "note": {"type": "string"},
                },
            }
        }
    )

    result = project_schema(schema, ProjectionContext(documents=[_doc(fields={"total": 7})]))

    expect(result.resolved).to(equal({"/totals/amount": 7}))
    expect(result.llm_pointers).to(equal(["/totals/note"]))


# ── @rule.<slug> refs ────────────────────────────────────────────────────────


def test_project_schema__rule_ref_resolves_output_path_with_rule_citation():
    doc_id = uuid4()
    rule_result = _rule_result({"passed": True}, document_refs={"invoice": [str(doc_id)]})
    schema = _schema({"approved": {"type": "boolean", "x-source": "@rule.credit_check.passed"}})
    context = ProjectionContext(rule_results_by_slug={"credit_check": [rule_result]})

    result = project_schema(schema, context)

    expect(result.resolved).to(equal({"/approved": True}))
    citation = result.citations["/approved"][0]
    expect(citation.document_type_slug).to(equal("rule"))
    expect(citation.document_id).to(equal(doc_id))
    expect(citation.field_path).to(equal("passed"))
    expect(citation.sub_check_id).to(equal(str(rule_result.uuid)))


def test_project_schema__rule_ref_without_path_resolves_whole_output():
    rule_result = _rule_result({"passed": True, "score": 9}, document_refs={"cv": [str(uuid4())]})
    schema = _schema({"check": {"type": "object", "x-source": "@rule.credit_check"}})

    result = project_schema(
        schema, ProjectionContext(rule_results_by_slug={"credit_check": [rule_result]})
    )

    expect(result.resolved).to(equal({"/check": {"passed": True, "score": 9}}))


def test_project_schema__rule_without_output_resolves_null_with_warning():
    # Decision (spec §6): SKIPPED/FAILED rule → null, never delegated to the LLM.
    schema = _schema({"approved": {"type": "boolean", "x-source": "@rule.credit_check.passed"}})
    context = ProjectionContext(rule_results_by_slug={"credit_check": [_rule_result(None)]})

    result = project_schema(schema, context)

    expect(result.resolved["/approved"]).to(be_none)
    expect(result.warnings).to(have_len(1))
    expect(result.llm_pointers).to(have_len(0))


def test_project_schema__unknown_rule_slug_resolves_null_with_warning():
    schema = _schema({"approved": {"type": "boolean", "x-source": "@rule.ghost.passed"}})

    result = project_schema(schema, ProjectionContext())

    expect(result.resolved["/approved"]).to(be_none)
    expect(result.warnings).to(have_len(1))


def test_project_schema__rule_with_multiple_results_resolves_list():
    # Decision (spec §6): multi-document rule → list of values, one per result.
    results = [
        _rule_result({"score": 7}, document_refs={"cv": [str(uuid4())]}),
        _rule_result({"score": 4}, document_refs={"cv": [str(uuid4())]}),
    ]
    schema = _schema({"scores": {"type": "array", "x-source": "@rule.scoring.score"}})

    result = project_schema(schema, ProjectionContext(rule_results_by_slug={"scoring": results}))

    expect(result.resolved).to(equal({"/scores": [7, 4]}))
    expect(result.citations["/scores"]).to(have_len(2))


def test_project_schema__rule_result_without_document_refs_resolves_without_citation():
    rule_result = _rule_result({"passed": False}, document_refs={})
    schema = _schema({"approved": {"type": "boolean", "x-source": "@rule.credit_check.passed"}})

    result = project_schema(
        schema, ProjectionContext(rule_results_by_slug={"credit_check": [rule_result]})
    )

    expect(result.resolved).to(equal({"/approved": False}))
    expect(result.citations).to(equal({}))
    expect(result.warnings).to(have_len(1))


# ── #kb and LLM fields ───────────────────────────────────────────────────────


def test_project_schema__kb_ref_is_delegated_to_llm_with_warning():
    schema = _schema({"context": {"type": "string", "x-source": "#puestos"}})

    result = project_schema(schema, ProjectionContext())

    expect(result.resolved).to(equal({}))
    expect(result.llm_pointers).to(equal(["/context"]))
    expect(result.warnings).to(have_len(1))


def test_project_schema__property_without_x_source_is_llm_pointer():
    schema = _schema({"risk_summary": {"type": "string"}})

    result = project_schema(schema, ProjectionContext())

    expect(result.llm_pointers).to(equal(["/risk_summary"]))
    expect(result.resolved).to(equal({}))
    expect(result.warnings).to(have_len(0))


# ── apply_resolved (merge) ───────────────────────────────────────────────────


def test_apply_resolved__resolved_values_override_llm_output():
    llm_output = {"total": 999, "summary": "ok", "nested": {"a": 1}}

    merged = apply_resolved(llm_output, {"/total": 5, "/nested/a": 2, "/extra": "x"})

    expect(merged).to(equal({"total": 5, "summary": "ok", "nested": {"a": 2}, "extra": "x"}))
    # Original LLM payload is untouched (deep copy).
    expect(llm_output["total"]).to(equal(999))
