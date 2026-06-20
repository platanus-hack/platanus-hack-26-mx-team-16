"""UpdateWorkflowRequest valida `case_noun` — product/specs/data-model/case-noun.md §2.

Si viene, ambos locales (es/en) con `one`+`other` no vacíos (≤30 chars). null ⇒
borra el override (la UI cae al default i18n).
"""

import pytest
from expects import be_none, equal, expect
from pydantic import ValidationError

from src.workflows.presentation.schemas.workflow_schemas import UpdateWorkflowRequest


def test_valid_case_noun_accepted():
    req = UpdateWorkflowRequest(
        caseNoun={
            "es": {"one": "Pedido", "other": "Pedidos"},
            "en": {"one": "Order", "other": "Orders"},
        }
    )
    expect(req.case_noun["es"]["one"]).to(equal("Pedido"))
    expect(req.case_noun["en"]["other"]).to(equal("Orders"))


def test_none_case_noun_is_default():
    expect(UpdateWorkflowRequest().case_noun).to(be_none)


@pytest.mark.parametrize(
    "bad",
    [
        {"es": {"one": "Pedido", "other": "Pedidos"}},  # falta el locale 'en'
        {"es": {"one": "Pedido"}, "en": {"one": "Order", "other": "Orders"}},  # falta 'other'
        {"es": {"one": "", "other": "Pedidos"}, "en": {"one": "Order", "other": "Orders"}},  # vacío
        {"es": {"one": "x" * 31, "other": "Pedidos"}, "en": {"one": "Order", "other": "Orders"}},  # >30
    ],
)
def test_invalid_case_noun_rejected(bad):
    with pytest.raises(ValidationError):
        UpdateWorkflowRequest(caseNoun=bad)
