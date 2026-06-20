"""ORM -> domain builders for the scans module (06-data-model)."""

from __future__ import annotations

from src.common.database.models.scans.agentic_surface import AgenticSurfaceORM
from src.common.database.models.scans.alert import AlertORM
from src.common.database.models.scans.finding import FindingORM
from src.common.database.models.scans.public_report import PublicReportORM
from src.common.database.models.scans.scan import ScanORM
from src.common.database.models.scans.scan_event import ScanEventORM
from src.scans.domain.contracts.events import ScanEvent
from src.scans.domain.models.agentic_surface import AgenticSurface
from src.scans.domain.models.alert import Alert
from src.scans.domain.models.finding import FindingRecord
from src.scans.domain.models.public_report import PublicReport
from src.scans.domain.models.scan import Scan


def build_scan(orm: ScanORM) -> Scan:
    return Scan.model_validate(orm)


def build_finding(orm: FindingORM) -> FindingRecord:
    return FindingRecord.model_validate(orm)


def build_agentic_surface(orm: AgenticSurfaceORM) -> AgenticSurface:
    return AgenticSurface.model_validate(orm)


def build_alert(orm: AlertORM) -> Alert:
    return Alert.model_validate(orm)


def build_public_report(orm: PublicReportORM) -> PublicReport:
    return PublicReport.model_validate(orm)


def build_scan_event(orm: ScanEventORM) -> ScanEvent:
    return ScanEvent.model_validate(orm)
