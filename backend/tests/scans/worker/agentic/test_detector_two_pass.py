"""2-pass detection + the hard false-negative rule (spec §2.2, plan §3.2/§3.3).

- Pass 1 hits ⇒ the LLM classifier is NEVER invoked.
- Pass 1 misses + a classifier is given ⇒ the LLM classifies the enriched snapshot.
- No vendor but an "ask me" input ⇒ a low-confidence ``prompt_input`` surface,
  NEVER ``[]`` "because it didn't render".
"""

from __future__ import annotations

from dataclasses import dataclass

from expects import be_empty, equal, expect, have_len

from src.scans.worker.agentic.detector import detect_surface


@dataclass
class _FakeClassify:
    is_agentic: bool
    type: str = "chatbot"
    vendor: str | None = None
    confidence: str = "media"


class _SpyClassifier:
    def __init__(self, result: _FakeClassify):
        self.result = result
        self.calls = 0

    async def __call__(self, dom: str) -> _FakeClassify:
        self.calls += 1
        return self.result


async def test_pass1_hit_skips_llm_classifier():
    spy = _SpyClassifier(_FakeClassify(is_agentic=True))
    dom = '<script src="https://js.intercomcdn.com/x.js"></script>'
    surfaces = await detect_surface(dom, network=None, classifier=spy)
    expect(spy.calls).to(equal(0))  # pass 1 matched ⇒ LLM not invoked
    expect([s.vendor for s in surfaces]).to(equal(["Intercom"]))


async def test_pass1_miss_invokes_llm_classifier():
    spy = _SpyClassifier(_FakeClassify(is_agentic=True, vendor="MysteryBot"))
    dom = "<html><body>nothing special</body></html>"
    surfaces = await detect_surface(dom, network=None, classifier=spy)
    expect(spy.calls).to(equal(1))
    expect(surfaces).to(have_len(1))
    expect(surfaces[0].vendor).to(equal("MysteryBot"))


async def test_llm_says_not_agentic_falls_through_to_generic_net():
    spy = _SpyClassifier(_FakeClassify(is_agentic=False))
    dom = "<html><body><textarea placeholder='Pregúntame algo'></textarea></body></html>"
    surfaces = await detect_surface(dom, network=None, classifier=spy)
    # LLM said no, but the ask-input net still catches it as low-confidence.
    expect(surfaces).to(have_len(1))
    expect(surfaces[0].type).to(equal("prompt_input"))
    expect(surfaces[0].confidence).to(equal("baja"))


async def test_false_negative_net_never_discards_ask_input():
    dom = "<textarea placeholder='Type your message'></textarea>"
    surfaces = await detect_surface(dom, network=None)  # no classifier
    expect(surfaces).to(have_len(1))
    expect(surfaces[0].type).to(equal("prompt_input"))
    expect(surfaces[0].vendor).to(equal(None))


async def test_truly_empty_dom_returns_empty():
    surfaces = await detect_surface("<html><body>solo texto</body></html>", network=None)
    expect(surfaces).to(be_empty)
