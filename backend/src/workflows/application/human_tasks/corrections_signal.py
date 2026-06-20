"""Señal ``corrections`` al run pausado en un stage de revisión (E5 · §3.3).

La dispara el use case de verificación por campo (PATCH tenant) y el endpoint
M2M ``POST /v1/cases/{id}/corrections`` tras persistir. Best-effort ESTRICTO
(patrón ``CaseReadySignalError``): la señal ES el re-analyze antes de aprobar;
si falla, el caller recibe 503 y reintenta (la verificación ya persistida es
idempotente vía dedupe de case_events).

Payload corto SIEMPRE (límite 2 MiB de Temporal): refs de campo, jamás valores.
"""

from __future__ import annotations

from typing import Any

from temporalio.client import Client as TemporalClient

from src.common.application.logging import get_logger
from src.common.domain.exceptions._base import DomainError

logger = get_logger(__name__)

CORRECTIONS_SIGNAL = "corrections"


class CorrectionsSignalError(DomainError):
    def __init__(self, pipeline_run_id: str):
        super().__init__(
            code="case.corrections_signal_failed",
            message=(
                "The correction was recorded but the review run could not be "
                "notified. Retry shortly."
            ),
            status_code=503,
            context={"pipeline_run_id": pipeline_run_id},
        )


async def signal_corrections(
    temporal_client: TemporalClient,
    pipeline_run_id: str,
    task_key: str,
    fields: list[dict[str, Any]],
) -> None:
    """Señala ``corrections`` al run; falla ⇒ 503 (el caller reintenta)."""
    try:
        handle = temporal_client.get_workflow_handle(pipeline_run_id)
        # Señal multi-arg: SIEMPRE via args=[...] (gotcha temporalio vigente).
        await handle.signal(CORRECTIONS_SIGNAL, args=[task_key, {"fields": fields}])
    except Exception as exc:
        logger.warning(
            "case.corrections_signal_failed",
            run_id=pipeline_run_id,
            task_key=task_key,
            error=f"{type(exc).__name__}: {exc}",
        )
        raise CorrectionsSignalError(pipeline_run_id) from exc
