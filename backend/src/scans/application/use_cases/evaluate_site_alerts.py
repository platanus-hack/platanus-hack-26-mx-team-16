"""``EvaluateSiteAlerts`` — the site-level monitoring decision
(08-ranking-watchlists §4.3).

Runs **after** a monitoring scan persisted its grade and findings. It is gated to
**cron-origin** scans (``scan.requested_by IS NULL`` — the contract fixed in plan
§4.2: cron/seed scans carry no requester, manual scans do). It then compares the
scan against the site history (not against the scan) and, if the grade dropped or
a new critical appeared, dispatches a redacted alert to the site owner.

Pure-ish orchestration over repos; the actual channel I/O lives in
``DispatchAlert``. A gov seed site (no owner) never has a recipient, so no alert
is emitted even though its grade is refreshed.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.application.logging import get_logger
from src.common.domain.buses.commands import CommandBus
from src.common.domain.interfaces.use_case import UseCase
from src.scans.application.use_cases.dispatch_alert import DispatchAlert
from src.scans.domain.models.alert import Alert
from src.scans.domain.repositories.alert import AlertRepository
from src.scans.domain.repositories.finding import FindingRepository
from src.scans.domain.repositories.scan import ScanRepository
from src.scans.domain.services.grade_delta import compare_grade
from src.scans.infrastructure.alerts.render import build_alert_payload
from src.sites.domain.repositories.notification_prefs import (
    NotificationPrefsRepository,
)
from src.sites.domain.repositories.site import SiteRepository
from src.users.domain.repositories.user import UserRepository

logger = get_logger(__name__)


@dataclass
class EvaluateSiteAlerts(UseCase):
    scan_id: UUID
    scan_repository: ScanRepository
    finding_repository: FindingRepository
    site_repository: SiteRepository
    notification_prefs_repository: NotificationPrefsRepository
    user_repository: UserRepository
    alert_repository: AlertRepository
    command_bus: CommandBus

    async def execute(self, *args, **kwargs) -> list[Alert]:
        scan = await self.scan_repository.find(self.scan_id)
        if scan is None:
            return []

        # Gate: only cron/monitoring scans (requested_by IS NULL) evaluate alerts
        # (§4.2). A manual scan never triggers monitoring alerts.
        if scan.requested_by is not None:
            return []

        # Comparison base: the previous terminal+graded scan of the same site.
        prev = await self.scan_repository.previous_graded_scan(
            scan.site_id, before=scan.uuid
        )
        prev_grade = prev.overall_grade if prev is not None else None
        grade_dropped = compare_grade(prev_grade, scan.overall_grade)

        new_criticals = await self.finding_repository.criticals_first_seen_in(
            scan.uuid
        )

        if not grade_dropped and not new_criticals:
            return []

        site = await self.site_repository.find(scan.site_id)
        if site is None or site.owner_user_id is None:
            # Gov seed (no owner) → grade refreshed, but nobody to notify.
            return []

        prefs = await self.notification_prefs_repository.get(site.owner_user_id)
        owner = await self.user_repository.find(site.owner_user_id)
        recipient_email = (
            owner.email_address.email
            if owner is not None and owner.email_address is not None
            else None
        )

        if prefs is None:
            # No explicit prefs row → default (email on, no slack).
            from src.sites.domain.models.notification_prefs import NotificationPrefs

            prefs = NotificationPrefs(user_id=site.owner_user_id)

        payload = build_alert_payload(
            hostname=site.hostname,
            previous_grade=prev_grade,
            current_grade=scan.overall_grade,
            grade_dropped=grade_dropped,
            new_criticals=new_criticals,
        )

        return await DispatchAlert(
            user_id=site.owner_user_id,
            site_id=site.uuid,
            scan_id=scan.uuid,
            recipient_email=recipient_email,
            prefs=prefs,
            payload=payload,
            alert_repository=self.alert_repository,
            command_bus=self.command_bus,
        ).execute()
