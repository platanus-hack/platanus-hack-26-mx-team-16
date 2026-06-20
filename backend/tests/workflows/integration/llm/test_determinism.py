"""Determinism / variance del PARSER.

Para cada ejemplo, corre N veces el PARSER LLM real (env
`LLM_DETERMINISM_RUNS`, default 5) y mide:

- `tree.op` consistency rate (igual top-level op cada corrida)
- `sub_check_count` desviación estándar

Falla si:

- `tree.op` consistency < 80%
- `sub_check_count` stdev > 1.5

No falla por varianza en texto narrativo.
"""

from __future__ import annotations

import statistics
from collections import Counter
from uuid import uuid4

import pytest
from expects import be_true, expect

from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.domain.rules.kind_protocol import CompileContext
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    AgnoLLMRunner,
)
from src.workflows.infrastructure.services.rules.kinds.validation.kind import (
    ValidationKind,
)
from src.workflows.infrastructure.services.rules.kinds.validation.llm_parser import (
    ValidationParser,
)
from tests.workflows.integration.conftest import (
    doctypes_from_slugs,
    llm_default_model,
    llm_determinism_runs,
)


pytestmark = pytest.mark.llm


_DETERMINISM_CASES = [
    {
        "id": "V1",
        "prompt": "El @dni.rut debe estar bien formateado y el DV válido según mod 11 chileno.",
        "slugs": ["dni"],
    },
    {
        "id": "V3-OR",
        "prompt": (
            "El comprobante de domicilio puede ser: al menos un @utility_bill[] reciente, "
            "O al menos un @bank_statement[] reciente."
        ),
        "slugs": ["utility_bill", "bank_statement"],
    },
    {
        "id": "V7-AGGREGATE",
        "prompt": "Debe haber al menos 3 @invoice[] y la suma de @invoice.monto_total > 1.000.000.",
        "slugs": ["invoice"],
    },
]


def _ctx(slugs):
    workflow_id, tenant_id = uuid4(), uuid4()
    return CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=doctypes_from_slugs(slugs, workflow_id, tenant_id),
    )


@pytest.mark.parametrize("case", _DETERMINISM_CASES, ids=lambda c: c["id"])
async def test_parser_determinism__top_level_op_consistent_across_runs(case):
    runs = llm_determinism_runs()
    ops: list[str] = []
    counts: list[int] = []

    for _ in range(runs):
        rule = WorkflowRule(
            uuid=uuid4(),
            tenant_id=uuid4(),
            workflow_id=uuid4(),
            name=f"det-{case['id']}",
            kind="VALIDATION",
            prompt=case["prompt"],
            config={"severity": "MAJOR"},
        )
        parser = ValidationParser(llm_runner=AgnoLLMRunner(model_id=llm_default_model()))
        try:
            outcome = await ValidationKind(parser=parser).compile(rule, _ctx(case["slugs"]))
        except Exception:
            ops.append("ERROR")
            counts.append(-1)
            continue
        ops.append(outcome.artifact["tree"].get("op", "ref"))
        counts.append(len(outcome.artifact["sub_checks"]))

    most_common_op, op_count = Counter(ops).most_common(1)[0]
    op_rate = op_count / runs
    if op_rate < 0.8:
        pytest.fail(f"{case['id']}: tree.op inconsistent across {runs} runs (observed={dict(Counter(ops))})")

    valid_counts = [c for c in counts if c >= 0]
    if len(valid_counts) >= 2:
        stdev = statistics.pstdev(valid_counts)
        if stdev > 1.5:
            pytest.fail(f"{case['id']}: sub_check_count drift is high (stdev={stdev:.2f}, samples={counts})")

    expect(most_common_op != "ERROR").to(be_true)
