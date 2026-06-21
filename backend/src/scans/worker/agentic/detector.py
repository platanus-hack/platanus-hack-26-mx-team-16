"""Chatbot detection — 2-pass, deterministic first (spec §2, plan §3).

The false negative is worse than the false positive: if detection says "no AI"
when a widget simply hasn't rendered, the whole differentiator is lost. So:

1. **First pass — fingerprints (no LLM):** deterministic match of ~12 versioned
   vendors against ``script src`` hosts, ``window.*`` globals and launcher DOM
   selectors (``match_fingerprints`` — pure Python over the data JSON).
2. **Second pass — LLM classification (only if pass 1 missed):** after the bridge
   resolves the lazy-load (scroll + launcher click + re-snapshot), an LLM
   classifies the enriched snapshot. The LLM client is **lazy-imported** so this
   module loads on CI; tests inject a fake ``classifier``.
3. **Hard false-negative rule:** if nothing matched but there is a
   "pregúntame"/"ask AI" ``<textarea>``/input, emit a low-confidence generic
   ``prompt_input`` surface — never an empty list "because it didn't render".

``AgenticSurface`` is an internal dataclass of the worker package — NOT the
``AgenticResult``/``AgenticSurface`` *domain* model (06). Python assembles the
public ``AgenticResult`` from these (see ``probe.py``).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).parent / "data"
_FINGERPRINTS_FILE = _DATA_DIR / "fingerprints.json"

#: Heuristic: a free-text input that invites the user to "ask" something — the
#: low-confidence generic surface the false-negative rule never discards.
_ASK_INPUT_HINTS: tuple[str, ...] = (
    "pregúntame",
    "preguntame",
    "ask ai",
    "ask me",
    "pregunta",
    "escribe tu mensaje",
    "type your message",
    "how can i help",
    "¿en qué puedo ayudarte",
    "en que puedo ayudarte",
    "asistente",
    "chat with",
)

#: Generic launcher selectors used by the bridge when no vendor selector is known.
GENERIC_LAUNCHER_SELECTORS: tuple[str, ...] = (
    "[aria-label*='chat' i]",
    "[aria-label*='asistente' i]",
    "button[class*='chat' i]",
    "button[class*='launcher' i]",
    "div[class*='chat-widget' i]",
    "[data-testid*='chat' i]",
)


@dataclass
class AgenticSurface:
    """Internal detection result — one detected agentic surface (plan §2.1).

    ``confidence`` mirrors the domain ``FindingConfidence`` values
    (``alta``/``media``/``baja``). A vendor fingerprint hit is ``alta``; the
    generic "ask me" input net is ``baja``.
    """

    type: str  # chatbot | prompt_input | search_ai
    vendor: str | None
    location_url: str
    confidence: str  # alta | media | baja
    launcher_selectors: list[str] = field(default_factory=list)
    endpoint: str | None = None
    inferred_model: str | None = None


@dataclass
class VendorFingerprint:
    vendor: str
    script_hosts: list[str]
    window_globals: list[str]
    launcher_selectors: list[str]


@lru_cache(maxsize=1)
def load_fingerprints() -> list[VendorFingerprint]:
    """Load + validate the versioned vendor fingerprint table (cached)."""
    raw = json.loads(_FINGERPRINTS_FILE.read_text(encoding="utf-8"))
    out: list[VendorFingerprint] = []
    for entry in raw["vendors"]:
        out.append(
            VendorFingerprint(
                vendor=entry["vendor"],
                script_hosts=list(entry.get("script_hosts", [])),
                window_globals=list(entry.get("window_globals", [])),
                launcher_selectors=list(entry.get("launcher_selectors", [])),
            )
        )
    return out


def _network_hosts(network: list[Any] | None) -> list[str]:
    """Best-effort extraction of request URLs/hosts from a captured-network list.

    Each item may be a string URL, a mapping with ``url``/``host``, or an object
    exposing ``.url`` — tolerant so the detector works against whatever the crawl
    (04/05) hands over without coupling to a concrete request type.
    """
    hosts: list[str] = []
    for item in network or []:
        if isinstance(item, str):
            hosts.append(item)
        elif isinstance(item, dict):
            value = item.get("url") or item.get("host")
            if value:
                hosts.append(str(value))
        else:
            value = getattr(item, "url", None) or getattr(item, "host", None)
            if value:
                hosts.append(str(value))
    return hosts


def match_fingerprints(
    dom: str,
    network: list[Any] | None,
    *,
    window_globals: list[str] | None = None,
    location_url: str = "",
) -> list[AgenticSurface]:
    """First pass — deterministic vendor match (no LLM), spec §2.1.

    Signals per vendor: (a) ``script src``/host in the DOM HTML or captured
    network, (b) ``window.*`` globals (``window_globals`` from ``page.evaluate``),
    (c) launcher selectors present in the DOM. Any signal type ⇒ a high-confidence
    ``chatbot`` surface. Returns one surface per matched vendor; ``[]`` if none.
    """
    dom_l = (dom or "").lower()
    hosts = [h.lower() for h in _network_hosts(network)]
    globals_present = {g for g in (window_globals or [])}

    surfaces: list[AgenticSurface] = []
    for fp in load_fingerprints():
        hit_host = any(
            host.lower() in dom_l or any(host.lower() in h for h in hosts)
            for host in fp.script_hosts
        )
        hit_global = any(g in globals_present for g in fp.window_globals)
        hit_selector = any(sel.lower() in dom_l for sel in fp.launcher_selectors)
        if hit_host or hit_global or hit_selector:
            surfaces.append(
                AgenticSurface(
                    type="chatbot",
                    vendor=fp.vendor,
                    location_url=location_url,
                    confidence="alta",
                    launcher_selectors=list(fp.launcher_selectors),
                )
            )
    return surfaces


def _has_ask_input(dom: str) -> bool:
    """True if the DOM has a free-text input that invites the user to ask (spec §2.2)."""
    dom_l = (dom or "").lower()
    if "<textarea" not in dom_l and "type=\"text\"" not in dom_l and "type='text'" not in dom_l:
        # No obvious free-text input at all.
        if "contenteditable" not in dom_l:
            return False
    return any(hint in dom_l for hint in _ASK_INPUT_HINTS)


def _generic_surface(dom: str, location_url: str) -> AgenticSurface | None:
    """The false-negative safety net: low-confidence generic prompt input (spec §2.2)."""
    if _has_ask_input(dom):
        return AgenticSurface(
            type="prompt_input",
            vendor=None,
            location_url=location_url,
            confidence="baja",
            launcher_selectors=list(GENERIC_LAUNCHER_SELECTORS),
        )
    return None


async def detect_surface(
    dom: str,
    network: list[Any] | None,
    *,
    window_globals: list[str] | None = None,
    location_url: str = "",
    classifier: Any | None = None,
) -> list[AgenticSurface]:
    """2-pass detection (spec §2, plan §3). Never returns ``[]`` "because lazy".

    - Pass 1: ``match_fingerprints`` — if it hits, return immediately (the LLM is
      **not** invoked, spec §2.2).
    - Pass 2: if pass 1 missed and a ``classifier`` is provided, classify the
      enriched snapshot. ``classifier`` is an async callable
      ``(dom) -> ClassifyResult``-like object exposing ``is_agentic``/``type``/
      ``vendor``/``confidence`` (lazy LLM; injected/faked in tests).
    - Fallback: the generic "ask me" input net (low confidence). Only after that
      yields nothing does detection return ``[]``.
    """
    surfaces = match_fingerprints(
        dom, network, window_globals=window_globals, location_url=location_url
    )
    if surfaces:
        return surfaces

    if classifier is not None:
        result = await classifier(dom)
        if getattr(result, "is_agentic", False):
            return [
                AgenticSurface(
                    type=getattr(result, "type", "chatbot") or "chatbot",
                    vendor=getattr(result, "vendor", None),
                    location_url=location_url,
                    confidence=getattr(result, "confidence", "media") or "media",
                    launcher_selectors=list(GENERIC_LAUNCHER_SELECTORS),
                )
            ]

    generic = _generic_surface(dom, location_url)
    return [generic] if generic is not None else []
