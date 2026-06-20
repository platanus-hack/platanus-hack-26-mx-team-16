"""default_llm_runner provider override (phases-config · G1 — assess/output)."""

from __future__ import annotations

from expects import equal, expect

from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    AgnoLLMRunner,
    default_llm_runner,
)


def test_override__provider_only_maps_to_default_model():
    runner = default_llm_runner("assess", override="anthropic")

    expect(isinstance(runner, AgnoLLMRunner)).to(equal(True))
    expect(runner.model_id).to(equal("anthropic:claude-3-5-haiku-20241022"))


def test_override__full_provider_model_passes_through():
    runner = default_llm_runner("synthesizer", override="openai:gpt-4o")

    expect(runner.model_id).to(equal("openai:gpt-4o"))


def test_no_override__falls_back_to_role_resolution():
    # Sin override resuelve por rol/env (default seguro openai:gpt-4o-mini en test).
    runner = default_llm_runner("assess")

    expect(runner.model_id).to(contain_colon())


def contain_colon():
    from expects.matchers import Matcher

    class _HasColon(Matcher):
        def _match(self, subject):
            return ":" in str(subject), ["is a provider:model id"]

    return _HasColon()
