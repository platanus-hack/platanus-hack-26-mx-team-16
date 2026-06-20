"""Shared fixtures and helpers for the workflows integration suite.

The non-LLM `test_compile_to_synthesis_contract.py` runs as part of
`make test`. Everything under `llm/` carries the `llm` marker and runs
only via `make test_llm` (or `make test_all`).

Knobs (env vars used by some tests, all optional):

- `LLM_TEST_MODEL=openai:gpt-4o-mini` (default model passed to AgnoLLMRunner)
- `LLM_TEST_PROVIDERS=openai,anthropic,google` (multi-provider matrix)
- `LLM_TEST_SUBSET=v1,d4` (limits the parametrized fixtures)
- `LLM_DETERMINISM_RUNS=5` (N runs per case in the determinism suite)
- `RECORD_LLM_GOLDEN=1` (overwrite the golden fixtures from the live run)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest

from src.common.domain.models.knowledge_base.kb_document import KBDocument
from src.common.domain.models.processing.document_type import DocumentType


FIXTURES_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "workflow_rules"


def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def record_llm_golden() -> bool:
    return _flag("RECORD_LLM_GOLDEN")


def llm_subset() -> set[str] | None:
    raw = os.environ.get("LLM_TEST_SUBSET", "").strip()
    if not raw:
        return None
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def llm_default_model() -> str:
    return os.environ.get("LLM_TEST_MODEL", "openai:gpt-4o-mini")


def llm_test_providers() -> list[str]:
    raw = os.environ.get("LLM_TEST_PROVIDERS", "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def llm_determinism_runs() -> int:
    raw = os.environ.get("LLM_DETERMINISM_RUNS", "5")
    try:
        return max(2, int(raw))
    except ValueError:
        return 5


@pytest.fixture
def derivation_fixtures() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted((FIXTURES_ROOT / "derivation").glob("d*.json"))]


@pytest.fixture
def validation_fixture_dirs() -> list[Path]:
    base = FIXTURES_ROOT / "validation"
    return sorted((p for p in base.glob("v*") if p.is_dir()), key=lambda p: int(p.name[1:]))


@dataclass
class StubKBResolver:
    """Minimal KB resolver: returns a fake KBDocument per slug, deterministic uuid."""

    slug_to_uuid: dict[str, str]

    async def resolve(self, tenant_id, workflow_id, slugs):  # noqa: ARG002
        return {
            slug: KBDocument(
                uuid=self.slug_to_uuid[slug],
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                slug=slug,
                file_name=f"{slug}.txt",
                mime="text/plain",
            )
            for slug in slugs
            if slug in self.slug_to_uuid
        }


def stub_kb_resolver(kb_slugs: list[str]) -> StubKBResolver | None:
    if not kb_slugs:
        return None
    return StubKBResolver({slug: str(uuid4()) for slug in kb_slugs})


def doctypes_from_slugs(slugs: list[str], workflow_id, tenant_id) -> list[DocumentType]:
    return [
        DocumentType(
            uuid=uuid4(),
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            name=slug.title(),
            slug=slug,
        )
        for slug in slugs
    ]
