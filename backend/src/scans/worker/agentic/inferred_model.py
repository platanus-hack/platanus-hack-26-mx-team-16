"""``infer_model`` — best-effort, NOT reliable (spec §6, plan §7.2).

Unless the JS calls a provider host directly (rare) or the bot delates its own
model under a direct probe, the model behind a chatbot is **indeterminable** from
outside. Guessing "GPT-4" wrong on the differentiator screen damages credibility,
so ``inferred_model`` is filled **only on hard signal**:

  (a) a fetch to a known provider host (``api.openai.com`` / ``api.anthropic.com``)
      observed in the crawl, or
  (b) the bot naming its own model in a probe reply.

In every other case → ``None`` → the report shows "modelo no expuesto (buena
práctica)". No writing-style fingerprinting (that is the unreliable guess we
refuse to make).
"""

from __future__ import annotations

import re
from typing import Any

#: Provider hosts whose presence in the crawl is a hard signal of the backend.
_PROVIDER_HOSTS: dict[str, str] = {
    "api.openai.com": "OpenAI (modelo no especificado)",
    "api.anthropic.com": "Anthropic Claude (modelo no especificado)",
    "generativelanguage.googleapis.com": "Google Gemini (modelo no especificado)",
    "api.cohere.ai": "Cohere (modelo no especificado)",
    "api.mistral.ai": "Mistral (modelo no especificado)",
}

#: Model families a bot might name about itself in a reply (hard self-disclosure).
_SELF_DISCLOSURE = re.compile(
    r"\b(gpt-4[\w.-]*|gpt-3\.5[\w.-]*|gpt-5[\w.-]*|claude[\w. -]*|"
    r"gemini[\w.-]*|llama[\w.-]*|mistral[\w.-]*)\b",
    re.IGNORECASE,
)


def _network_urls(network: list[Any] | None) -> list[str]:
    urls: list[str] = []
    for item in network or []:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict):
            value = item.get("url") or item.get("host")
            if value:
                urls.append(str(value))
        else:
            value = getattr(item, "url", None) or getattr(item, "host", None)
            if value:
                urls.append(str(value))
    return urls


def infer_model(
    network: list[Any] | None = None,
    probe_reply: str | None = None,
) -> str | None:
    """Return an inferred model string only on hard signal, else ``None``.

    Hard signals (spec §6): a provider host in the crawl, or the bot naming its
    own model in ``probe_reply``. Never guesses by writing style.
    """
    for url in _network_urls(network):
        low = url.lower()
        for host, label in _PROVIDER_HOSTS.items():
            if host in low:
                return label

    if probe_reply:
        match = _SELF_DISCLOSURE.search(probe_reply)
        if match:
            return match.group(0)

    return None
