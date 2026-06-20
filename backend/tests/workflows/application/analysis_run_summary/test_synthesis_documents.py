"""F7 · A4: document-aware synthesis — documents enter both prompt and hash."""

import json

from expects import equal, expect

from src.common.domain.enums.run_summary import Verdict
from src.workflows.application.analysis_run_summary.hashing import compute_input_hash
from src.workflows.infrastructure.services.run_summary.synthesizer import (
    SynthesizerInput,
    _build_user_prompt,
)


def _hash(documents):
    return compute_input_hash(
        verdict=Verdict.PASS,
        rule_results=[],
        output_schema={"type": "object"},
        synthesis_template="t",
        model="m",
        documents=documents,
    )


def test_input_hash__differs_when_document_content_differs():
    # Same verdict / rules, different document content → must NOT collide (A4).
    h1 = _hash([{"fields": {"name": "Alice"}}])
    h2 = _hash([{"fields": {"name": "Bob"}}])

    expect(h1).to_not(equal(h2))


def test_input_hash__stable_for_identical_inputs():
    docs = [{"fields": {"name": "Alice"}}]

    expect(_hash(docs)).to(equal(_hash(docs)))


def test_input_hash__none_and_empty_are_equivalent():
    expect(_hash(None)).to(equal(_hash([])))


def _input(uses_documents: bool) -> SynthesizerInput:
    return SynthesizerInput(
        tenant=None,
        verdict=Verdict.PASS,
        blocking_failures=[],
        rule_results=[],
        output_schema={"type": "object"},
        synthesis_template="t",
        documents=[{"fields": {"name": "Alice"}}],
        uses_documents=uses_documents,
    )


def test_user_prompt__includes_documents_only_when_opted_in():
    with_docs = json.loads(_build_user_prompt(_input(True)))
    without_docs = json.loads(_build_user_prompt(_input(False)))

    expect("documents" in with_docs).to(equal(True))
    expect("documents" in without_docs).to(equal(False))
