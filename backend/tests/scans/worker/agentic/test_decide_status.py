"""Three-state ``agentic_status`` logic (spec §7, plan §7.1) — pure determinism.

no surface ⇒ no_surface; detected + probed ⇒ tested; detected but not probed
(gov passive / probe failure) ⇒ detected_not_tested.
"""

from __future__ import annotations

from expects import equal, expect

from src.common.domain.enums.scans import AgenticStatus
from src.scans.worker.agentic.detector import AgenticSurface
from src.scans.worker.agentic.probe import decide_status


def _surface() -> AgenticSurface:
    return AgenticSurface(
        type="chatbot", vendor="Intercom", location_url="u", confidence="alta"
    )


def test_no_surface_when_empty():
    expect(decide_status([], probed=False)).to(equal(AgenticStatus.NO_SURFACE))
    expect(decide_status([], probed=True)).to(equal(AgenticStatus.NO_SURFACE))


def test_tested_when_detected_and_probed():
    expect(decide_status([_surface()], probed=True)).to(equal(AgenticStatus.TESTED))


def test_detected_not_tested_when_detected_but_not_probed():
    expect(decide_status([_surface()], probed=False)).to(
        equal(AgenticStatus.DETECTED_NOT_TESTED)
    )
