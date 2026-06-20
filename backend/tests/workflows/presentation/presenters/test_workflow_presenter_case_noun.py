"""WorkflowPresenter expone `case_noun` (o None) — product/specs/data-model/case-noun.md §3.2.

La envoltura de respuesta cameliza la clave a `caseNoun`; las claves anidadas
(es/en/one/other) no llevan guion ⇒ sobreviven intactas.
"""

from uuid import uuid4

from expects import be_none, equal, expect

from src.common.domain.models.processing.workflow import Workflow
from src.workflows.presentation.presenters.workflow import WorkflowPresenter


def _workflow(case_noun: dict | None = None) -> Workflow:
    return Workflow(uuid=uuid4(), tenant_id=uuid4(), name="W", case_noun=case_noun)


def test_to_dict__includes_case_noun_when_set():
    noun = {
        "es": {"one": "Pedido", "other": "Pedidos"},
        "en": {"one": "Order", "other": "Orders"},
    }
    result = WorkflowPresenter(instance=_workflow(noun)).to_dict
    expect(result["case_noun"]).to(equal(noun))


def test_to_dict__case_noun_is_none_when_unset():
    result = WorkflowPresenter(instance=_workflow()).to_dict
    expect(result["case_noun"]).to(be_none)
