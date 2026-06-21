"""LLM-judge rubric path + finding assembly (spec §5.1, plan §6/§6.1).

system-prompt-leak / jailbreak use ``response_model=Verdict`` via an injected fake
model; ``pass_=True`` ⇒ a ``Finding`` with the right OWASP-LLM category and
``confidence=media``; the technique→category map is a static dict (never the LLM);
Python owns ``technique``/``confidence`` regardless of what the LLM returns.
"""

from __future__ import annotations

from expects import equal, expect

from src.scans.worker.agentic.judge import (
    TECHNIQUE_CATEGORY,
    Verdict,
    judge_response,
    verdict_to_finding,
)
from src.scans.worker.agentic.payloads import Payload


class _FakeModel:
    """Stands in for the lazy Claude judge — returns a fixed Verdict."""

    def __init__(self, verdict: Verdict):
        self._verdict = verdict
        self.calls = 0

    def judge(self, payload: Payload, reply: str) -> Verdict:
        self.calls += 1
        return self._verdict


def _spl_payload() -> Payload:
    return Payload(id="spl-01", technique="system_prompt_leak", min_level="intermedio", text="leak")


def _jb_payload() -> Payload:
    return Payload(id="jb-01", technique="jailbreak", min_level="intermedio", text="jb")


def test_system_prompt_leak_uses_llm_and_maps_to_llm07():
    model = _FakeModel(Verdict(pass_=True, severity="high", reason="reveló reglas"))
    verdict = judge_response(_spl_payload(), "Mis reglas son...", model=model)
    expect(model.calls).to(equal(1))
    expect(verdict.pass_).to(equal(True))
    expect(verdict.confidence).to(equal("media"))  # Python forces media for LLM verdicts
    finding = verdict_to_finding(_spl_payload(), "Mis reglas son...", verdict, location_url="u")
    expect(finding.category).to(equal("LLM07"))
    expect(finding.confidence).to(equal("media"))


def test_jailbreak_maps_to_llm01():
    model = _FakeModel(Verdict(pass_=True, severity="medium", reason="cumplió fuera de dominio"))
    verdict = judge_response(_jb_payload(), "Aquí está el phishing...", model=model)
    finding = verdict_to_finding(_jb_payload(), "Aquí está el phishing...", verdict, location_url="u")
    expect(finding.category).to(equal("LLM01"))


def test_technique_category_is_a_static_dict():
    expect(TECHNIQUE_CATEGORY["canary"]).to(equal("LLM01"))
    expect(TECHNIQUE_CATEGORY["jailbreak"]).to(equal("LLM01"))
    expect(TECHNIQUE_CATEGORY["system_prompt_leak"]).to(equal("LLM07"))


def test_no_model_yields_non_leak_verdict():
    verdict = judge_response(_spl_payload(), "respuesta", model=None)
    expect(verdict.pass_).to(equal(False))
    expect(verdict.severity).to(equal("info"))


def test_verdict_alias_pass_round_trips():
    # The wire/LLM uses `pass`; Python uses `pass_`.
    v = Verdict.model_validate({"pass": True, "severity": "high", "reason": "x"})
    expect(v.pass_).to(equal(True))
    dumped = v.model_dump(by_alias=True)
    expect(dumped["pass"]).to(equal(True))
