"""Deterministic input_hash for synthesis cache (synthesis spec §8, §16.6).

Projects only the bits that the synthesizer actually depends on. Specifically
NEVER includes `evaluation_metadata`, `reasoning`, or `rendered_prompt` —
those carry LLM noise that would defeat the cache.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from src.common.domain.enums.run_summary import Verdict
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult


# Bumped whenever the hashed projection changes so old cached summaries don't
# get reused under the new key. v3 (E2): documents are hashed ALWAYS (not only
# when `synthesis_uses_documents`) and the deterministic x-source projection
# (`resolved_fields`) enters the hash too.
_CACHE_VERSION = "v3"


def compute_input_hash(
    *,
    verdict: Verdict,
    rule_results: Iterable[WorkflowRuleResult],
    output_schema: dict[str, Any] | None,
    synthesis_template: str | None,
    model: str | None,
    documents: Iterable[dict[str, Any]] | None = None,
    resolved_fields: dict[str, Any] | None = None,
) -> str:
    """Return a stable 64-char SHA-256 hex digest for the synthesizer inputs.

    A4 golden rule: everything that enters the synthesis prompt enters the hash.
    ``documents`` is the case ``mapped_extraction`` — hashed unconditionally
    since v3 so an extraction change invalidates the cached synthesis even when
    the documents are not injected in the prompt (x-source projection reads
    them either way). ``resolved_fields`` is the deterministic projection
    (json_pointer → value) that overrides the LLM output.
    """
    payload = {
        "cache_version": _CACHE_VERSION,
        "verdict": verdict.value,
        "rule_results": [_project_result(r) for r in rule_results],
        "output_schema": output_schema or {},
        "synthesis_template": synthesis_template or "",
        "model": model or "",
        "documents": list(documents) if documents else [],
        "resolved_fields": resolved_fields or {},
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _project_result(result: WorkflowRuleResult) -> dict[str, Any]:
    """Project a result down to (rule_id, kind, output) only — no metadata."""
    return {
        "rule_id": str(result.rule_id),
        "kind": result.kind,
        "output": result.output,
    }
