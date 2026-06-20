"""Resolución de un Classifier a su contrato de ejecución (F3 · D-C).

Función PURA (sin I/O): la activity ``resolve_classifier`` carga la fila del
registry y delega aquí la normalización por ``kind``. ``classify_pages`` consume
el contrato (hoy el motor ``lambda``; ``prompt``/``tool`` quedan declarados para
sus motores futuros).
"""

from __future__ import annotations

from typing import Any

from src.common.domain.enums.pipelines import ClassifierKind
from src.workflows.domain.models.classifier import Classifier


def resolve_classifier_contract(classifier: Classifier) -> dict[str, Any]:
    """``Classifier`` → contrato ``{kind, lambda_function?, lambda_alias?, config}``.

    - ``lambda`` → ``{function, alias?}`` se expone como ``lambda_function``/
      ``lambda_alias`` (lo que consume ``classify_pages`` hoy).
    - ``prompt``/``tool`` → se devuelve su ``config`` cruda para el motor futuro.
    """
    cfg = classifier.config or {}
    if classifier.kind is ClassifierKind.LAMBDA:
        return {
            "kind": ClassifierKind.LAMBDA.value,
            "lambda_function": cfg.get("function"),
            "lambda_alias": cfg.get("alias"),
            "config": {},
        }
    if classifier.kind is ClassifierKind.PROMPT:
        return {
            "kind": ClassifierKind.PROMPT.value,
            "config": {k: cfg.get(k) for k in ("provider", "prompt_template", "output_schema")},
        }
    return {
        "kind": ClassifierKind.TOOL.value,
        "config": {k: cfg.get(k) for k in ("tool_slug", "transport")},
    }
