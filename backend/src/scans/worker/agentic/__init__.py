"""Agentic-surface services (03-agentic-surface, plan §1/§2).

The deterministic + I/O machinery behind Owliver's differentiator: detect
embedded chatbots / LLM widgets (``detector``), drive their conversation turn by
turn (``bridge`` — Playwright, lazy-imported), feed them a proprietary payload
bank (``payloads``), and judge each reply per technique (``judge`` — canary regex
is deterministic; the LLM client is lazy-imported and mocked in tests). The
``probe`` module orchestrates detect → probe → judge into one ``AgenticResult``.

Public, import-clean-on-CI surface (no agno/anthropic/playwright at import time):

- ``detector.match_fingerprints`` / ``detect_surface`` / ``AgenticSurface``
- ``payloads.load_payloads`` / ``Payload`` / ``inject_canary``
- ``judge.judge_response`` / ``Verdict`` / ``verdict_to_finding`` / ``TECHNIQUE_CATEGORY``
- ``probe.agentic_probe`` (the 03 implementation of the 05 seam)
- ``probe.decide_status``
- ``inferred_model.infer_model``
"""

from __future__ import annotations

from src.scans.worker.agentic.detector import (
    AgenticSurface,
    detect_surface,
    match_fingerprints,
)
from src.scans.worker.agentic.judge import (
    TECHNIQUE_CATEGORY,
    Verdict,
    judge_response,
    verdict_to_finding,
)
from src.scans.worker.agentic.payloads import Payload, inject_canary, load_payloads
from src.scans.worker.agentic.probe import agentic_probe, decide_status

__all__ = [
    "TECHNIQUE_CATEGORY",
    "AgenticSurface",
    "Payload",
    "Verdict",
    "agentic_probe",
    "decide_status",
    "detect_surface",
    "inject_canary",
    "judge_response",
    "load_payloads",
    "match_fingerprints",
    "verdict_to_finding",
]
