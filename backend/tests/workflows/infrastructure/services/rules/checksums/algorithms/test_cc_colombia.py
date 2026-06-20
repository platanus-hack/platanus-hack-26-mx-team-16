"""Unit tests for the Colombian CC (cédula de ciudadanía) *format* validation.

The Colombian cédula has no public verifier digit; the algorithm validates
format only: 6-10 digits (dots/spaces tolerated as separators).
"""

import pytest
from expects import be_false, be_true, expect

from src.workflows.infrastructure.services.rules.checksums.algorithms import cc_colombia


@pytest.mark.parametrize(
    "value",
    [
        "123456",  # 6 digits (minimum)
        "79456123",  # legacy 8-digit cédula
        "1020713756",  # 10-digit NUIP
        "1.020.713.756",  # dots tolerated
        " 79456123 ",  # surrounding whitespace tolerated
    ],
)
def test_validate__accepts_well_formed_cc(value):
    expect(cc_colombia.validate(value)).to(be_true)


@pytest.mark.parametrize(
    "value",
    [
        "12345",  # too short (5 digits)
        "12345678901",  # too long (11 digits)
        "12A45678",  # letters
        "79.456-123",  # hyphen is not a tolerated separator
        "",
        "   ",
    ],
)
def test_validate__rejects_malformed_cc(value):
    expect(cc_colombia.validate(value)).to(be_false)


def test_validate__rejects_non_string_input():
    expect(cc_colombia.validate(1020713756)).to(be_false)  # type: ignore[arg-type]
    expect(cc_colombia.validate(None)).to(be_false)  # type: ignore[arg-type]
