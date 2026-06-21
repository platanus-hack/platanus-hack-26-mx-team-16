"""SQL implementation of ``FindingRepository`` — UPSERT by (site_id, dedupe_key)
(06-data-model §3.3, §4)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.scans.finding import FindingORM
from src.common.domain.enums.scans import FindingSeverity, FindingStatus
from src.common.infrastructure.helpers.database import atomic_transaction
from src.scans.domain.models.finding import FindingRecord
from src.scans.domain.repositories.finding import FindingRepository
from src.scans.infrastructure.builders.scan import build_finding


@dataclass
class SQLFindingRepository(FindingRepository):
    session: AsyncSession

    async def upsert(self, finding: FindingRecord) -> FindingRecord:
        now = datetime.now(timezone.utc)
        payload = {
            "uuid": finding.uuid or uuid.uuid4(),
            "scan_id": finding.scan_id,
            "site_id": finding.site_id,
            "source": finding.source,
            "tool": finding.tool,
            "category": finding.category,
            "title": finding.title,
            "severity": finding.severity,
            "cvss": finding.cvss,
            "confidence": finding.confidence,
            "description": finding.description,
            "evidence": finding.evidence,
            "affected_url": finding.affected_url,
            "endpoint": finding.endpoint,
            "param": finding.param,
            "impact": finding.impact,
            "remediation": finding.remediation,
            "references": finding.references,
            "status": finding.status or str(FindingStatus.OPEN),
            "dedupe_key": finding.dedupe_key,
            "first_seen": now,
            "last_seen": now,
        }
        stmt = pg_insert(FindingORM).values(**payload)
        # On re-scan: refresh the mutable fields + last_seen, keep first_seen,
        # re-open if it had been marked fixed. first_seen is preserved (§4).
        update_cols = {
            "scan_id": stmt.excluded.scan_id,
            "title": stmt.excluded.title,
            "severity": stmt.excluded.severity,
            "cvss": stmt.excluded.cvss,
            "confidence": stmt.excluded.confidence,
            "description": stmt.excluded.description,
            "evidence": stmt.excluded.evidence,
            "affected_url": stmt.excluded.affected_url,
            "endpoint": stmt.excluded.endpoint,
            "impact": stmt.excluded.impact,
            "remediation": stmt.excluded.remediation,
            "references": stmt.excluded.references,
            "status": str(FindingStatus.OPEN),
            "last_seen": stmt.excluded.last_seen,
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_findings_site_dedupe", set_=update_cols
        ).returning(FindingORM)
        async with atomic_transaction(self.session):
            result = await self.session.execute(stmt)
            orm = result.scalar_one()
        await self.session.refresh(orm)
        return build_finding(orm)

    async def list_for_scan(self, scan_id: UUID) -> list[FindingRecord]:
        result = await self.session.execute(
            select(FindingORM).where(FindingORM.scan_id == scan_id)
        )
        return [build_finding(orm) for orm in result.scalars().all()]

    async def list_for_site(self, site_id: UUID) -> list[FindingRecord]:
        result = await self.session.execute(
            select(FindingORM).where(FindingORM.site_id == site_id)
        )
        return [build_finding(orm) for orm in result.scalars().all()]

    async def criticals_first_seen_in(self, scan_id: UUID) -> list[FindingRecord]:
        # A finding's UPSERT sets first_seen and last_seen to ``now`` on insert
        # and only refreshes last_seen on conflict (§4). So a finding that is new
        # at the site level has ``first_seen == last_seen``; a re-seen one has
        # ``first_seen < last_seen``. We scope to this scan's critical rows.
        stmt = (
            select(FindingORM)
            .where(FindingORM.scan_id == scan_id)
            .where(FindingORM.severity == str(FindingSeverity.CRITICAL))
            .where(FindingORM.first_seen == FindingORM.last_seen)
        )
        result = await self.session.execute(stmt)
        return [build_finding(orm) for orm in result.scalars().all()]

    async def mark_fixed_absent(self, site_id: UUID, present_keys: list[str]) -> int:
        stmt = (
            update(FindingORM)
            .where(FindingORM.site_id == site_id)
            .where(FindingORM.status != str(FindingStatus.ACCEPTED))
            .where(FindingORM.dedupe_key.notin_(present_keys or [""]))
            .values(status=str(FindingStatus.FIXED))
        )
        async with atomic_transaction(self.session):
            result = await self.session.execute(stmt)
            rowcount = result.rowcount or 0
        return rowcount
