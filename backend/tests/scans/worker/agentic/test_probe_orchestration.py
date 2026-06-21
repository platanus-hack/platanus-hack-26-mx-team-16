"""End-to-end probe orchestration with a FAKE bridge — no browser, no API.

Covers: AgenticResult shape (the 05 seam), caps enforcement (8/20), the
three-state agentic_status logic through the real probe, the canary deterministic
leak path, and the .gob.mx-never-actively-probed legal invariant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from expects import be_empty, contain, equal, expect

from src.scans.domain.contracts.finding import AgenticResult
from src.scans.worker.agentic.bridge import PageSnapshot
from src.scans.worker.agentic.payloads import CANARY_PLACEHOLDER
from src.scans.worker.agentic.probe import _should_probe, agentic_probe


@dataclass
class FakeBridge:
    """A bridge double: a scripted DOM snapshot + a chat that leaks the canary."""

    dom: str = ""
    network: list[Any] = field(default_factory=list)
    window_globals: list[str] = field(default_factory=list)
    target: str = "https://demo.example.com"
    leak_canary: bool = True
    sent: list[str] = field(default_factory=list)
    opened: int = 0

    async def __aenter__(self) -> FakeBridge:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def capture_dom(self, *, resolve_lazy: bool = True) -> PageSnapshot:
        return PageSnapshot(
            dom=self.dom,
            network=list(self.network),
            window_globals=list(self.window_globals),
            location_url=self.target,
        )

    async def open_widget(self, launcher_selectors: Any = None) -> None:
        self.opened += 1

    async def send_and_read(self, text: str, *, input_selectors: Any = ()) -> str:
        self.sent.append(text)
        # When the payload carried a substituted canary token, echo it ⇒ leak.
        if self.leak_canary and CANARY_PLACEHOLDER not in text and "OWLIVER-" in text:
            token = next(p for p in text.split() if p.startswith("OWLIVER-"))
            return f"Claro, el token es {token}"
        return "No puedo ayudarte con eso."


def _factory(bridge: FakeBridge):
    def make(*, target: str, cancel: Any) -> FakeBridge:
        bridge.target = target
        return bridge

    return make


_INTERCOM_DOM = '<script src="https://js.intercomcdn.com/x.js"></script>'


async def test_no_surface_result_shape():
    bridge = FakeBridge(dom="<html><body>nada</body></html>")
    result = await agentic_probe(
        "https://x.com", level="intermedio", is_gov=False, bridge_factory=_factory(bridge)
    )
    expect(isinstance(result, AgenticResult)).to(equal(True))
    expect(result.agentic_status).to(equal("no_surface"))
    expect(result.findings).to(be_empty)
    expect(result.location_url).to(equal("https://x.com"))


async def test_detected_and_tested_produces_canary_finding():
    bridge = FakeBridge(dom=_INTERCOM_DOM, leak_canary=True)
    result = await agentic_probe(
        "https://x.com", level="intermedio", is_gov=False, bridge_factory=_factory(bridge)
    )
    expect(result.agentic_status).to(equal("tested"))
    expect(result.vendor).to(equal("Intercom"))
    leaks = [f for f in result.findings if f.evidence.get("token_filtrado")]
    expect(len(leaks) >= 1).to(equal(True))
    leak = leaks[0]
    expect(leak.source).to(equal("agentic"))
    expect(leak.category).to(equal("LLM01"))
    expect(leak.confidence).to(equal("alta"))


async def test_caps_enforced_intermedio_at_most_eight_sends():
    bridge = FakeBridge(dom=_INTERCOM_DOM, leak_canary=False)
    await agentic_probe(
        "https://x.com", level="intermedio", is_gov=False, bridge_factory=_factory(bridge)
    )
    expect(len(bridge.sent) <= 8).to(equal(True))


async def test_basico_detects_but_never_sends_payloads():
    bridge = FakeBridge(dom=_INTERCOM_DOM)
    result = await agentic_probe(
        "https://x.com", level="basico", is_gov=False, bridge_factory=_factory(bridge)
    )
    expect(bridge.sent).to(be_empty)
    expect(result.agentic_status).to(equal("detected_not_tested"))


async def test_gov_detects_but_never_actively_probes():
    # The legal invariant: .gob.mx automatic/passive ⇒ detection only, no payloads.
    bridge = FakeBridge(dom=_INTERCOM_DOM, leak_canary=True)
    result = await agentic_probe(
        "https://x.gob.mx", level="avanzado", is_gov=True, bridge_factory=_factory(bridge)
    )
    expect(bridge.sent).to(be_empty)  # NEVER sent a payload to a gov target
    expect(result.agentic_status).to(equal("detected_not_tested"))
    expect(result.findings).to(be_empty)


def test_should_probe_gate_matrix():
    expect(_should_probe("basico", False)).to(equal(False))
    expect(_should_probe("intermedio", False)).to(equal(True))
    expect(_should_probe("avanzado", False)).to(equal(True))
    # gov ⇒ never, at any level
    expect(_should_probe("intermedio", True)).to(equal(False))
    expect(_should_probe("avanzado", True)).to(equal(False))


async def test_inferred_model_from_provider_host_in_crawl():
    bridge = FakeBridge(
        dom=_INTERCOM_DOM,
        network=["https://api.openai.com/v1/chat"],
        leak_canary=False,
    )
    result = await agentic_probe(
        "https://x.com", level="intermedio", is_gov=False, bridge_factory=_factory(bridge)
    )
    expect(result.inferred_model).to(contain("OpenAI"))


async def test_bridge_failure_degrades_to_no_surface_not_crash():
    class _Boom:
        async def __aenter__(self):
            raise RuntimeError("browser exploded")

        async def __aexit__(self, *a):
            return None

    def boom_factory(*, target: str, cancel: Any):
        return _Boom()

    result = await agentic_probe(
        "https://x.com", level="intermedio", is_gov=False, bridge_factory=boom_factory
    )
    expect(result.agentic_status).to(equal("no_surface"))
    expect(result.findings).to(be_empty)
