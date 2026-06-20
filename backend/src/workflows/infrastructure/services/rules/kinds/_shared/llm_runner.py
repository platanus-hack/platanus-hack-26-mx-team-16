"""Thin LLM caller wrapper used by kinds.

Every text-LLM call in the workflows module flows through `LLMRunner`. The
default implementation is `AgnoLLMRunner` (multi-provider via Agno); tests
inject `StaticLLMRunner` with recorded payloads.

Provider/model selection by role:

- `default_llm_runner("parser")` → reads `ANALYSIS_PARSER_PROVIDER`
- `default_llm_runner("synthesizer")` → reads `ANALYSIS_SYNTHESIZER_PROVIDER`
- `default_llm_runner("evaluator")` → reads `ANALYSIS_REVIEWER_PROVIDER`
- `default_llm_runner("critic")` → reads `ANALYSIS_CRITIC_PROVIDER`
- `default_llm_runner("assess")` → reads `ANALYSIS_ASSESS_PROVIDER`

Falls back to `openai:gpt-4o-mini` if the env override is empty. Override
`LLM_TEST_MODEL` in tests to pin a specific model.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


Role = Literal["parser", "synthesizer", "evaluator", "critic", "schema_builder", "assess", "default"]


_PROVIDER_DEFAULT_MODEL: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-20241022",
    "gemini": "gemini-2.0-flash",
    "google": "gemini-2.0-flash",
    "openrouter": "openrouter/auto",
}

_FALLBACK_MODEL_ID = "openai:gpt-4o-mini"


class LLMRunner(Protocol):
    async def run(
        self,
        *,
        system: str,
        user: str,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]: ...


@dataclass
class StaticLLMRunner:
    """Returns a fixed payload — used as a sane default and in tests."""

    payload: dict[str, Any]

    async def run(
        self,
        *,
        system: str,
        user: str,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        return self.payload


@dataclass
class FunctionLLMRunner:
    """Adapter for arbitrary async callables (e.g. wired in production)."""

    fn: Callable[..., Awaitable[dict[str, Any]]]

    async def run(
        self,
        *,
        system: str,
        user: str,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        return await self.fn(system=system, user=user, output_schema=output_schema)


def coerce_json(payload: Any) -> dict[str, Any]:
    """Best-effort: ensure dict from str/bytes/dict."""
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, bytes | bytearray):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as exc:
            msg = f"LLM response is not JSON: {exc.msg}"
            raise ValueError(msg) from exc
        if not isinstance(value, dict):
            msg = "LLM response root must be an object"
            raise ValueError(msg)
        return value
    msg = f"Unsupported LLM payload type: {type(payload).__name__}"
    raise ValueError(msg)


@dataclass
class AgnoLLMRunner:
    """LLMRunner that delegates to an Agno `Agent` for structured generation.

    `model_id` selects the provider via the same `provider:id` shorthand the
    rest of the platform uses (e.g. `openai:gpt-4o-mini`,
    `anthropic:claude-3-5-haiku-20241022`, `google:gemini-2.0-flash`). The
    output schema is appended to the system prompt and we ask the model for
    plain JSON: that path works across all providers and schema shapes.
    """

    model_id: str = "openai:gpt-4o-mini"
    temperature: float | None = 0.0

    async def run(
        self,
        *,
        system: str,
        user: str,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        from agno.agent import Agent  # noqa: PLC0415

        model = _build_agno_model(self.model_id, temperature=self.temperature)
        composed_system = _compose_system_prompt(system, output_schema)
        agent = Agent(model=model, system_message=composed_system, telemetry=False)
        result = await agent.arun(user)
        content = getattr(result, "content", None)
        if content is None:
            msg = f"AgnoLLMRunner: model {self.model_id!r} returned an empty response"
            raise ValueError(msg)
        if isinstance(content, str):
            content = _strip_code_fences(content)
        return coerce_json(content)


def _compose_system_prompt(system: str, output_schema: dict[str, Any]) -> str:
    schema_str = json.dumps(output_schema, ensure_ascii=False)
    return (
        f"{system}\n\n"
        "You MUST respond with a single JSON object that conforms exactly to "
        "the JSON Schema below. No prose, no Markdown fencing — only the JSON "
        "object.\n\nJSON Schema:\n"
        f"{schema_str}"
    )


def _strip_code_fences(text: str) -> str:
    """Tolerate models that wrap JSON in ```json ... ``` despite instructions."""
    s = text.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl != -1:
            s = s[first_nl + 1 :]
        if s.endswith("```"):
            s = s[:-3]
    return s.strip()


def _build_agno_model(model_id: str, *, temperature: float | None) -> Any:
    """Resolve `provider:id` strings to Agno model instances."""
    if ":" not in model_id:
        msg = f"AgnoLLMRunner: model_id must be 'provider:id', got {model_id!r}"
        raise ValueError(msg)
    provider, model = model_id.split(":", 1)
    provider = provider.lower()
    kwargs: dict[str, Any] = {"id": model}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if provider == "openai":
        from agno.models.openai import OpenAIChat  # noqa: PLC0415

        return OpenAIChat(**kwargs)
    if provider == "anthropic":
        from agno.models.anthropic import Claude  # noqa: PLC0415

        return Claude(**kwargs)
    if provider in ("google", "gemini"):
        from agno.models.google import Gemini  # noqa: PLC0415

        return Gemini(**kwargs)
    msg = f"AgnoLLMRunner: unsupported provider {provider!r} (model_id={model_id!r})"
    raise ValueError(msg)


_ROLE_TO_SETTING: dict[Role, str] = {
    "parser": "ANALYSIS_PARSER_PROVIDER",
    "synthesizer": "ANALYSIS_SYNTHESIZER_PROVIDER",
    "evaluator": "ANALYSIS_REVIEWER_PROVIDER",
    "critic": "ANALYSIS_CRITIC_PROVIDER",
    "schema_builder": "DOCTYPE_SCHEMA_BUILDER_PROVIDER",
    # E3: el setting existe en `settings.py` — si se renombra, el fallback a
    # `openai:gpt-4o-mini` sería silencioso (getattr → None), como pasa hoy
    # con DOCTYPE_SCHEMA_BUILDER_PROVIDER. Mantener ambos en sync.
    "assess": "ANALYSIS_ASSESS_PROVIDER",
    "default": "",
}


def _resolve_role_model_id(role: Role) -> str:
    """Pick the `provider:model` for a role, honoring settings + env overrides."""
    pinned = os.environ.get("LLM_TEST_MODEL", "").strip()
    if pinned:
        return pinned

    setting_name = _ROLE_TO_SETTING.get(role) or ""
    if not setting_name:
        return _FALLBACK_MODEL_ID

    try:
        from src.common.settings import settings  # noqa: PLC0415

        provider_raw = (getattr(settings, setting_name, None) or "").strip().lower()
    except Exception:  # noqa: BLE001
        provider_raw = ""

    return _model_id_from_provider(provider_raw)


def _model_id_from_provider(provider_raw: str) -> str:
    """``"openai"`` / ``"openai:gpt-4o"`` → un ``provider:model`` válido."""
    provider_raw = (provider_raw or "").strip().lower()
    if not provider_raw:
        return _FALLBACK_MODEL_ID
    if ":" in provider_raw:
        return provider_raw
    model_default = _PROVIDER_DEFAULT_MODEL.get(provider_raw)
    if model_default is None:
        return _FALLBACK_MODEL_ID
    return f"{provider_raw}:{model_default}"


def default_llm_runner(role: Role = "default", override: str | None = None) -> "LLMRunner":
    """Build the production runner for a given agent role.

    ``override`` (phases-config · F1b/G1) es un ``provider`` o ``provider:model``
    per-pipeline sellado en la config de la fase; tiene prioridad sobre el setting
    env-global del rol. ``None`` ⇒ comportamiento de hoy (lee ``ANALYSIS_*_PROVIDER``).
    """
    model_id = _model_id_from_provider(override) if override else _resolve_role_model_id(role)
    return AgnoLLMRunner(model_id=model_id)
