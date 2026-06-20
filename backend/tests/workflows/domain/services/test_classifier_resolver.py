"""Resolución de Classifier → contrato de ejecución (phases-config · F3 · D-C)."""

from __future__ import annotations

from uuid import uuid4

from expects import equal, expect

from src.common.domain.enums.pipelines import ClassifierKind
from src.workflows.domain.models.classifier import Classifier
from src.workflows.domain.services.classifier_resolver import resolve_classifier_contract


def _classifier(kind: ClassifierKind, config: dict) -> Classifier:
    return Classifier(uuid=uuid4(), tenant_id=uuid4(), slug="custom", kind=kind, config=config)


def test_resolve__lambda_exposes_function_and_alias():
    result = resolve_classifier_contract(_classifier(ClassifierKind.LAMBDA, {"function": "fn-custom", "alias": "v3"}))

    expect(result["kind"]).to(equal("lambda"))
    expect(result["lambda_function"]).to(equal("fn-custom"))
    expect(result["lambda_alias"]).to(equal("v3"))


def test_resolve__prompt_returns_normalized_config():
    result = resolve_classifier_contract(
        _classifier(ClassifierKind.PROMPT, {"provider": "openai:gpt-4o", "prompt_template": "T", "output_schema": {}})
    )

    expect(result["kind"]).to(equal("prompt"))
    expect(result["config"]["provider"]).to(equal("openai:gpt-4o"))


def test_resolve__tool_returns_normalized_config():
    result = resolve_classifier_contract(
        _classifier(ClassifierKind.TOOL, {"tool_slug": "clf-tool", "transport": "HTTP"})
    )

    expect(result["kind"]).to(equal("tool"))
    expect(result["config"]["tool_slug"]).to(equal("clf-tool"))
