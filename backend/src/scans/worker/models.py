"""``ModelFactory`` — centralizes pentest-model construction with a provider switch.

Builds the Agno model instances for the **coordinator** tier (Opus role) and the
**member** tier (Sonnet role) from settings. A single ``MODEL_PROVIDER`` env var
swaps the whole Team between providers WITHOUT touching ``team.py`` /
``members.py`` / ``summary.py`` / ``llm_judge.py``:

    MODEL_PROVIDER=anthropic   (default) → agno ``Claude``      (Anthropic native)
    MODEL_PROVIDER=openai               → agno ``OpenAIChat``   (OpenAI native)
    MODEL_PROVIDER=gemini               → agno ``Gemini``       (Google native)
    MODEL_PROVIDER=openrouter           → agno ``OpenRouter``   (OpenRouter gateway)
    MODEL_PROVIDER=minimax              → agno ``OpenAILike``   (MiniMax, OpenAI-compatible)
    MODEL_PROVIDER=glm                  → agno ``OpenAILike``   (Zhipu / Z.ai GLM, OpenAI-compatible)

Per provider the api key, base url and model id come from settings (read with
``getattr``-defaults). The coordinator/member *tiers* are preserved: the native
providers map them to two distinct ids (Anthropic ``OPUS_MODEL_ID`` /
``SONNET_MODEL_ID``; OpenAI / Gemini / OpenRouter ``*_COORDINATOR_MODEL_ID`` /
``*_MEMBER_MODEL_ID``). The OpenAI-compatible providers serve a single model id for
both tiers (``*_MODEL_ID``) since MiniMax / GLM each expose one main model.
``opus()`` / ``sonnet()`` are kept as aliases of ``coordinator()`` / ``member()`` so
existing call sites need no change.

CRITICAL: ``agno`` and the provider SDKs are **lazy-imported inside the build
methods** so this module — and everything importing it (the worker, the
``RunScanHandler``) — imports cleanly on CI where neither is installed. Settings are
read with ``getattr``-defaults for the same reason (the keys may not exist yet).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.common.settings import settings

#: Provider keys accepted by ``MODEL_PROVIDER`` (case-insensitive).
ANTHROPIC = "anthropic"
OPENAI = "openai"
GEMINI = "gemini"
OPENROUTER = "openrouter"
MINIMAX = "minimax"
GLM = "glm"

#: Defaults used when the settings keys are absent (getattr-with-default).
#: Current Claude model IDs (override via OPUS_MODEL_ID / SONNET_MODEL_ID settings).
DEFAULT_OPUS_MODEL_ID = "claude-opus-4-8"
DEFAULT_SONNET_MODEL_ID = "claude-sonnet-4-6"


def _setting(name: str, default: str) -> str:
    value = getattr(settings, name, None)
    return value if isinstance(value, str) and value else default


@dataclass(frozen=True)
class _ProviderSpec:
    """How to build a provider's models: which settings to read + sensible defaults.

    ``base_url_setting`` is ``None`` for Anthropic (the native SDK resolves its own
    endpoint). For the OpenAI-compatible providers the coordinator and member tiers
    intentionally read the SAME ``*_MODEL_ID`` setting (one model serves both).
    """

    api_key_setting: str
    base_url_setting: str | None
    base_url_default: str
    coordinator_setting: str
    coordinator_default: str
    member_setting: str
    member_default: str


#: Registry of supported providers. The model-id *defaults* below are overridable via
#: env (``*_MODEL_ID``) — set them to the exact id your provider currently exposes.
_PROVIDERS: dict[str, _ProviderSpec] = {
    ANTHROPIC: _ProviderSpec(
        api_key_setting="ANTHROPIC_API_KEY",
        base_url_setting=None,
        base_url_default="",
        coordinator_setting="OPUS_MODEL_ID",
        coordinator_default=DEFAULT_OPUS_MODEL_ID,
        member_setting="SONNET_MODEL_ID",
        member_default=DEFAULT_SONNET_MODEL_ID,
    ),
    # Native OpenAI/Gemini/OpenRouter: the SDK resolves its own endpoint
    # (base_url_setting=None) and each tier reads a distinct *_MODEL_ID, mirroring
    # Anthropic's coordinator/member split. Defaults are overridable via env.
    OPENAI: _ProviderSpec(
        api_key_setting="OPENAI_API_KEY",
        base_url_setting=None,
        base_url_default="",
        coordinator_setting="OPENAI_COORDINATOR_MODEL_ID",
        coordinator_default="gpt-5.2",
        member_setting="OPENAI_MEMBER_MODEL_ID",
        member_default="gpt-5-mini",
    ),
    GEMINI: _ProviderSpec(
        api_key_setting="GEMINI_API_KEY",
        base_url_setting=None,
        base_url_default="",
        coordinator_setting="GEMINI_COORDINATOR_MODEL_ID",
        coordinator_default="gemini-3-pro-preview",
        member_setting="GEMINI_MEMBER_MODEL_ID",
        member_default="gemini-3-flash-preview",
    ),
    OPENROUTER: _ProviderSpec(
        api_key_setting="OPENROUTER_API_KEY",
        base_url_setting=None,
        base_url_default="",
        coordinator_setting="OPENROUTER_COORDINATOR_MODEL_ID",
        coordinator_default="openai/gpt-5.2",
        member_setting="OPENROUTER_MEMBER_MODEL_ID",
        member_default="openai/gpt-5-mini",
    ),
    MINIMAX: _ProviderSpec(
        api_key_setting="MINIMAX_API_KEY",
        base_url_setting="MINIMAX_BASE_URL",
        base_url_default="https://api.minimax.io/v1",
        coordinator_setting="MINIMAX_MODEL_ID",
        coordinator_default="MiniMax-M2",
        member_setting="MINIMAX_MODEL_ID",
        member_default="MiniMax-M2",
    ),
    GLM: _ProviderSpec(
        api_key_setting="GLM_API_KEY",
        base_url_setting="GLM_BASE_URL",
        base_url_default="https://api.z.ai/api/paas/v4",
        coordinator_setting="GLM_MODEL_ID",
        coordinator_default="glm-4.6",
        member_setting="GLM_MODEL_ID",
        member_default="glm-4.6",
    ),
}


def _resolve_provider(name: str | None) -> str:
    key = (name or _setting("MODEL_PROVIDER", ANTHROPIC)).strip().lower()
    if key not in _PROVIDERS:
        raise ValueError(
            f"Unknown MODEL_PROVIDER {key!r}; expected one of {sorted(_PROVIDERS)}"
        )
    return key


@dataclass
class ModelFactory:
    """Builds the coordinator/member models for the selected provider.

    ``provider`` defaults to the ``MODEL_PROVIDER`` setting. The api key, base url and
    per-tier model ids are resolved from the provider's settings unless explicitly
    passed (the constructor overrides exist for tests and for the judge, which injects
    ``member_model_id=AGENTIC_JUDGE_MODEL_ID``). ``agno`` / the provider SDK are
    imported lazily inside the build methods.
    """

    provider: str = ""
    api_key: str | None = None
    base_url: str | None = None
    coordinator_model_id: str = ""
    member_model_id: str = ""
    _spec: _ProviderSpec = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.provider = _resolve_provider(self.provider)
        spec = _PROVIDERS[self.provider]
        self._spec = spec
        if self.api_key is None:
            self.api_key = getattr(settings, spec.api_key_setting, None)
        if self.base_url is None and spec.base_url_setting is not None:
            self.base_url = _setting(spec.base_url_setting, spec.base_url_default)
        self.coordinator_model_id = self.coordinator_model_id or _setting(
            spec.coordinator_setting, spec.coordinator_default
        )
        self.member_model_id = self.member_model_id or _setting(
            spec.member_setting, spec.member_default
        )

    def _model(self, model_id: str) -> Any:
        """Build one Agno model for ``model_id`` using the selected provider.

        Native providers — Anthropic → ``Claude``, OpenAI → ``OpenAIChat``,
        Gemini → ``Gemini``, OpenRouter → ``OpenRouter`` — each resolve their own
        endpoint. MiniMax / GLM → ``OpenAILike`` pointed at the provider's
        OpenAI-compatible ``base_url``. Lazy imports keep CI clean.
        """
        if self.provider == ANTHROPIC:
            from agno.models.anthropic import Claude  # noqa: PLC0415

            return Claude(id=model_id, api_key=self.api_key)

        if self.provider == OPENAI:
            from agno.models.openai import OpenAIChat  # noqa: PLC0415

            return OpenAIChat(id=model_id, api_key=self.api_key)

        if self.provider == GEMINI:
            from agno.models.google import Gemini  # noqa: PLC0415

            return Gemini(id=model_id, api_key=self.api_key)

        if self.provider == OPENROUTER:
            from agno.models.openrouter import OpenRouter  # noqa: PLC0415

            return OpenRouter(id=model_id, api_key=self.api_key)

        # MiniMax / GLM expose OpenAI-compatible endpoints — one model class fits both.
        from agno.models.openai.like import OpenAILike  # noqa: PLC0415

        return OpenAILike(id=model_id, api_key=self.api_key, base_url=self.base_url)

    def coordinator(self) -> Any:
        """The coordinator model (Team lead / executive-summary synthesis)."""
        return self._model(self.coordinator_model_id)

    def member(self) -> Any:
        """The member model (OWASP / agentic subagents + the agentic LLM judge)."""
        return self._model(self.member_model_id)

    # Back-compat aliases — call sites in team.py/members.py/summary.py use these.
    def opus(self) -> Any:
        return self.coordinator()

    def sonnet(self) -> Any:
        return self.member()
