"""Functional test: ApiJSONResponse + RawJson preserves JSONB key shape.

Wires a minimal FastAPI app with a single endpoint that returns the
WorkflowPresenter dict (which marks `per_doc_kb_ids` and `output_schema`
as RawJson). Verifies through TestClient that:

- The wrapping ApiResponse envelope is produced (data + timestamp).
- Top-level presenter keys are camelCased by CamelCaseJSONResponse.
- RawJson-wrapped JSONB blobs come through with their original
  domain-defined keys (slugs, snake_case identifiers) intact.
"""

from datetime import UTC, datetime
from uuid import uuid4

from expects import equal, expect, have_keys
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.common.domain.models.processing.workflow import Workflow
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.workflows.presentation.presenters.workflow import WorkflowPresenter


def _build_workflow() -> Workflow:
    return Workflow(
        uuid=uuid4(),
        tenant_id=uuid4(),
        name="Test Workflow",
        selected_doc_types=["loan_contract", "id_card"],
        per_doc_kb_ids={"loan_contract": ["kb-id-1", "kb-id-2"]},
        output_schema={
            "type": "object",
            "properties": {
                "loan_amount": {"type": "number", "x-source": "@loan_contract.loan_amount"},
                "full_name": {"type": "string"},
            },
        },
        created_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
    )


def _build_client(workflow: Workflow) -> TestClient:
    app = FastAPI(default_response_class=ApiJSONResponse)

    @app.get("/workflow")
    def get_workflow():
        return WorkflowPresenter(instance=workflow).to_dict

    return TestClient(app)


def test_api_json_response__wraps_in_data_envelope_with_timestamp():
    client = _build_client(_build_workflow())

    response = client.get("/workflow")

    expect(response.status_code).to(equal(200))
    body = response.json()
    expect(body).to(have_keys("data", "timestamp"))


def test_api_json_response__camelcases_top_level_presenter_keys():
    client = _build_client(_build_workflow())

    data = client.get("/workflow").json()["data"]

    expect(data).to(
        have_keys(
            "workflowId",
            "tenantId",
            "name",
            # E7 · F2: `workflowType` retirado; el presenter expone `capabilities`.
            "capabilities",
            "selectedDocTypes",
            "kbDocumentIds",
            "perDocKbIds",
            "outputSchema",
            "createdAt",
            "updatedAt",
        )
    )


def test_api_json_response__raw_json_preserves_outer_jsonb_keys():
    client = _build_client(_build_workflow())

    data = client.get("/workflow").json()["data"]

    # per_doc_kb_ids is RawJson — its keys (doc-type slugs) stay verbatim
    # and would otherwise be camelCased into "loanContract".
    expect(data["perDocKbIds"]).to(have_keys("loan_contract"))


def test_api_json_response__raw_json_preserves_nested_keys():
    client = _build_client(_build_workflow())

    data = client.get("/workflow").json()["data"]

    # output_schema is RawJson — user-defined field names (snake_case) and
    # JSON-Schema keywords survive untouched.
    properties = data["outputSchema"]["properties"]
    expect(properties).to(have_keys("loan_amount", "full_name"))
    expect(properties["loan_amount"]).to(have_keys("type", "x-source"))
    expect(properties["loan_amount"]["x-source"]).to(equal("@loan_contract.loan_amount"))


def test_api_json_response__non_raw_list_values_pass_through_unchanged():
    """Sanity check: list items (selected_doc_types) are not transformed."""
    client = _build_client(_build_workflow())

    data = client.get("/workflow").json()["data"]

    expect(data["selectedDocTypes"]).to(equal(["loan_contract", "id_card"]))
