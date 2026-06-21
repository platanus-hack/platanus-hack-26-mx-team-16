"""``inferred_model`` — best-effort, hard signal only (spec §6, plan §7.2).

A provider host in the crawl or the bot naming its own model ⇒ a string; no hard
signal ⇒ ``None`` (never guesses by writing style).
"""

from __future__ import annotations

from expects import contain, equal, expect

from src.scans.worker.agentic.inferred_model import infer_model


def test_provider_host_in_network_is_hard_signal():
    out = infer_model(network=["https://api.openai.com/v1/chat"], probe_reply=None)
    expect(out).to(contain("OpenAI"))


def test_anthropic_host_detected():
    out = infer_model(network=[{"url": "https://api.anthropic.com/v1/messages"}])
    expect(out).to(contain("Anthropic"))


def test_self_disclosure_in_reply_is_hard_signal():
    out = infer_model(network=None, probe_reply="Soy un asistente basado en GPT-4o.")
    expect(out.lower()).to(contain("gpt-4"))


def test_no_signal_returns_none():
    out = infer_model(
        network=["https://example.com/app.js"],
        probe_reply="Hola, ¿en qué puedo ayudarte?",
    )
    expect(out).to(equal(None))


def test_does_not_guess_by_style():
    # A flowery reply with no model name and no provider host must stay None.
    out = infer_model(network=[], probe_reply="¡Encantado de ayudarte hoy!")
    expect(out).to(equal(None))
