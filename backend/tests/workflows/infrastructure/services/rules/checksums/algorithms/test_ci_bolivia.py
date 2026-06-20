"""Unit tests for the Bolivian CI *format* validation.

The Bolivian CI has no public verifier digit, so the algorithm only
validates the format: 5-8 digits + optional departmental extension
(LP/CB/SC/OR/PT/TJ/CH/BE/PD).
"""

import pytest
from expects import be_false, be_true, expect

from src.workflows.infrastructure.services.rules.checksums.algorithms import ci_bolivia


@pytest.mark.parametrize(
    "value",
    [
        "12345",  # 5 digits (minimum)
        "12345678",  # 8 digits (maximum)
        "1234567",
        "1234567 LP",  # departmental extension, space-separated
        "1234567-SC",  # hyphen-separated
        "1234567CB",  # glued
        "1234567 lp",  # case-insensitive extension
        "1.234.567",  # dots tolerated
        "12345678 PD",
    ],
)
def test_validate__accepts_well_formed_ci(value):
    expect(ci_bolivia.validate(value)).to(be_true)


@pytest.mark.parametrize(
    "value",
    [
        "1234",  # too short (4 digits)
        "123456789",  # too long (9 digits)
        "1234567-XX",  # not a department code
        "1234567 LPZ",
        "ABC4567",
        "",
        "  ",
    ],
)
def test_validate__rejects_malformed_ci(value):
    expect(ci_bolivia.validate(value)).to(be_false)


def test_validate__rejects_non_string_input():
    expect(ci_bolivia.validate(1234567)).to(be_false)  # type: ignore[arg-type]
    expect(ci_bolivia.validate(None)).to(be_false)  # type: ignore[arg-type]
