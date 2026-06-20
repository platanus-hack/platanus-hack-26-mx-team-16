"""Presenters: domain entities → camelCase dicts (wire format).

The project's camelCase middleware only converts incoming request bodies;
outgoing responses must already be camelCase. Each presenter owns the
exact wire shape — keep the keys here in sync with the spec's JSON
examples (`product/plans/dashboard/dashboard-data.md`).
"""

from dataclasses import dataclass
from typing import Any

from src.common.domain.interfaces.presenter import Presenter
from src.dashboard.domain.entities.overview import OverviewData
from src.dashboard.domain.entities.processing import ProcessingData


@dataclass
class OverviewPresenter(Presenter[OverviewData]):
    instance: OverviewData

    @property
    def to_dict(self) -> dict[str, Any]:
        summary = self.instance.summary
        return {
            "summary": {
                "totalDocuments": {
                    "value": summary.total_documents.value,
                    "deltaPct": summary.total_documents.delta_pct,
                },
                "documentsProcessed": {
                    "value": summary.documents_processed.value,
                    "deltaPct": summary.documents_processed.delta_pct,
                },
                "activeWorkflows": {
                    "value": summary.active_workflows.value,
                    "deltaPct": summary.active_workflows.delta_pct,
                },
                "processingQueue": {
                    "value": summary.processing_queue.value,
                    "deltaSinceLastHour": summary.processing_queue.delta_since_last_hour,
                },
            },
            "throughput": [
                {
                    "label": b.label,
                    "year": b.year,
                    "month": b.month,
                    "total": b.total,
                }
                for b in self.instance.throughput
            ],
            "recentDocuments": [
                {
                    "uuid": str(d.uuid),
                    "name": d.name,
                    "workflowSlug": d.workflow_slug,
                    "workflowName": d.workflow_name,
                    "status": d.status.value,
                    "pageCount": d.page_count,
                    "createdAt": d.created_at.isoformat(),
                    "updatedAt": d.updated_at.isoformat(),
                }
                for d in self.instance.recent_documents
            ],
        }


@dataclass
class ProcessingPresenter(Presenter[ProcessingData]):
    instance: ProcessingData

    @property
    def to_dict(self) -> dict[str, Any]:
        summary = self.instance.summary
        return {
            "summary": {
                "inQueue": summary.in_queue,
                "processing": summary.processing,
                "completedToday": summary.completed_today,
                "failed": summary.failed,
                "avgProcessingSeconds": summary.avg_processing_seconds,
            },
            "stages": [
                {
                    "stage": s.stage.value,
                    "label": s.label,
                    "count": s.count,
                }
                for s in self.instance.stages
            ],
            "liveProcessing": [
                {
                    "uuid": str(d.uuid),
                    "name": d.name,
                    "stage": d.stage.value,
                    "progressPct": d.progress_pct,
                    "etaSeconds": d.eta_seconds,
                    "startedAt": d.started_at.isoformat(),
                }
                for d in self.instance.live_processing
            ],
        }
