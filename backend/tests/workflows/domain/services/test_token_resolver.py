"""Unit tests for the runtime token resolver."""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from expects import be_a, equal, expect, raise_error

from src.common.domain.enums.tenants import TenantStatus
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.common.domain.models.tenants.tenant import Tenant
from src.workflows.domain.services.token_resolver import (
    TokenContext,
    TokenScopeError,
    resolve,
    resolve_all,
    to_prompt_value,
)


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
        prompt="check {{rule.severity}}",
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
    )


def test_resolve__now_returns_datetime(ctx):
    expect(resolve("now", ctx)).to(equal(ctx.now))


def test_resolve__today_returns_date(ctx):
    result = resolve("today", ctx)

    expect(result).to(be_a(date))
    expect(result).to(equal(date(2026, 5, 5)))


def test_resolve__today_year_returns_int(ctx):
    expect(resolve("today.year", ctx)).to(equal(2026))


def test_resolve__case_name_returns_value(ctx):
    expect(resolve("case.name", ctx)).to(equal("Case 42"))


def test_resolve__tenant_name_returns_value(ctx):
    expect(resolve("tenant.name", ctx)).to(equal("Acme Inc."))


def test_resolve__rule_severity_returns_config_value(ctx):
    expect(resolve("rule.severity", ctx)).to(equal("BLOCKER"))


def test_resolve__case_name_without_case_raises():
    ctx_without_case = TokenContext(
        case_name=None,
        tenant=None,
        run_id=None,
        rule=None,
        now=datetime.now(timezone.utc),
    )

    expect(lambda: resolve("case.name", ctx_without_case)).to(raise_error(TokenScopeError))


def test_resolve__tenant_name_without_tenant_raises():
    ctx_without_tenant = TokenContext(
        case_name="x",
        tenant=None,
        run_id=None,
        rule=None,
        now=datetime.now(timezone.utc),
    )

    expect(lambda: resolve("tenant.name", ctx_without_tenant)).to(raise_error(TokenScopeError))


def test_resolve__unknown_token_raises_keyerror(ctx):
    expect(lambda: resolve("unknown_token", ctx)).to(raise_error(KeyError))


def test_resolve_all__returns_dict_keyed_by_name(ctx):
    result = resolve_all(["now", "today.year", "tenant.name"], ctx)

    expect(set(result.keys())).to(equal({"now", "today.year", "tenant.name"}))
    expect(result["today.year"]).to(equal(2026))


def test_resolve__run_id_returns_uuid_when_present(ctx):
    expect(resolve("run.id", ctx)).to(equal(ctx.run_id))


def test_resolve__run_id_raises_when_missing(tenant, rule):
    ctx_no_run = TokenContext(
        case_name="c",
        tenant=tenant,
        run_id=None,
        rule=rule,
        now=datetime.now(timezone.utc),
    )

    expect(lambda: resolve("run.id", ctx_no_run)).to(raise_error(TokenScopeError))


def test_resolve__run_completed_at_requires_explicit_completion(tenant, rule):
    completed_at = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    ctx = TokenContext(
        case_name="c",
        tenant=tenant,
        run_id=uuid4(),
        rule=rule,
        now=datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc),
        run_completed_at=completed_at,
    )

    expect(resolve("run.completed_at", ctx)).to(equal(completed_at))


def test_resolve__run_completed_at_raises_when_run_in_progress(ctx):
    expect(lambda: resolve("run.completed_at", ctx)).to(raise_error(TokenScopeError))


def test_resolve__rule_severity_defaults_to_major_when_unset(tenant):
    rule_no_severity = WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant.uuid,
        workflow_id=uuid4(),
        name="r",
        kind="VALIDATION",
        prompt="x",
        config={},
    )
    ctx = TokenContext(
        case_name="c",
        tenant=tenant,
        run_id=uuid4(),
        rule=rule_no_severity,
        now=datetime.now(timezone.utc),
    )

    expect(resolve("rule.severity", ctx)).to(equal("MAJOR"))


def test_resolve__rule_severity_raises_when_no_rule_in_scope(tenant):
    ctx_no_rule = TokenContext(
        case_name="c",
        tenant=tenant,
        run_id=None,
        rule=None,
        now=datetime.now(timezone.utc),
    )

    expect(lambda: resolve("rule.severity", ctx_no_rule)).to(raise_error(TokenScopeError))


def test_resolve_all__now_and_today_share_the_same_instant(ctx):
    out = resolve_all(["now", "today"], ctx)

    expect(out["today"]).to(equal(out["now"].date()))


def test_to_prompt_value__formats_datetime_as_isoformat():
    instant = datetime(2026, 5, 5, 12, 30, tzinfo=timezone.utc)

    expect(to_prompt_value(instant)).to(equal(instant.isoformat()))


def test_to_prompt_value__none_becomes_empty_string():
    expect(to_prompt_value(None)).to(equal(""))


def test_to_prompt_value__numeric_value_becomes_string():
    expect(to_prompt_value(2026)).to(equal("2026"))
