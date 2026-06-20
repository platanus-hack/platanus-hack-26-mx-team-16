"""Unit tests for TokenPromptRenderer (validation + substitution)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.enums.tenants import TenantStatus
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.common.domain.models.tenants.tenant import Tenant
from src.workflows.domain.services.prompt_renderer import (
    RendererNotConfiguredError,
    TokenPromptRenderer,
    UnknownTokenError,
)
from src.workflows.domain.services.token_resolver import TokenContext


@pytest.fixture
def tenant():
    return Tenant(
        uuid=uuid4(),
        owner_id=uuid4(),
        name="Acme Inc.",
        slug="acme",
        status=TenantStatus.ACTIVE,
    )


@pytest.fixture
def rule(tenant):
    return WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant.uuid,
        workflow_id=uuid4(),
        name="rule",
        kind="VALIDATION",
        prompt="x",
        config={"severity": "BLOCKER"},
    )


@pytest.fixture
def ctx(tenant, rule):
    return TokenContext(
        case_name="Case 42",
        tenant=tenant,
        run_id=uuid4(),
        rule=rule,
        now=datetime(2026, 5, 5, 12, 30, tzinfo=timezone.utc),
        run_completed_at=datetime(2026, 5, 5, 12, 31, tzinfo=timezone.utc),
    )


def test_assert_valid__accepts_known_tokens():
    renderer = TokenPromptRenderer()

    renderer.assert_valid("hello {{case.name}} on {{today}}")  # no raise


def test_assert_valid__rejects_unknown_tokens():
    renderer = TokenPromptRenderer()

    with pytest.raises(UnknownTokenError, match="case.unknown"):
        renderer.assert_valid("hi {{case.unknown}}")


def test_assert_valid__accepts_template_without_tokens():
    renderer = TokenPromptRenderer()

    renderer.assert_valid("plain text without placeholders")  # no raise


async def test_render__substitutes_known_tokens(ctx):
    renderer = TokenPromptRenderer(ctx=ctx)

    result = await renderer.render("Hello {{case.name}} from {{tenant.name}} in {{today.year}}")

    expect(result.text).to(equal("Hello Case 42 from Acme Inc. in 2026"))
    expect(result.unresolved_tokens).to(equal([]))


async def test_render__supports_run_scope_tokens(ctx):
    renderer = TokenPromptRenderer(ctx=ctx)

    result = await renderer.render("run {{run.id}} closed at {{run.completed_at}}")

    expect(str(ctx.run_id) in result.text).to(equal(True))
    expect("2026-05-05T12:31" in result.text).to(equal(True))


async def test_render__without_context_raises():
    renderer = TokenPromptRenderer()

    with pytest.raises(RendererNotConfiguredError):
        await renderer.render("anything")


async def test_render__rejects_unknown_token_before_resolving(ctx):
    renderer = TokenPromptRenderer(ctx=ctx)

    with pytest.raises(UnknownTokenError):
        await renderer.render("hi {{nope}}")
