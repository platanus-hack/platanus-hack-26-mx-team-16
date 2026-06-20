"""Vector tests for the Chilean RUT mod-11 checksum."""

import pytest
from expects import be_false, be_true, expect

from src.workflows.infrastructure.services.rules.checksums.algorithms.rut_chile_mod11 import (
    validate,
)


@pytest.mark.parametrize(
    "value",
    [
        "12.345.678-5",
        "12345678-5",
        "11.111.111-1",
        "22.222.222-2",
        "6-K",
        "6-k",
    ],
)
def test_validate__accepts_known_valid_ruts(value):
    expect(validate(value)).to(be_true)


@pytest.mark.parametrize(
    "value",
    [
        "12.345.678-9",
        "11.111.111-2",
        "6-0",
        "not-a-rut",
        "",
        "12.345.678-",
    ],
)
def test_validate__rejects_invalid_ruts(value):
    expect(validate(value)).to(be_false)


def test_validate__rejects_non_string_inputs():
    expect(validate(None)).to(be_false)  # type: ignore[arg-type]
