"""Egress guard against lateral SSRF (spec §5, plan §5).

Scanners attack external URLs with egress to the internet. Two complementary
controls keep them from reaching the internal network or the cloud metadata
endpoint:

1. Docker networks (``owliver_egress`` / ``owliver_internal``) — see
   ``docker-compose.scanners.yml``; every sibling ``docker run`` carries
   ``--network owliver_egress`` (centralized in ``run_tool``).
2. ``assert_public_target`` (here): before resolving a target, reject private
   IPs (RFC1918, loopback, link-local) and ``169.254.169.254`` (cloud metadata).

A controlled exception exists for the demo profile, which runs against
``localhost`` targets (juice-shop / the own bot): hosts may be allow-listed
explicitly via the ``allowed_demo_hosts`` argument, NEVER by default.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from src.common.domain.exceptions._base import DomainError

# Cloud instance metadata endpoints (IMDS) — never a legitimate scan target.
METADATA_IPS: frozenset[str] = frozenset(
    {
        "169.254.169.254",  # AWS / GCP / Azure / DigitalOcean IMDS
        "fd00:ec2::254",  # AWS IMDS IPv6
    }
)


class EgressViolation(DomainError):
    """Raised when a target resolves to a forbidden (internal/metadata) address.

    This is an internal safety invariant of the engine: a target that points at
    the private network or the cloud metadata endpoint must never be scanned.
    """

    def __init__(self, message: str) -> None:
        super().__init__(code="egress_violation", message=message, status_code=400)


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True if ``ip`` is in a range a scanner must never reach."""
    if str(ip) in METADATA_IPS:
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _resolve_host(host: str) -> list[str]:
    """Resolve ``host`` to its IP addresses; ``[]`` if it cannot be resolved.

    DNS resolution is part of the guard: a public-looking hostname that resolves
    to a private IP (DNS rebinding / SSRF) must still be rejected.
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return []
    return [info[4][0] for info in infos]


def assert_public_target(
    url: str,
    *,
    allowed_demo_hosts: frozenset[str] | None = None,
) -> None:
    """Assert ``url`` points at a public host (spec §5).

    Rejects (``EgressViolation``):
    - literal private/loopback/link-local/reserved IPs,
    - the cloud metadata IPs (``169.254.169.254`` & friends),
    - hostnames that *resolve* to any of the above (DNS rebinding defense).

    ``allowed_demo_hosts`` is an explicit opt-in allow-list (e.g.
    ``{"localhost", "juice-shop"}``) for the demo profile; those hosts skip the
    private-range check. It is empty by default — never broadens automatically.
    """
    allowed = allowed_demo_hosts or frozenset()
    parsed = urlparse(url)
    host = parsed.hostname

    if not host:
        raise EgressViolation(f"target {url!r} has no host component")

    if host in allowed:
        return

    # If the host is a literal IP, check it directly.
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        if _is_blocked_ip(literal):
            raise EgressViolation(
                f"target {url!r} points at a non-public address {host} "
                "(private/loopback/link-local/metadata)"
            )
        return

    # Hostname: it must resolve, and none of its addresses may be blocked.
    addresses = _resolve_host(host)
    if not addresses:
        raise EgressViolation(f"target host {host!r} does not resolve to any address")

    for addr in addresses:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _is_blocked_ip(ip):
            raise EgressViolation(
                f"target host {host!r} resolves to non-public address {addr} "
                "(possible SSRF / DNS-rebinding)"
            )
