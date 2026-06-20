"""Aggregate report for a workflow bundle import (E6 · W4).

Mirrors the rules importer report shape (counts + ``unresolved_*``) but nests a
section per bundle part so the FE preview can render an honest per-section
summary. v1 is NOT all-or-nothing: each section commits independently, so the
report tells the caller exactly what landed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowBundleImportReport:
    dry_run: bool = False
    # Doc-types
    doc_types_created: int = 0
    doc_types_overwritten: int = 0
    doc_types_skipped: int = 0
    doc_types_failed: int = 0
    # Pipeline
    pipeline_slug: str | None = None
    pipeline_version: int | None = None
    pipeline_created: bool = False
    pipeline_bound: bool = False
    # Rules (espejo del reporte del importer de reglas)
    rules_created: int = 0
    rules_overwritten: int = 0
    rules_skipped: int = 0
    rules_renamed: int = 0
    rules_failed: int = 0
    # Diagnostics
    recompilation_scheduled: int = 0
    unresolved_kb_refs: list[str] = field(default_factory=list)
    unresolved_doc_type_slugs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dryRun": self.dry_run,
            "documentTypes": {
                "created": self.doc_types_created,
                "overwritten": self.doc_types_overwritten,
                "skipped": self.doc_types_skipped,
                "failed": self.doc_types_failed,
            },
            "pipeline": {
                "slug": self.pipeline_slug,
                "version": self.pipeline_version,
                "created": self.pipeline_created,
                "bound": self.pipeline_bound,
            },
            "rules": {
                "created": self.rules_created,
                "overwritten": self.rules_overwritten,
                "skipped": self.rules_skipped,
                "renamed": self.rules_renamed,
                "failed": self.rules_failed,
            },
            "recompilationScheduled": self.recompilation_scheduled,
            "unresolvedKbRefs": self.unresolved_kb_refs,
            "unresolvedDocTypeSlugs": self.unresolved_doc_type_slugs,
            "errors": self.errors,
        }
