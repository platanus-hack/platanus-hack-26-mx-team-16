"""Passive-profile invariant (01-legal §3) — pure domain.

Invariant: the gov passive scan stays inside the codified allow-list — only the
four passive tools, nuclei restricted to the passive tags and excluding
``intrusive,dos,fuzzing,network``, no spider/katana/zap-spider, root-only, robots
honored. Anything outside fails ``assert_within_passive_profile``.

04 owns ``resolve_tools(is_gov, level)``; this suite asserts the *contract* it must
satisfy (the simulated resolved invocations stand in for 04's output until 04 lands).
"""

from __future__ import annotations

from expects import contain, equal, expect, raise_error

from src.common.domain.legal.passive_profile import (
    GOV_PASSIVE_PROFILE,
    PassiveProfileViolation,
    ToolInvocation,
    assert_within_passive_profile,
)


def _gov_passive_invocations() -> list[ToolInvocation]:
    """Simulated output of 04's ``resolve_tools(is_gov=True, basico)``."""
    return [
        ToolInvocation(tool="testssl"),
        ToolInvocation(tool="security_headers"),
        ToolInvocation(tool="whatweb"),
        ToolInvocation(
            tool="nuclei",
            flags=frozenset(GOV_PASSIVE_PROFILE.nuclei_tags_allow),
            targets_root_only=True,
        ),
    ]


def test_profile_freezes_passive_definition() -> None:
    expect(GOV_PASSIVE_PROFILE.tools).to(
        equal(frozenset({"testssl", "security_headers", "whatweb", "nuclei"}))
    )
    expect(GOV_PASSIVE_PROFILE.spider).to(equal(False))
    expect(GOV_PASSIVE_PROFILE.katana).to(equal(False))
    expect(GOV_PASSIVE_PROFILE.zap_spider).to(equal(False))
    expect(GOV_PASSIVE_PROFILE.root_only).to(equal(True))
    expect(GOV_PASSIVE_PROFILE.honor_robots).to(equal(True))


def test_nuclei_excludes_active_tags() -> None:
    for tag in ("intrusive", "dos", "fuzzing", "network"):
        expect(GOV_PASSIVE_PROFILE.nuclei_tags_exclude).to(contain(tag))
        expect(GOV_PASSIVE_PROFILE.nuclei_tags_allow).not_to(contain(tag))


def test_resolved_gov_tools_are_within_profile() -> None:
    expect(
        assert_within_passive_profile(_gov_passive_invocations())
    ).to(equal(None))


def test_tool_outside_allow_list_fails() -> None:
    invocations = [*_gov_passive_invocations(), ToolInvocation(tool="sqlmap")]
    expect(lambda: assert_within_passive_profile(invocations)).to(
        raise_error(PassiveProfileViolation)
    )


def test_zap_spider_and_katana_absent() -> None:
    # Any crawler/spider tool is outside the allow-list -> rejected.
    for crawler in ("zap_spider", "katana", "zap"):
        invocations = [*_gov_passive_invocations(), ToolInvocation(tool=crawler)]
        expect(lambda inv=invocations: assert_within_passive_profile(inv)).to(
            raise_error(PassiveProfileViolation)
        )


def test_nuclei_intrusive_tag_fails() -> None:
    invocations = [
        ToolInvocation(tool="nuclei", flags=frozenset({"ssl", "intrusive"})),
    ]
    expect(lambda: assert_within_passive_profile(invocations)).to(
        raise_error(PassiveProfileViolation)
    )


def test_nuclei_tag_outside_allow_list_fails() -> None:
    invocations = [
        ToolInvocation(tool="nuclei", flags=frozenset({"cve", "rce"})),
    ]
    expect(lambda: assert_within_passive_profile(invocations)).to(
        raise_error(PassiveProfileViolation)
    )


def test_non_root_target_fails_root_only_profile() -> None:
    invocations = [ToolInvocation(tool="whatweb", targets_root_only=False)]
    expect(lambda: assert_within_passive_profile(invocations)).to(
        raise_error(PassiveProfileViolation)
    )
