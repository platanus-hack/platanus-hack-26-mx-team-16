"""Pure metric computation for eval runs (F11 · A5).

``compute_metrics`` is deliberately side-effect free so it can be unit-tested in
isolation and later reused by a Temporal activity that actually executes the
pipeline over the dataset. For now the eval-run endpoint calls it with empty
inputs, yielding ``{"count": 0, "accuracy": 0.0}``.
"""

from __future__ import annotations

from typing import Any


def compute_metrics(cases: list[Any], outputs: list[Any]) -> dict:
    """Aggregate metrics for a single eval run.

    ``cases`` are the golden cases (each carrying an ``expected`` payload);
    ``outputs`` are the corresponding actual pipeline outputs, positionally
    aligned with ``cases``. Accuracy is a simple exact-match ratio over the
    pairs we have outputs for. With no outputs, accuracy is ``0.0``.
    """

    count = len(cases)
    if not outputs:
        return {"count": count, "accuracy": 0.0}

    comparable = min(len(cases), len(outputs))
    if comparable == 0:
        return {"count": count, "accuracy": 0.0}

    matches = 0
    for case, output in zip(cases[:comparable], outputs[:comparable]):
        expected = _expected_of(case)
        if expected == output:
            matches += 1

    return {"count": count, "accuracy": matches / comparable}


def _expected_of(case: Any) -> Any:
    """Extract the expected payload from a case (pydantic model, dict, or raw)."""

    if hasattr(case, "expected"):
        return case.expected
    if isinstance(case, dict):
        return case.get("expected", case)
    return case
