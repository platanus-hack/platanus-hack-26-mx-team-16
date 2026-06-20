"""E5 · matriz rol×acción por workflow (permission-based, diseño §5)."""

from __future__ import annotations

from expects import be_false, be_true, equal, expect

from src.common.domain.permissions.workflow_actions import (
    WORKFLOW_ROLE_ACTIONS,
    WorkflowActionForbiddenError,
    workflow_role_allows,
)


def test_matrix__viewer_only_views():
    expect(workflow_role_allows("viewer", "view")).to(be_true)
    expect(workflow_role_allows("viewer", "operate")).to(be_false)
    expect(workflow_role_allows("viewer", "approve")).to(be_false)
    expect(workflow_role_allows("viewer", "manage")).to(be_false)


def test_matrix__member_operates_but_does_not_manage_nor_approve():
    expect(workflow_role_allows("member", "view")).to(be_true)
    expect(workflow_role_allows("member", "operate")).to(be_true)
    expect(workflow_role_allows("member", "approve")).to(be_false)
    expect(workflow_role_allows("member", "manage")).to(be_false)


def test_matrix__admin_does_everything():
    for action in ("view", "operate", "approve", "manage"):
        expect(workflow_role_allows("admin", action)).to(be_true)


def test_matrix__no_role_denies_everything():
    for action in ("view", "operate", "approve", "manage"):
        expect(workflow_role_allows(None, action)).to(be_false)


def test_matrix__unknown_role_denies_everything():
    expect(workflow_role_allows("ghost", "view")).to(be_false)


def test_matrix__shape_is_the_decided_v1():
    expect(WORKFLOW_ROLE_ACTIONS).to(
        equal(
            {
                "viewer": frozenset({"view"}),
                "member": frozenset({"view", "operate"}),
                "admin": frozenset({"view", "operate", "approve", "manage"}),
            }
        )
    )


def test_forbidden_error__is_403_with_action_context():
    error = WorkflowActionForbiddenError("approve", "wf-1", "member")
    expect(error.status_code).to(equal(403))
    expect(error.code).to(equal("workflow.action_forbidden"))
    expect(error.context["action"]).to(equal("approve"))
    expect(error.context["role"]).to(equal("member"))
