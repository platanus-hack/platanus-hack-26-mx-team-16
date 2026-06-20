"""select_rules_in_set — subconjunto nombrado de reglas (phases-config · H2).

``analyze.rule_set`` es un tag declarado en ``rule.config.rule_sets`` (lista de
strings, sin entidad nueva). ``None``/vacío ⇒ todas las reglas (comportamiento de
hoy). Extraído a función de módulo para testearlo sin harness de BD.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from expects import be, contain_exactly, equal, expect

from src.workflows.presentation.workflows.activities.analysis_run_activities import (
    select_rules_in_set,
)


def _rule(name, rule_sets=None):
    config = {} if rule_sets is None else {"rule_sets": rule_sets}
    return SimpleNamespace(name=name, config=config)


@pytest.mark.parametrize("rule_set", [None, ""])
def test_select__empty_rule_set_returns_same_list(rule_set):
    rules = [_rule("a"), _rule("b", ["x"])]

    result = select_rules_in_set(rules, rule_set)

    expect(result).to(be(rules))


def test_select__filters_to_tagged_rules():
    a = _rule("a", ["x", "y"])
    b = _rule("b", ["y"])
    c = _rule("c", ["x"])

    result = select_rules_in_set([a, b, c], "x")

    expect(result).to(contain_exactly(a, c))


def test_select__excludes_untagged_and_null_config_rules():
    tagged = _rule("a", ["billing"])
    untagged = _rule("b")
    null_config = SimpleNamespace(name="c", config=None)

    result = select_rules_in_set([tagged, untagged, null_config], "billing")

    expect(result).to(contain_exactly(tagged))


def test_select__no_match_returns_empty():
    result = select_rules_in_set([_rule("a", ["x"])], "zzz")

    expect(result).to(equal([]))


def test_select__scalar_rule_sets_tag_does_not_substring_match():
    # config['rule_sets']='billing' (escalar, no lista) NO debe degradar a match
    # por substring ('bill'); se coacciona a [] ⇒ la regla queda fuera.
    scalar = SimpleNamespace(name="a", config={"rule_sets": "billing"})

    expect(select_rules_in_set([scalar], "bill")).to(equal([]))
    expect(select_rules_in_set([scalar], "billing")).to(equal([]))
