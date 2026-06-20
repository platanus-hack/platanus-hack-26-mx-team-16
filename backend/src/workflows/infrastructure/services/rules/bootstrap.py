"""Register first-party kinds and checksum algorithms at app startup.

Boot wires the production runner: every text-LLM call goes through the
Agno-backed `AgnoLLMRunner`. Each agent role (`parser`, `evaluator`,
`synthesizer`, `critic`) reads its model from `ANALYSIS_*_PROVIDER`
settings via `default_llm_runner(role)`.

Tests bypass this entirely by importing the kinds directly — those keep the
safe `StaticLLMRunner` stub in their `default_factory`.
"""

from __future__ import annotations

from src.workflows.infrastructure.services.rules import registry
from src.workflows.infrastructure.services.rules.checksums import registry as checksum_registry
from src.workflows.infrastructure.services.rules.checksums.algorithms import (
    cc_colombia,
    ci_bolivia,
    iso_iban_mod97,
    luhn_credit_card,
    nit_bolivia_mod11,
    nit_colombia_mod11,
    rut_chile_mod11,
)
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    default_llm_runner,
)
from src.workflows.infrastructure.services.rules.kinds.derivation import DerivationKind
from src.workflows.infrastructure.services.rules.kinds.validation import ValidationKind
from src.workflows.infrastructure.services.rules.kinds.validation.llm_parser import (
    ValidationParser,
)
from src.workflows.infrastructure.services.run_summary.synthesizer import (
    SynthesizerAgent,
)


def build_kind(
    kind_name: str,
    *,
    parser_provider: str | None = None,
    evaluator_provider: str | None = None,
):
    """Construye un kind LLM con override de provider por rol (phases-config ·
    analyze.{parser,reviewer}_provider). ``None`` ⇒ provider del rol (env). Para
    kinds sin runner LLM (checksum/cross_ref…) devuelve ``None`` ⇒ el caller usa
    el registry global. Con ambos overrides ``None`` reproduce el wiring de boot.
    """
    if kind_name == "VALIDATION":
        return ValidationKind(
            parser=ValidationParser(llm_runner=default_llm_runner("parser", override=parser_provider)),
            llm_runner=default_llm_runner("evaluator", override=evaluator_provider),
        )
    if kind_name == "DERIVATION":
        return DerivationKind(llm_runner=default_llm_runner("evaluator", override=evaluator_provider))
    return None


def register_default_kinds() -> None:
    """Register Agno-backed VALIDATION + DERIVATION kinds (production wiring)."""
    if not registry.has("VALIDATION"):
        registry.register(build_kind("VALIDATION"))
    if not registry.has("DERIVATION"):
        registry.register(build_kind("DERIVATION"))
    register_default_checksums()


def register_stub_kinds() -> None:
    """Register kinds wired with their default `StaticLLMRunner` stubs (tests).

    Use this from test conftests where the real LLM is undesirable. Each
    kind keeps its own safe-default runner (no real network call) so the
    application layer can verify its own logic deterministically.
    """
    if not registry.has("VALIDATION"):
        registry.register(ValidationKind())
    if not registry.has("DERIVATION"):
        registry.register(DerivationKind())
    register_default_checksums()


def register_default_checksums() -> None:
    checksum_registry.register("rut_chile_mod11", rut_chile_mod11.validate)
    checksum_registry.register("luhn_credit_card", luhn_credit_card.validate)
    checksum_registry.register("iso_iban_mod97", iso_iban_mod97.validate)
    # E5 · multi-country v1 (BO+CO). `ci_bolivia`/`cc_colombia` are format
    # checks (no public verifier digit exists for those documents).
    checksum_registry.register("nit_bolivia_mod11", nit_bolivia_mod11.validate)
    checksum_registry.register("ci_bolivia", ci_bolivia.validate)
    checksum_registry.register("nit_colombia_mod11", nit_colombia_mod11.validate)
    checksum_registry.register("cc_colombia", cc_colombia.validate)


def build_synthesizer_agent(provider: str | None = None) -> SynthesizerAgent:
    """Production factory for the synthesizer agent (Agno-backed).

    ``provider`` (phases-config · output.synthesizer_provider) overrides the role
    provider; ``None`` ⇒ env ``ANALYSIS_SYNTHESIZER_PROVIDER`` (today's behavior).
    Tests construct ``SynthesizerAgent(llm_runner=StaticLLMRunner(...))`` directly.
    """
    runner = default_llm_runner("synthesizer", override=provider)
    return SynthesizerAgent(
        llm_runner=runner,
        model=getattr(runner, "model_id", None),
        provider=getattr(runner, "model_id", "").split(":", 1)[0] or None,
    )
