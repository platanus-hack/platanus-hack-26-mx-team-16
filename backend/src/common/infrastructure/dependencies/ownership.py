"""Anti-IDOR ownership dependencies (12-api §"AuthZ por endpoint", plan §4).

The product stores **exploitable vulnerabilities**; without per-resource authZ
Owliver would become a public index of how to hack its users' sites. These
dependencies centralize the rule so every scan/watchlist endpoint enforces it
identically:

- ``require_scan_access`` — read access to a single scan. ``public`` scans (gov
  basic/passive) are open; ``private`` scans require the caller to **own** the
  scan or **watch** the site. Missing/forbidden → ``ScanNotFoundError`` (**404,
  never 403**): the existence of a private scan is never confirmed to a
  non-owner.
- ``require_scan_owner`` — mutations (``cancel``/``share``/``report.pdf``): the
  caller must own the scan; ``public`` alone is **not** enough. Same 404 rule.
- ``require_watchlist_owner`` — ``PATCH``/``DELETE /watchlist/{id}`` where ``{id}``
  is a **watchlist-row uuid** (not a site_id). 404 if the row is absent or not
  the caller's.

Auth uses the existing boilerplate dependencies (``get_authenticated_user`` /
``get_optional_authenticated_user``); the SSE cookie/stream_token variant is
declared by 10-realtime and is out of scope here.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from src.common.domain.contexts.domain import DomainContext
from src.common.domain.enums.scans import ScanVisibility
from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import get_domain_context
from src.common.infrastructure.dependencies.session import (
    get_authenticated_user,
    get_optional_authenticated_user,
)
from src.scans.domain.models.scan import Scan
from src.scans.presentation.exceptions import ScanNotFoundError
from src.sites.domain.models.watchlist import WatchlistEntry
from src.sites.presentation.exceptions import WatchlistEntryNotFoundError


async def _user_watches_site(
    domain_context: DomainContext, user_id: UUID, site_id: UUID
) -> bool:
    entry = await domain_context.watchlist_repository.find(user_id, site_id)
    return entry is not None


async def _owns_or_watches(
    domain_context: DomainContext, user: User | None, scan: Scan
) -> bool:
    if user is None:
        return False
    if scan.requested_by is not None and scan.requested_by == user.uuid:
        return True
    return await _user_watches_site(domain_context, user.uuid, scan.site_id)


async def require_scan_access(
    scan_id: UUID,
    domain_context: DomainContext = Depends(get_domain_context),
    user: User | None = Depends(get_optional_authenticated_user),
) -> Scan:
    """Resolve ``scan_id`` enforcing read access. 404 (not 403) when forbidden."""
    scan = await domain_context.scan_repository.find(scan_id)
    if scan is None:
        raise ScanNotFoundError
    if scan.visibility == str(ScanVisibility.PUBLIC):
        return scan
    if not await _owns_or_watches(domain_context, user, scan):
        # Never confirm existence of a private scan to a non-owner.
        raise ScanNotFoundError
    return scan


async def require_scan_owner(
    scan_id: UUID,
    domain_context: DomainContext = Depends(get_domain_context),
    user: User = Depends(get_authenticated_user),
) -> Scan:
    """Resolve ``scan_id`` for a mutation — caller must OWN it (public is not
    enough). 404 (not 403) when absent or not owned."""
    scan = await domain_context.scan_repository.find(scan_id)
    if scan is None:
        raise ScanNotFoundError
    if scan.requested_by is None or scan.requested_by != user.uuid:
        raise ScanNotFoundError
    return scan


async def require_watchlist_owner(
    watchlist_id: UUID,
    domain_context: DomainContext = Depends(get_domain_context),
    user: User = Depends(get_authenticated_user),
) -> WatchlistEntry:
    """Resolve a watchlist **row** by its uuid for the current user.

    ``{watchlist_id}`` is the ``watchlist.uuid`` returned by ``GET/POST
    /watchlist`` — never a ``site_id``. 404 if the row is absent or belongs to
    another user (no 403 — same anti-IDOR rule)."""
    entries = await domain_context.watchlist_repository.list_for_user(user.uuid)
    for entry in entries:
        if entry.uuid == watchlist_id:
            return entry
    raise WatchlistEntryNotFoundError
