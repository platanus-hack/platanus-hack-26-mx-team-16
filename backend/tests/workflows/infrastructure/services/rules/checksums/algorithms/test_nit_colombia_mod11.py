"""Unit tests for the Colombian NIT (DIAN mod-11) checksum.

Hand computation with the DIAN primes (left-to-right for a 9-digit body:
41, 37, 29, 23, 19, 17, 13, 7, 3; r = sum % 11; dv = r if r < 2 else 11 - r):

- 800197268 (NIT of DIAN itself):
  8·41+0·37+0·29+1·23+9·19+7·17+2·13+6·7+8·3
  = 328+0+0+23+171+119+26+42+24 = 733; 733 % 11 = 7 → dv = 4
- 890903938 (NIT of Bancolombia):
  8·41+9·37+0·29+9·23+0·19+3·17+9·13+3·7+8·3
  = 328+333+0+207+0+51+117+21+24 = 1081; 1081 % 11 = 3 → dv = 8
- 800197262: 328+0+0+23+171+119+26+42+6 = 715; 715 % 11 = 0 → dv = 0 (r < 2 edge)
"""

import pytest
from expects import be_false, be_true, expect

from src.workflows.infrastructure.services.rules.checksums.algorithms import (
    nit_colombia_mod11,
)


@pytest.mark.parametrize(
    "value",
    [
        "800197268-4",  # DIAN
        "800.197.268-4",  # thousand separators
        "8001972684",  # no hyphen
        "890903938-8",  # Bancolombia
        "800197262-0",  # r = 0 edge → dv = 0
    ],
)
def test_validate__accepts_nit_with_correct_dian_verifier(value):
    expect(nit_colombia_mod11.validate(value)).to(be_true)


@pytest.mark.parametrize(
    "value",
    [
        "800197268-5",  # dv should be 4
        "890903938-9",  # dv should be 8
        "800197262-1",  # dv should be 0
        "80-1",  # body too short
        "800197268-K",  # non-numeric verifier
        "nit-invalido",
        "",
    ],
)
def test_validate__rejects_wrong_verifier_or_malformed(value):
    expect(nit_colombia_mod11.validate(value)).to(be_false)


@pytest.mark.parametrize(
    "value",
    [
        "8.0.0.1.9.7.2.6.8-4",  # separator soup — dots not in thousand groups
        "8001.972.68-4",  # first dot group not a valid thousand boundary
        "800-197268-4",  # two hyphens
    ],
)
def test_validate__rejects_separator_soup(value):
    expect(nit_colombia_mod11.validate(value)).to(be_false)


def test_validate__rejects_non_string_input():
    expect(nit_colombia_mod11.validate(8001972684)).to(be_false)  # type: ignore[arg-type]
    expect(nit_colombia_mod11.validate(None)).to(be_false)  # type: ignore[arg-type]
