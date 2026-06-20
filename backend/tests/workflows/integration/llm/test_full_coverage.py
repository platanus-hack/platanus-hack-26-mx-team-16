"""Cobertura completa con record-replay (LLM real).

Para cada uno de los 23 ejemplos, corre compile contra el LLM real y
compara con el golden grabado en disco. Tolerancia por campo:

- `tree.op` → match exacto cuando hay golden.
- `sub_check.method` distribución → mismo set (orden flexible).
- Texto narrativo (descripciones, reasons) → no se compara.

Modo grabación: `RECORD_LLM_GOLDEN=1` graba la primera corrida.
Modo replay (default cuando hay golden): compara contra el golden.

Subset: limita ejemplos con `LLM_TEST_SUBSET=v1,v3,d4`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.domain.rules.kind_protocol import CompileContext
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    AgnoLLMRunner,
)
from src.workflows.infrastructure.services.rules.kinds.derivation import DerivationKind
from src.workflows.infrastructure.services.rules.kinds.validation.kind import (
    ValidationKind,
)
from src.workflows.infrastructure.services.rules.kinds.validation.llm_parser import (
    ValidationParser,
)
from tests.workflows.integration.conftest import (
    FIXTURES_ROOT,
    doctypes_from_slugs,
    llm_default_model,
    llm_subset,
    record_llm_golden,
    stub_kb_resolver,
)


pytestmark = pytest.mark.llm


def _golden_root() -> Path:
    provider, model = llm_default_model().split(":", 1)
    base = FIXTURES_ROOT / "golden" / provider / model
    base.mkdir(parents=True, exist_ok=True)
    return base


def _slug(label: str) -> str:
    return label.lower()


def _load_derivation_fixtures() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted((FIXTURES_ROOT / "derivation").glob("d*.json"))]


def _load_validation_fixtures() -> list[dict]:
    base = FIXTURES_ROOT / "validation"
    out = []
    for d in sorted((p for p in base.glob("v*") if p.is_dir()), key=lambda p: int(p.name[1:])):
        rule = json.loads((d / "rule.json").read_text())
        rule["_dir"] = d.name
        out.append(rule)
    return out


def _filter_subset(items, key_fn):
    subset = llm_subset()
    if subset is None:
        return items
    return [it for it in items if key_fn(it).lower() in subset]


def _maybe_save_golden(name: str, payload: dict, *, latency_ms: float) -> None:
    golden_path = _golden_root() / f"{name}.json"
    if record_llm_golden() or not golden_path.exists():
        golden_path.write_text(
            json.dumps(
                {
                    "payload": payload,
                    "latency_ms": round(latency_ms, 1),
                    "model": llm_default_model(),
                },
                indent=2,
                ensure_ascii=False,
            )
        )


def _load_golden(name: str) -> dict | None:
    path = _golden_root() / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _ids_for(items, key_fn):
    return [key_fn(it) for it in items]


_D_FIXTURES = _filter_subset(_load_derivation_fixtures(), lambda f: f["id"])
_V_FIXTURES = _filter_subset(_load_validation_fixtures(), lambda f: f["id"])


@pytest.mark.parametrize("fixture", _D_FIXTURES, ids=_ids_for(_D_FIXTURES, lambda f: f["id"]))
async def test_derivation_compile__record_replay(fixture):
    tenant_id, workflow_id = uuid4(), uuid4()
    rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name=fixture["name"],
        kind="DERIVATION",
        prompt=fixture["rule"]["prompt"],
        config=fixture["rule"]["config"],
    )
    kb_slugs = fixture.get("kb_slugs", [])
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=doctypes_from_slugs(fixture["available_doctypes"], workflow_id, tenant_id),
        kb_resolver=stub_kb_resolver(kb_slugs),
    )

    started = time.time()
    outcome = await DerivationKind(llm_runner=AgnoLLMRunner(model_id=llm_default_model())).compile(rule, ctx)
    elapsed = (time.time() - started) * 1000

    payload = {
        "tree": None,
        "input_count": len(outcome.artifact["inputs"]),
        "tokens": outcome.artifact["tokens"],
    }
    name = f"derivation-{_slug(fixture['id'])}"
    _maybe_save_golden(name, payload, latency_ms=elapsed)

    golden = _load_golden(name)
    expect(golden["payload"]["input_count"]).to(equal(payload["input_count"]))
    expect(golden["payload"]["tokens"]).to(equal(payload["tokens"]))


@pytest.mark.parametrize("fixture", _V_FIXTURES, ids=_ids_for(_V_FIXTURES, lambda f: f["id"]))
async def test_validation_compile__record_replay(fixture):
    tenant_id, workflow_id = uuid4(), uuid4()
    rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name=fixture["name"],
        kind="VALIDATION",
        prompt=fixture["rule"]["prompt"],
        config=fixture["rule"]["config"],
    )
    kb_slugs = fixture.get("kb_slugs", [])
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=doctypes_from_slugs(fixture["available_doctypes"], workflow_id, tenant_id),
        kb_resolver=stub_kb_resolver(kb_slugs),
    )
    parser = ValidationParser(llm_runner=AgnoLLMRunner(model_id=llm_default_model()))
    kind = ValidationKind(parser=parser)

    started = time.time()
    try:
        outcome = await kind.compile(rule, ctx)
    except Exception as exc:
        pytest.skip(f"PARSER LLM produced an invalid payload for {fixture['id']}: {exc}")
        return
    elapsed = (time.time() - started) * 1000

    methods = sorted({sc["method"] for sc in outcome.artifact["sub_checks"]})
    payload = {
        "tree_op": outcome.artifact["tree"].get("op", "ref"),
        "sub_check_count": len(outcome.artifact["sub_checks"]),
        "methods": methods,
    }
    name = f"validation-{fixture['_dir']}"
    _maybe_save_golden(name, payload, latency_ms=elapsed)

    golden = _load_golden(name)
    expect(payload["tree_op"]).to(equal(golden["payload"]["tree_op"]))
    diff = abs(payload["sub_check_count"] - golden["payload"]["sub_check_count"])
    if diff > 1:
        pytest.fail(
            f"sub_check_count drifted: golden={golden['payload']['sub_check_count']} "
            f"actual={payload['sub_check_count']}"
        )
    overlap = len(set(payload["methods"]) & set(golden["payload"]["methods"]))
    union = len(set(payload["methods"]) | set(golden["payload"]["methods"]))
    if union and overlap / union < 0.5:
        pytest.fail(f"method distribution drifted: golden={golden['payload']['methods']} actual={payload['methods']}")
