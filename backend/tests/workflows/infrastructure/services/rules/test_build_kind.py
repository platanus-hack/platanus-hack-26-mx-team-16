"""build_kind — kind LLM con override de provider por rol (phases-config · H1).

``analyze.{parser,reviewer}_provider`` sellan un provider por pipeline; el run
construye un kind con runners override (sin tocar el registry global). Para kinds
sin runner LLM devuelve ``None`` ⇒ el caller cae al registry.
"""

from __future__ import annotations

from expects import be_none, equal, expect

from src.workflows.infrastructure.services.rules.bootstrap import build_kind
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    AgnoLLMRunner,
)
from src.workflows.infrastructure.services.rules.kinds.derivation import DerivationKind
from src.workflows.infrastructure.services.rules.kinds.validation import ValidationKind


def test_build_kind__validation_applies_parser_and_evaluator_overrides():
    kind = build_kind("VALIDATION", parser_provider="anthropic", evaluator_provider="openai:gpt-4o")

    expect(isinstance(kind, ValidationKind)).to(equal(True))
    # evaluator runner ← evaluator_provider; parser runner ← parser_provider.
    expect(kind.llm_runner.model_id).to(equal("openai:gpt-4o"))
    expect(kind.parser.llm_runner.model_id).to(equal("anthropic:claude-3-5-haiku-20241022"))


def test_build_kind__validation_without_overrides_uses_agno_runners():
    # Sin overrides reproduce el wiring de boot (Agno-backed, no el stub estático).
    kind = build_kind("VALIDATION")

    expect(isinstance(kind.llm_runner, AgnoLLMRunner)).to(equal(True))
    expect(isinstance(kind.parser.llm_runner, AgnoLLMRunner)).to(equal(True))


def test_build_kind__derivation_applies_evaluator_override():
    kind = build_kind("DERIVATION", evaluator_provider="anthropic")

    expect(isinstance(kind, DerivationKind)).to(equal(True))
    expect(kind.llm_runner.model_id).to(equal("anthropic:claude-3-5-haiku-20241022"))


def test_build_kind__non_llm_kind_returns_none():
    # CHECKSUM / cross_ref no tienen runner LLM ⇒ None ⇒ el caller usa el registry.
    expect(build_kind("CHECKSUM")).to(be_none)
    expect(build_kind("CROSS_REFERENCE")).to(be_none)
