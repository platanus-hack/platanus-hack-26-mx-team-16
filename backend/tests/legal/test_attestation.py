"""Attestation-gate invariant (01-legal §2.1) — pure domain.

Invariant: an active (intrusive) scan can NEVER be enqueued without an explicit
``authorized=true``; a passive scan never requires attestation.
"""

from __future__ import annotations

import pytest
from expects import be_none, equal, expect, raise_error

from src.common.domain.enums.scans import ScanLevel
from src.common.domain.legal.attestation_gate import enforce_attestation
from src.common.domain.legal.exceptions import AttestationRequiredError


@pytest.mark.parametrize("level", [ScanLevel.INTERMEDIO, ScanLevel.AVANZADO])
def test_active_without_authorization_raises(level: ScanLevel) -> None:
    expect(lambda: enforce_attestation(level=level, authorized=False)).to(
        raise_error(AttestationRequiredError)
    )


@pytest.mark.parametrize("level", [ScanLevel.INTERMEDIO, ScanLevel.AVANZADO])
def test_active_with_authorization_passes(level: ScanLevel) -> None:
    expect(enforce_attestation(level=level, authorized=True)).to(be_none)


@pytest.mark.parametrize("authorized", [True, False])
def test_passive_never_requires_attestation(authorized: bool) -> None:
    # Basic (passive) passes regardless of the attestation flag.
    expect(enforce_attestation(level=ScanLevel.BASICO, authorized=authorized)).to(
        be_none
    )


def test_attestation_error_is_422() -> None:
    error = AttestationRequiredError()
    expect(error.status_code).to(equal(422))
    expect(error.code).to(equal("attestation_required"))
