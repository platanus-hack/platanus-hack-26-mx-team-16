"""Cost & latency benchmarks (LLM real, no falla).

Mide latencia + tokens aproximados por ejemplo, persiste a
`tests/fixtures/workflow_rules/benchmarks/<provider>/<model>/<ts>.json` y
emite un reporte resumen `report-latest.md`.

Este suite NUNCA falla — solo mide y reporta. Útil para presupuesto en
prod y para detectar regresiones de eficiencia.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

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
    stub_kb_resolver,
)


pytestmark = pytest.mark.llm


def _bench_root() -> Path:
    provider, model = llm_default_model().split(":", 1)
    base = FIXTURES_ROOT / "benchmarks" / provider / model
    base.mkdir(parents=True, exist_ok=True)
    return base


def _approx_tokens(text: str) -> int:
    # 1 token ≈ 4 chars heuristic — good enough for trend detection.
    return max(1, len(text) // 4)


def _load_validation_fixtures() -> list[dict]:
    base = FIXTURES_ROOT / "validation"
    out = []
    for d in sorted((p for p in base.glob("v*") if p.is_dir()), key=lambda p: int(p.name[1:])):
        rule = json.loads((d / "rule.json").read_text())
        rule["_dir"] = d.name
        out.append(rule)
    return out


def _load_derivation_fixtures() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted((FIXTURES_ROOT / "derivation").glob("d*.json"))]


def _filter_subset(items, key_fn):
    subset = llm_subset()
    if subset is None:
        return items
    return [it for it in items if key_fn(it).lower() in subset]


_VAL_FIXTURES = _filter_subset(_load_validation_fixtures(), lambda f: f["id"])
_DER_FIXTURES = _filter_subset(_load_derivation_fixtures(), lambda f: f["id"])


_SAMPLES: list[dict] = []


@pytest.fixture(scope="module", autouse=True)
def _flush_benchmarks_at_end(request):  # noqa: ARG001
    yield
    if not _SAMPLES:
        return
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = _bench_root() / f"{ts}.json"
    out_path.write_text(json.dumps({"samples": _SAMPLES, "model": llm_default_model()}, indent=2, ensure_ascii=False))

    total_in = sum(s["tokens_in"] for s in _SAMPLES)
    total_out = sum(s["tokens_out"] for s in _SAMPLES)
    p50 = sorted(s["latency_ms"] for s in _SAMPLES)[len(_SAMPLES) // 2]
    p95 = sorted(s["latency_ms"] for s in _SAMPLES)[max(0, int(len(_SAMPLES) * 0.95) - 1)]
    md = (
        f"# Benchmarks — {llm_default_model()} @ {ts}\n\n"
        f"- Samples: {len(_SAMPLES)}\n"
        f"- Total tokens_in (approx): {total_in}\n"
        f"- Total tokens_out (approx): {total_out}\n"
        f"- Latency p50: {p50:.1f} ms · p95: {p95:.1f} ms\n\n"
        "| id | kind | latency_ms | tokens_in | tokens_out |\n"
        "|---|---|---:|---:|---:|\n"
    )
    md += "\n".join(
        f"| {s['id']} | {s['kind']} | {s['latency_ms']:.1f} | {s['tokens_in']} | {s['tokens_out']} |" for s in _SAMPLES
    )
    (_bench_root() / "report-latest.md").write_text(md)


@pytest.mark.parametrize("fixture", _VAL_FIXTURES, ids=lambda f: f["id"])
async def test_validation_compile_benchmark(fixture):
    rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name=fixture["name"],
        kind="VALIDATION",
        prompt=fixture["rule"]["prompt"],
        config=fixture["rule"]["config"],
    )
    workflow_id, tenant_id = uuid4(), uuid4()
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=doctypes_from_slugs(fixture["available_doctypes"], workflow_id, tenant_id),
        kb_resolver=stub_kb_resolver(fixture.get("kb_slugs", [])),
    )
    parser = ValidationParser(llm_runner=AgnoLLMRunner(model_id=llm_default_model()))

    started = time.time()
    try:
        outcome = await ValidationKind(parser=parser).compile(rule, ctx)
        artifact_text = json.dumps(outcome.artifact, ensure_ascii=False)
    except Exception as exc:
        artifact_text = json.dumps({"error": str(exc)})
    elapsed = (time.time() - started) * 1000

    _SAMPLES.append(
        {
            "id": fixture["id"],
            "kind": "VALIDATION",
            "latency_ms": elapsed,
            "tokens_in": _approx_tokens(rule.prompt),
            "tokens_out": _approx_tokens(artifact_text),
        }
    )


@pytest.mark.parametrize("fixture", _DER_FIXTURES, ids=lambda f: f["id"])
async def test_derivation_compile_benchmark(fixture):
    rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name=fixture["name"],
        kind="DERIVATION",
        prompt=fixture["rule"]["prompt"],
        config=fixture["rule"]["config"],
    )
    workflow_id, tenant_id = uuid4(), uuid4()
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=doctypes_from_slugs(fixture["available_doctypes"], workflow_id, tenant_id),
        kb_resolver=stub_kb_resolver(fixture.get("kb_slugs", [])),
    )

    started = time.time()
    outcome = await DerivationKind().compile(rule, ctx)
    elapsed = (time.time() - started) * 1000

    artifact_text = json.dumps(outcome.artifact, ensure_ascii=False)
    _SAMPLES.append(
        {
            "id": fixture["id"],
            "kind": "DERIVATION",
            "latency_ms": elapsed,
            "tokens_in": _approx_tokens(rule.prompt),
            "tokens_out": _approx_tokens(artifact_text),
        }
    )
