"""E2: input_hash cache v3 — projection inputs enter the hash."""

from expects import equal, expect

from src.common.domain.enums.run_summary import Verdict
from src.workflows.application.analysis_run_summary import hashing
from src.workflows.application.analysis_run_summary.hashing import compute_input_hash


def _hash(**overrides):
    base = dict(
        verdict=Verdict.PASS,
        rule_results=[],
        output_schema={"type": "object"},
        synthesis_template="t",
        model="m",
    )
    base.update(overrides)
    return compute_input_hash(**base)


def test_cache_version__bumped_to_v3_so_previous_cache_is_invalidated():
    # Any v2-era cached summary must miss under the new key space.
    expect(hashing._CACHE_VERSION).to(equal("v3"))


def test_compute_input_hash__resolved_fields_change_the_hash():
    h1 = _hash(resolved_fields={"/total": 5})
    h2 = _hash(resolved_fields={"/total": 6})

    assert h1 != h2


def test_compute_input_hash__resolved_fields_none_and_empty_are_equivalent():
    expect(_hash(resolved_fields=None)).to(equal(_hash(resolved_fields={})))


def test_compute_input_hash__documents_change_the_hash_regardless_of_prompt_opt_in():
    # v3: documents are hashed ALWAYS (the projection reads them either way).
    h1 = _hash(documents=[{"fields": {"name": "Alice"}}])
    h2 = _hash(documents=[{"fields": {"name": "Bob"}}])

    assert h1 != h2
