"""``EnqueueScan`` — the use case behind ``POST /scans`` (12-api §2, §3).

Idempotent, attested scan enqueue. The endpoint only maps ``EnqueueResult`` to
201 (new) / 200 (idempotent hit); all the policy lives here:

1. **Attestation gate (01-legal):** ``enforce_attestation`` raises
   ``AttestationRequiredError`` (422) for an active level without
   ``authorized=true`` — the job is never enqueued in that case.
2. **Host flags / visibility (01-legal):** ``resolve_host_flags`` derives
   ``is_gov`` server-side; ``default_visibility`` decides ``public`` vs ``private``
   (gov + passive + un-owned ⇒ public, everything else ⇒ private).
3. **Site upsert (06):** ``SiteRepository.get_or_create`` resolves one row per
   hostname; ``is_gov`` is never taken from the client.
4. **Two-layer idempotency:**
   - **Layer 1 (partial unique index, 06):** if a live scan already exists for
     ``(site_id, level)`` we return it (``created=False`` → 200). The repo's
     ``enqueue`` also catches the ``IntegrityError`` from the partial index on a
     lost race and returns the live scan with ``created=False``, so a burst
     collapses to one row. ``enqueue`` returns ``(scan, created)`` where
     ``created`` is ``True`` only on the branch that actually inserted the row.
   - **Layer 2 (SAQ job key):** the shared ``SaqCommandEnqueuer`` does **not**
     accept a ``key``/``retries`` today (see plan §2), so we lean on Layer 1 and
     dispatch the ``RunScanCommand`` exactly once — only when the repo reports
     ``created=True`` (never inferred from requester/status).

Rate-limit (5/h per user) is applied by the endpoint via the existing Redis
``create_rate_limit_dependency`` factory — not here.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.common.domain.buses.commands import CommandBus
from src.common.domain.enums.scans import ScanLevel
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.legal import (
    default_visibility,
    enforce_attestation,
    resolve_host_flags,
)
from src.common.domain.models.user import User
from src.scans.application.commands.run_scan import RunScanCommand
from src.scans.domain.models.scan import Scan
from src.scans.domain.repositories.scan import ScanRepository
from src.sites.domain.repositories.site import SiteRepository


@dataclass
class EnqueueResult:
    scan: Scan
    created: bool


@dataclass
class EnqueueScan(UseCase):
    url: str
    level: ScanLevel
    authorized: bool
    user: User
    site_repository: SiteRepository
    scan_repository: ScanRepository
    command_bus: CommandBus

    async def execute(self, *args, **kwargs) -> EnqueueResult:
        level_value = str(self.level)

        # 1. Legal gate — active level without attestation ⇒ 422, nothing enqueued.
        enforce_attestation(level=self.level, authorized=self.authorized)

        # 2/3. Resolve the site (server-derived is_gov) and the default visibility.
        flags = resolve_host_flags(self.url)
        site = await self.site_repository.get_or_create(
            self.url, owner_user_id=None
        )
        visibility = default_visibility(
            is_gov=flags.is_gov, level=self.level, has_owner=False
        )

        # 4. Layer 1 — short-circuit on a live scan for (site, level) ⇒ 200 hit.
        existing = await self.scan_repository.find_active(site.uuid, level_value)
        if existing is not None:
            return EnqueueResult(scan=existing, created=False)

        # The repo reports ``created`` authoritatively: ``True`` only on the
        # fresh-INSERT-won branch, ``False`` on the pre-check hit and the
        # lost-race branch. We no longer infer it from requester/status, so a
        # concurrent same-user enqueue can never dispatch twice for one row.
        scan, created = await self.scan_repository.enqueue(
            site.uuid,
            level_value,
            visibility=str(visibility),
            requested_by=self.user.uuid,
            authorized=self.authorized,
        )

        if created:
            # Layer 2 — dispatch exactly once for a freshly created scan.
            await self.command_bus.dispatch(
                RunScanCommand(scan_id=scan.uuid), run_async=True
            )

        return EnqueueResult(scan=scan, created=created)
