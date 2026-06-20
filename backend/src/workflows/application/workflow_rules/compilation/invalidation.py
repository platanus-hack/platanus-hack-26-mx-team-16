"""Pure functions to detect compilation-invalidating edits (spec §10.2).

A rule edit invalidates its current compilation when any of these fields
changes: ``prompt``, ``kind``, ``config.output_shape``, ``scope``,
``knowledge_refs``. Other fields (``name``, ``position``, ``is_active``,
``config.severity`` …) do NOT trigger recompilation (decision #9).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.common.domain.models.processing.workflow_rule import WorkflowRule

_INVALIDATING_CONFIG_KEYS: tuple[str, ...] = ("output_shape",)


def _canonical_dump(value: Any) -> str:
    """Stable JSON serialization (sorted keys, no whitespace)."""
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def _invalidating_config_subset(config: dict[str, Any]) -> dict[str, Any]:
    return {key: config.get(key) for key in _INVALIDATING_CONFIG_KEYS if key in config}


def compilation_input_hash(rule: WorkflowRule) -> str:
    payload = _canonical_dump(
        {
            "prompt": rule.prompt,
            "kind": rule.kind,
            "config": _invalidating_config_subset(rule.config or {}),
            "scope": rule.scope or {},
            "knowledge_refs": sorted(str(k) for k in (rule.knowledge_refs or [])),
        }
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_invalidating_change(old: WorkflowRule, new: WorkflowRule) -> bool:
    """True if the new rule's invalidating-input hash differs from the old one."""
    return compilation_input_hash(old) != compilation_input_hash(new)
