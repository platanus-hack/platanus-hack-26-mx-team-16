"""SingleAgentService — wraps an Agno Agent as an injectable service."""

from __future__ import annotations

import json
from typing import Any, Type, TypeVar

from agno.agent import Agent
from pydantic import BaseModel

from src.workflows.infrastructure.agents.builder import AgentBuilder, AgentEffort, AgentProvider
from src.workflows.infrastructure.services.utils.json_safety import strip_fences

T = TypeVar("T", bound=BaseModel)


class SingleAgentService:
    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    @classmethod
    def from_builder(
        cls,
        system_prompt: str,
        provider: AgentProvider = AgentProvider.OPENAI,
        effort: AgentEffort = AgentEffort.LITE,
        **kwargs: Any,
    ) -> "SingleAgentService":
        return cls(AgentBuilder.build(system_prompt=system_prompt, provider=provider, effort=effort, **kwargs))

    def run(self, prompt: str, output_schema: Type[T]) -> T:
        response = self._agent.run(prompt, output_schema=output_schema)
        return response.content

    async def arun(self, prompt: str, output_schema: Type[T]) -> T:
        response = await self._agent.arun(prompt, output_schema=output_schema)
        return response.content

    async def arun_json(self, prompt: str) -> dict[str, Any]:
        """Run without structured outputs and parse the response as a JSON dict.

        Use this when the output schema uses ``additionalProperties`` or other
        constructs that OpenAI structured outputs does not support. The schema
        must be embedded in the agent's system prompt as text instructions.
        """
        response = await self._agent.arun(prompt)
        content = getattr(response, "content", None)
        if isinstance(content, dict):
            return content
        parsed, _ = json.JSONDecoder().raw_decode(strip_fences(content or ""))
        if not isinstance(parsed, dict):
            raise ValueError(f"Agent response is not a JSON object: {type(parsed).__name__}")
        return parsed

