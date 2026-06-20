"""Unit tests for the checksum algorithm `registry` module."""

import pytest
from expects import be_false, be_true, equal, expect, raise_error

from src.workflows.infrastructure.services.rules.bootstrap import (
    register_default_checksums,
)
from src.workflows.infrastructure.services.rules.checksums import registry


@pytest.fixture(autouse=True)
def _isolated_registry():
    registry.clear()
    yield
    registry.clear()
    register_default_checksums()


def test_register__adds_algorithm_callable():
    registry.register("always_true", lambda value: True)

    fn = registry.get("always_true")
    expect(fn("anything")).to(be_true)


def test_get__raises_on_unknown_algorithm():
    expect(lambda: registry.get("does_not_exist")).to(raise_error(KeyError))


def test_get__error_lists_known_algorithms_for_diagnostics():
    registry.register("a", lambda v: True)
    registry.register("b", lambda v: True)

    try:
        registry.get("missing")
    except KeyError as exc:
        message = str(exc)
        expect("'a'" in message or '"a"' in message).to(equal(True))
        expect("'b'" in message or '"b"' in message).to(equal(True))


def test_known__returns_set_of_registered_names():
    registry.register("alpha", lambda v: True)
    registry.register("beta", lambda v: True)

    expect(registry.known()).to(equal({"alpha", "beta"}))


def test_clear__empties_registry():
    registry.register("temp", lambda v: True)

    registry.clear()

    expect(registry.known()).to(equal(set()))


def test_register__overwrites_existing_algorithm():
    registry.register("dup", lambda value: True)
    registry.register("dup", lambda value: False)

    expect(registry.get("dup")("x")).to(be_false)


def test_default_checksums__are_registered_after_bootstrap():
    register_default_checksums()

    for name in (
        "rut_chile_mod11",
        "luhn_credit_card",
        "iso_iban_mod97",
        # E5 · multi-país BO+CO
        "nit_bolivia_mod11",
        "ci_bolivia",
        "nit_colombia_mod11",
        "cc_colombia",
    ):
        expect(name in registry.known()).to(equal(True))
