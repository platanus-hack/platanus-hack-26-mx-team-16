"""Payload bank cap + level filtering (spec §1/§3.4, plan §5).

``basico`` ⇒ ``[]``; ``intermedio`` ≤ 8; ``avanzado`` ≤ 20; cumulative
``min_level`` filtering; truncation if the JSON exceeds the cap; the canary token
substitution makes the leak deterministic.
"""

from __future__ import annotations

from expects import be_empty, contain, equal, expect

from src.scans.worker.agentic import payloads as payloads_mod
from src.scans.worker.agentic.payloads import (
    CANARY_PLACEHOLDER,
    inject_canary,
    load_payloads,
    new_canary_token,
)


def test_basico_returns_no_payloads():
    expect(load_payloads("basico")).to(be_empty)


def test_intermedio_capped_at_eight():
    out = load_payloads("intermedio")
    expect(len(out) <= 8).to(equal(True))
    # intermedio must NOT include avanzado-only payloads.
    levels = {p.min_level for p in out}
    expect("avanzado" in levels).to(equal(False))


def test_avanzado_capped_at_twenty_and_includes_intermedio():
    out = load_payloads("avanzado")
    expect(len(out) <= 20).to(equal(True))
    levels = {p.min_level for p in out}
    # cumulative: avanzado sees intermedio payloads too.
    expect(levels).to(contain("intermedio"))


def test_cap_truncates_when_json_exceeds_cap(monkeypatch):
    big = [
        payloads_mod.Payload(id=f"p{i}", technique="jailbreak", min_level="intermedio", text="x")
        for i in range(50)
    ]
    monkeypatch.setattr(payloads_mod, "_raw_payloads", lambda: big)
    monkeypatch.setattr(payloads_mod, "_cap_for", lambda level: 8)
    out = payloads_mod.load_payloads("intermedio")
    expect(len(out)).to(equal(8))


def test_canary_substitution_records_token():
    canary = next(p for p in load_payloads("intermedio") if p.technique == "canary")
    expect(CANARY_PLACEHOLDER in canary.text).to(equal(True))
    token = new_canary_token()
    bound = inject_canary(canary, token)
    expect(CANARY_PLACEHOLDER in bound.text).to(equal(False))
    expect(token in bound.text).to(equal(True))
    expect(bound.canary_token).to(equal(token))


def test_unique_canary_tokens_per_call():
    expect(new_canary_token() == new_canary_token()).to(equal(False))


def test_non_canary_payload_passes_through_without_token():
    jb = next(p for p in load_payloads("intermedio") if p.technique == "jailbreak")
    bound = inject_canary(jb, new_canary_token())
    expect(bound.canary_token).to(equal(None))
