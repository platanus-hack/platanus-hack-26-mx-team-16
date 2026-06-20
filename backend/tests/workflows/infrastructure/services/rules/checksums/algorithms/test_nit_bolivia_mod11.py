"""Unit tests for the Bolivian NIT mod-11 checksum.

Verifier digits below are computed by hand with the documented algorithm
(weights 2..9 cycling right-to-left over the body; dv = 11 - (sum % 11);
11 → 0, 10 → 1):

- body 123456789 → 9·2+8·3+7·4+6·5+5·6+4·7+3·8+2·9+1·2
                 = 18+24+28+30+30+28+24+18+2 = 202; 202 % 11 = 4 → dv = 7
- body 2030988   → 8·2+8·3+9·4+0·5+3·6+0·7+2·8
                 = 16+24+36+0+18+0+16 = 110; 110 % 11 = 0 → 11 → dv = 0
- body 1009      → 9·2+0·3+0·4+1·5 = 23; 23 % 11 = 1 → 10 → dv = 1
"""

import pytest
from expects import be_false, be_true, expect

from src.workflows.infrastructure.services.rules.checksums.algorithms import (
    nit_bolivia_mod11,
)


@pytest.mark.parametrize(
    "value",
    [
        "1234567897",  # body 123456789, dv 7
        "123456789-7",  # hyphen before the dv
        "123.456.789-7",  # thousand separators
        "20309880",  # body 2030988, dv 0 (remainder 11 → 0 edge)
        "10091",  # body 1009, dv 1 (remainder 10 → 1 edge)
    ],
)
def test_validate__accepts_nit_with_correct_verifier(value):
    expect(nit_bolivia_mod11.validate(value)).to(be_true)


@pytest.mark.parametrize(
    "value",
    [
        "1234567890",  # dv should be 7
        "1234567891",
        "20309881",  # dv should be 0
        "10090",  # dv should be 1
        "123",  # too short to carry body + dv
        "12345678-A",  # non-numeric verifier
        "no-es-un-nit",
        "",
    ],
)
def test_validate__rejects_wrong_verifier_or_malformed(value):
    expect(nit_bolivia_mod11.validate(value)).to(be_false)


@pytest.mark.parametrize(
    "value",
    [
        "1.2.3.4.5.6.7.8.9-7",  # separator soup — dots not in thousand groups
        "1234.567.89-7",  # first dot group not a valid thousand boundary
        "12-3456789-7",  # two hyphens
        "123456789--7",  # doubled hyphen
    ],
)
def test_validate__rejects_separator_soup(value):
    # These previously stripped to a clean `1234567897` and PASSed (~10% false
    # positives from separator ambiguity). They must now be rejected.
    expect(nit_bolivia_mod11.validate(value)).to(be_false)


def test_validate__rejects_non_string_input():
    expect(nit_bolivia_mod11.validate(1234567897)).to(be_false)  # type: ignore[arg-type]
    expect(nit_bolivia_mod11.validate(None)).to(be_false)  # type: ignore[arg-type]
