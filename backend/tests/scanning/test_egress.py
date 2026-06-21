"""Egress guard (plan §10: test_egress_guard) — SSRF lateral defense (spec §5)."""

from __future__ import annotations

from expects import expect, raise_error

from src.scanning.egress import EgressViolation, assert_public_target


def test_rejects_private_rfc1918_ip() -> None:
    expect(lambda: assert_public_target("http://10.0.0.5/")).to(raise_error(EgressViolation))
    expect(lambda: assert_public_target("http://192.168.1.1/")).to(raise_error(EgressViolation))
    expect(lambda: assert_public_target("http://172.16.0.1/")).to(raise_error(EgressViolation))


def test_rejects_loopback_and_metadata() -> None:
    expect(lambda: assert_public_target("http://127.0.0.1/")).to(raise_error(EgressViolation))
    expect(lambda: assert_public_target("http://169.254.169.254/latest/meta-data/")).to(
        raise_error(EgressViolation)
    )


def test_rejects_missing_host() -> None:
    expect(lambda: assert_public_target("not-a-url")).to(raise_error(EgressViolation))


def test_allows_public_ip() -> None:
    # 1.1.1.1 is a public IP literal — must NOT raise.
    assert_public_target("https://1.1.1.1/")


def test_demo_allow_list_permits_localhost() -> None:
    # localhost is blocked by default but allowed via explicit demo allow-list.
    expect(lambda: assert_public_target("http://localhost:3000/")).to(raise_error(EgressViolation))
    assert_public_target("http://localhost:3000/", allowed_demo_hosts=frozenset({"localhost"}))


def test_metadata_ip_blocked_even_in_demo_unless_listed() -> None:
    # metadata IP is a literal IP; not auto-allowed. Demo allow-list is by hostname.
    expect(
        lambda: assert_public_target(
            "http://169.254.169.254/", allowed_demo_hosts=frozenset({"localhost"})
        )
    ).to(raise_error(EgressViolation))
