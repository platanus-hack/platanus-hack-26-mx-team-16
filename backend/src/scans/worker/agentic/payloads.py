"""Proprietary embedded payload bank + hard cap (spec §3, plan §5).

The demo does NOT depend on the full garak/promptfoo suite: the bank is our own
(canary, ignore-previous, system-prompt-leak, jailbreak). ``load_payloads(level)``
filters by cumulative ``min_level`` and **truncates to the hard cap** read from
settings (8 intermedio / 20 avanzado) — the cap can never be exceeded even if the
JSON grows. ``básico`` ⇒ ``[]`` (detection only, no payloads).

``{{CANARY}}`` is substituted **per chatbot** with a unique runtime token
(``secrets.token_urlsafe``); that is what makes the canary leak deterministic and
the evidence incontestable (see ``judge.py``).
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"
_PAYLOADS_FILE = _DATA_DIR / "payloads.json"

CANARY_PLACEHOLDER = "{{CANARY}}"

#: Defaults mirror spec §3 / settings; used when the settings keys are absent.
DEFAULT_CAP_INTERMEDIO = 8
DEFAULT_CAP_AVANZADO = 20

#: Cumulative level ordering — a payload with ``min_level`` <= the scan level applies.
_LEVEL_ORDER: dict[str, int] = {"basico": 0, "intermedio": 1, "avanzado": 2}


@dataclass(frozen=True)
class Payload:
    """A single attack payload from the bank (internal worker dataclass)."""

    id: str
    technique: str  # canary | system_prompt_leak | jailbreak
    min_level: str  # basico | intermedio | avanzado
    text: str
    canary_token: str | None = None


@lru_cache(maxsize=1)
def _raw_payloads() -> list[Payload]:
    raw = json.loads(_PAYLOADS_FILE.read_text(encoding="utf-8"))
    return [
        Payload(
            id=entry["id"],
            technique=entry["technique"],
            min_level=entry["min_level"],
            text=entry["text"],
        )
        for entry in raw["payloads"]
    ]


def _cap_for(level: str) -> int:
    """Hard per-chatbot cap for ``level``, read from settings (getattr-default)."""
    from src.common.settings import settings  # local: keep import light + override-safe

    norm = str(level).lower()
    if norm == "avanzado":
        return int(getattr(settings, "AGENTIC_PAYLOAD_CAP_AVANZADO", DEFAULT_CAP_AVANZADO))
    if norm == "intermedio":
        return int(
            getattr(settings, "AGENTIC_PAYLOAD_CAP_INTERMEDIO", DEFAULT_CAP_INTERMEDIO)
        )
    return 0  # basico (or unknown) -> detection only, no payloads


def load_payloads(level: str) -> list[Payload]:
    """Return the payloads for ``level`` — filtered by ``min_level`` and capped.

    ``basico`` ⇒ ``[]``. The list is truncated to the hard cap so the bank never
    exceeds 8 (intermedio) / 20 (avanzado) per chatbot regardless of JSON size.
    """
    cap = _cap_for(level)
    if cap <= 0:
        return []
    level_rank = _LEVEL_ORDER.get(str(level).lower(), 0)
    eligible = [
        p for p in _raw_payloads() if _LEVEL_ORDER.get(p.min_level, 99) <= level_rank
    ]
    return eligible[:cap]


def new_canary_token() -> str:
    """A unique, hard-to-guess control token for one chatbot probe session."""
    return f"OWLIVER-{secrets.token_urlsafe(12)}"


def inject_canary(payload: Payload, token: str) -> Payload:
    """Return a copy of ``payload`` with ``{{CANARY}}`` substituted by ``token``.

    For canary payloads, also records ``canary_token`` so the judge can verify the
    leak deterministically by regex. Non-canary payloads pass through unchanged
    (no placeholder), keeping ``canary_token`` ``None``.
    """
    if CANARY_PLACEHOLDER in payload.text:
        return replace(
            payload,
            text=payload.text.replace(CANARY_PLACEHOLDER, token),
            canary_token=token,
        )
    if payload.technique == "canary":
        # Defensive: a canary payload should always carry the placeholder, but if
        # not, still bind the token so the verdict path stays deterministic.
        return replace(payload, canary_token=token)
    return payload
