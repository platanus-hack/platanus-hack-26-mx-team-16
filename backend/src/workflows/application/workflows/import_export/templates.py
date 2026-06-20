"""Workflow templates catalog (E6 · W4 · diseño §4.4).

Templates are static bundle envelopes (schemaVersion 1.0) living in
``backend/fixtures/templates/*.json`` — git-able by definition, no DB table.
``GET /v1/workflow-templates`` reads the directory and returns metadata + the
full envelope so the FE can render cards and pipe the envelope straight into the
bundle importer ("create workflow from template" = create + import).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.common.application.logging import get_logger

logger = get_logger(__name__)

# backend/src/workflows/application/workflows/import_export/templates.py
#  → parents[5] == backend/
TEMPLATES_DIR = Path(__file__).resolve().parents[5] / "fixtures" / "templates"


@dataclass
class WorkflowTemplatesLister:
    """List the static template envelopes. Pure FS read; tenant-auth at router."""

    templates_dir: Path = TEMPLATES_DIR

    def execute(self) -> list[dict[str, Any]]:
        if not self.templates_dir.is_dir():
            return []
        templates: list[dict[str, Any]] = []
        for path in sorted(self.templates_dir.glob("*.json")):
            try:
                envelope = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                logger.exception("workflow_template.read_failed", path=str(path))
                continue
            workflow = envelope.get("workflow") or {}
            templates.append(
                {
                    "slug": envelope.get("slug") or path.stem,
                    "name": envelope.get("name") or workflow.get("name") or path.stem,
                    "description": envelope.get("description"),
                    "industry": envelope.get("industry"),
                    "envelope": envelope,
                }
            )
        return templates
