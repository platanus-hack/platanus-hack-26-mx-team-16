"""Legal contract of "passive" — the gov allow-list (spec §3).

The whole legal defense of the gov ranking ("equivalent to Observatory / SSL
Labs / Shodan") only holds if what runs is genuinely passive. "Passive" is
therefore defined by a **tools+flags allow-list codified here**, not by intent
and not user-configurable. The worker (04) imports ``GOV_PASSIVE_PROFILE`` as the
source of truth for ``(is_gov=True, basico)`` and must validate its resolved tool
invocations against ``assert_within_passive_profile``. 04 owns the
intermediate/advanced (active) profiles; this module freezes only the legal
passive contract.

Allow-list, not deny-list: anything not explicitly allowed is forbidden.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolInvocation:
    """A concrete tool the worker resolved for a scan.

    ``flags`` is the set of flag/tag tokens the invocation carries (e.g. nuclei
    ``-tags`` values). The validator checks both the tool name and these tokens
    against the profile. ``targets_root_only`` lets the worker assert it is not
    spidering/crawling beyond the root URL.
    """

    tool: str
    flags: frozenset[str] = field(default_factory=frozenset)
    targets_root_only: bool = True


@dataclass(frozen=True)
class PassiveProfile:
    """Frozen legal contract of a passive scan profile (§3).

    For gov/basic this freezes: the allowed tool set, the nuclei tag allow/deny
    lists, the disabling of every crawler/spider, root-only targeting and the
    obligation to honor ``robots.txt``.
    """

    tools: frozenset[str]
    nuclei_tags_allow: tuple[str, ...]
    nuclei_tags_exclude: tuple[str, ...]
    spider: bool
    katana: bool
    zap_spider: bool
    root_only: bool
    honor_robots: bool


# §3 — frozen passive profile for ``(is_gov=True, basico)``. Network footprint kept
# close to Observatory / SSL Labs / Shodan: TLS/headers/fingerprint + a bounded set
# of requests over the root and a few known routes, with NO crawl/spider and
# honoring ``robots.txt``.
GOV_PASSIVE_PROFILE = PassiveProfile(
    tools=frozenset({"testssl", "security_headers", "whatweb", "nuclei"}),
    nuclei_tags_allow=("exposures", "misconfiguration", "ssl", "tech", "dns"),
    nuclei_tags_exclude=("intrusive", "dos", "fuzzing", "network"),
    spider=False,
    katana=False,
    zap_spider=False,
    root_only=True,
    honor_robots=True,
)


class PassiveProfileViolation(AssertionError):
    """Raised when a resolved tool/flag falls outside the passive allow-list.

    Subclasses ``AssertionError`` so it reads naturally in the invariant test
    suite (§5) while still being explicitly catchable. This is an internal
    code-invariant violation (a worker/scheduler bug), not a user-facing error.
    """


def assert_within_passive_profile(
    invocations: Iterable[ToolInvocation],
    profile: PassiveProfile = GOV_PASSIVE_PROFILE,
) -> None:
    """Assert every invocation stays inside ``profile`` (allow-list).

    Fails (``PassiveProfileViolation``) if any invocation:
    - uses a tool not in ``profile.tools``;
    - (for nuclei) carries a tag outside the allow-list or any excluded tag;
    - targets beyond the root while ``profile.root_only`` is set.

    Used by the worker (04) and by the invariant test suite (§5) to prove the gov
    passive scan never exceeds its legal footprint.
    """
    allow = set(profile.nuclei_tags_allow)
    exclude = set(profile.nuclei_tags_exclude)

    for inv in invocations:
        if inv.tool not in profile.tools:
            raise PassiveProfileViolation(
                f"tool {inv.tool!r} is not in the gov passive allow-list "
                f"{sorted(profile.tools)}"
            )

        if profile.root_only and not inv.targets_root_only:
            raise PassiveProfileViolation(
                f"tool {inv.tool!r} targets beyond the root URL, but the gov "
                "passive profile is root-only (no spider/crawl)"
            )

        if inv.tool == "nuclei":
            forbidden = inv.flags & exclude
            if forbidden:
                raise PassiveProfileViolation(
                    f"nuclei carries excluded tags {sorted(forbidden)} "
                    "(intrusive/dos/fuzzing/network are forbidden for gov)"
                )
            outside = inv.flags - allow
            if outside:
                raise PassiveProfileViolation(
                    f"nuclei carries tags {sorted(outside)} outside the passive "
                    f"allow-list {sorted(allow)}"
                )
