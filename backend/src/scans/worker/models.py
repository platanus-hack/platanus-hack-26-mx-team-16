"""``ModelFactory`` — centralizes Claude model construction (spec §7, plan §7).

Returns Agno ``Claude`` model instances for the Opus coordinator and the Sonnet
members, reading the model ids + ``ANTHROPIC_API_KEY`` from settings. Centralizing
here lets tests inject a fake factory (no real API call) without touching
``team.py``.

CRITICAL: ``agno`` / ``anthropic`` are **lazy-imported inside the methods** so this
module — and everything that imports it (the worker, the RunScanHandler) — imports
cleanly on CI where neither package is installed. Settings are read with
``getattr``-defaults for the same reason (the keys may not exist yet).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.common.settings import settings

#: Defaults used when the settings keys are absent (getattr-with-default, plan §0).
#: Current Claude model IDs (override via OPUS_MODEL_ID / SONNET_MODEL_ID settings).
DEFAULT_OPUS_MODEL_ID = "claude-opus-4-8"
DEFAULT_SONNET_MODEL_ID = "claude-sonnet-4-6"


def _setting(name: str, default: str) -> str:
    value = getattr(settings, name, None)
    return value if isinstance(value, str) and value else default


@dataclass
class ModelFactory:
    """Builds Claude models from settings. ``agno``/``anthropic`` imported lazily."""

    opus_model_id: str = ""
    sonnet_model_id: str = ""
    api_key: str | None = None

    def __post_init__(self) -> None:
        self.opus_model_id = self.opus_model_id or _setting("OPUS_MODEL_ID", DEFAULT_OPUS_MODEL_ID)
        self.sonnet_model_id = self.sonnet_model_id or _setting(
            "SONNET_MODEL_ID", DEFAULT_SONNET_MODEL_ID
        )
        if self.api_key is None:
            self.api_key = getattr(settings, "ANTHROPIC_API_KEY", None)

    def _claude(self, model_id: str) -> Any:
        # LAZY import — keeps the module importable without agno/anthropic (CI).
        from agno.models.anthropic import Claude  # noqa: PLC0415

        return Claude(id=model_id, api_key=self.api_key)

    def opus(self) -> Any:
        """The coordinator model (executive synthesis + delegation)."""
        return self._claude(self.opus_model_id)

    def sonnet(self) -> Any:
        """The member model (OWASP / agentic subagents)."""
        return self._claude(self.sonnet_model_id)
