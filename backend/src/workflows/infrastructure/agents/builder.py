"""Centralised agent construction: provider×effort matrix and model resolution."""

from typing import Any

from agno.agent import Agent
from agno.models.base import Model
from pydantic import BaseModel

from src.common.application.logging import get_logger
from src.common.domain.enums.base_enum import BaseEnum

logger = get_logger()

DEFAULT_TEMPERATURE: float = 0.0

_OPENAI_REASONING_PREFIXES: tuple[str, ...] = ("o1", "o3", "o4", "gpt-5")


class AgentProvider(BaseEnum):
    OPENAI = "OPENAI"
    GEMINI = "GEMINI"
    ANTHROPIC = "ANTHROPIC"


class AgentEffort(BaseEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LITE = "LITE"


_MODEL_MATRIX: dict[AgentProvider, dict[AgentEffort, str]] = {
    AgentProvider.OPENAI: {
        AgentEffort.HIGH: "gpt-5.5",
        AgentEffort.MEDIUM: "gpt-5",
        AgentEffort.LITE: "gpt-4.1-mini",
    },
    AgentProvider.GEMINI: {
        AgentEffort.HIGH: "gemini-3.1-pro-preview",
        AgentEffort.MEDIUM: "gemini-3-flash-preview",
        AgentEffort.LITE: "gemini-3.1-flash-lite",
    },
    AgentProvider.ANTHROPIC: {
        AgentEffort.HIGH: "claude-opus-4-7",
        AgentEffort.MEDIUM: "claude-sonnet-4-6",
        AgentEffort.LITE: "claude-haiku-4-5-20251001",
    },
}


class AgentBuilder:
    @classmethod
    def build(
        cls,
        system_prompt: str,
        instructions: list[str] | str | None = None,
        provider: AgentProvider = AgentProvider.OPENAI,
        effort: AgentEffort = AgentEffort.LITE,
        *,
        output_schema: type[BaseModel] | None = None,
        name: str | None = None,
        role: str | None = None,
        retries: int = 2,
        agent_kwargs: dict[str, Any] | None = None,
    ) -> Agent:
        return Agent(
            name=name,
            role=role,
            model=cls.build_model(provider, effort),
            description=system_prompt,
            instructions=instructions or [],
            output_schema=output_schema,
            retries=retries,
            markdown=False,
            structured_outputs=output_schema is not None,
            **(agent_kwargs or {}),
        )

    @classmethod
    def build_model(cls, provider: AgentProvider, effort: AgentEffort) -> Model:
        try:
            model_id = _MODEL_MATRIX[provider][effort]
        except KeyError as exc:
            raise ValueError(
                f"Sin modelo registrado para provider={provider} effort={effort}"
            ) from exc

        temperature: float | None = (
            None
            if provider is AgentProvider.OPENAI and model_id.startswith(_OPENAI_REASONING_PREFIXES)
            else DEFAULT_TEMPERATURE
        )

        if provider is AgentProvider.OPENAI:
            from agno.models.openai import OpenAIChat  # noqa: PLC0415

            return OpenAIChat(id=model_id, temperature=temperature)
        if provider is AgentProvider.GEMINI:
            from agno.models.google import Gemini  # noqa: PLC0415

            return Gemini(id=model_id, temperature=temperature)
        if provider is AgentProvider.ANTHROPIC:
            from agno.models.anthropic import Claude  # noqa: PLC0415

            return Claude(id=model_id, temperature=temperature)

        raise ValueError(f"Provider no soportado: {provider}")
