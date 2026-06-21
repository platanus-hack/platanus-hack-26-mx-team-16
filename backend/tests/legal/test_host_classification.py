"""Host classification invariant (01-legal §2.4, §3) — pure domain.

Invariant: ``is_gov`` is derived only from the ``.gob.mx`` suffix, server-side,
case/port/scheme tolerant; ``is_sensitive`` is a superset of ``is_gov``. The sites
host service must delegate to this single source of truth.
"""

from __future__ import annotations

import pytest
from expects import equal, expect

from src.common.domain.legal.host import (
    HostFlags,
    is_gov_hostname,
    is_sensitive_hostname,
    resolve_host_flags,
)


@pytest.mark.parametrize(
    "value",
    [
        "gob.mx",
        "www.gob.mx",
        "sat.gob.mx",
        "HTTPS://SAT.GOB.MX/login",
        "sat.gob.mx:8443",
        "sat.gob.mx.",
        "https://portal.x.gob.mx",
    ],
)
def test_gov_hostnames(value: str) -> None:
    expect(is_gov_hostname(value)).to(equal(True))


@pytest.mark.parametrize(
    "value",
    [
        "example.com",
        "gob.mx.evil.com",  # suffix spoof must NOT match
        "notgob.mx",  # missing the dot boundary -> still endswith .gob.mx? -> check
        "google.com",
    ],
)
def test_non_gov_hostnames(value: str) -> None:
    # ``notgob.mx`` ends with ``gob.mx`` but NOT ``.gob.mx`` -> not gov.
    if value == "notgob.mx":
        expect(is_gov_hostname(value)).to(equal(False))
    elif value == "gob.mx.evil.com":
        expect(is_gov_hostname(value)).to(equal(False))
    else:
        expect(is_gov_hostname(value)).to(equal(False))


def test_gov_implies_sensitive() -> None:
    expect(is_sensitive_hostname("sat.gob.mx")).to(equal(True))


def test_sensitive_superset_of_gov() -> None:
    # mil.mx is sensitive but not gov.
    expect(is_sensitive_hostname("ejercito.mil.mx")).to(equal(True))
    expect(is_gov_hostname("ejercito.mil.mx")).to(equal(False))


def test_resolve_host_flags_full_url() -> None:
    flags = resolve_host_flags("https://www.SAT.gob.mx:443/portal?x=1")
    expect(flags).to(
        equal(HostFlags(hostname="www.sat.gob.mx", is_gov=True, is_sensitive=True))
    )


def test_resolve_host_flags_non_gov() -> None:
    flags = resolve_host_flags("example.com")
    expect(flags.is_gov).to(equal(False))
    expect(flags.is_sensitive).to(equal(False))
    expect(flags.hostname).to(equal("example.com"))


def test_sites_service_delegates_to_legal() -> None:
    # The sites host service must be the SAME callable as the legal one
    # (single source of truth — no divergent is_gov implementation).
    from src.sites.domain.services.host import (
        resolve_host_flags as sites_resolve,
    )

    expect(sites_resolve).to(equal(resolve_host_flags))
