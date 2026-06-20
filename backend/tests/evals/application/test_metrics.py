"""F11 · A5: eval-run metric aggregation."""

from expects import equal, expect

from src.evals.application.metrics import compute_metrics


def test_compute_metrics__no_outputs_is_zero_accuracy():
    result = compute_metrics([{"expected": "a"}, {"expected": "b"}], [])

    expect(result).to(equal({"count": 2, "accuracy": 0.0}))


def test_compute_metrics__exact_match_ratio():
    cases = [{"expected": "a"}, {"expected": "b"}, {"expected": "c"}]
    outputs = ["a", "x", "c"]  # 2 of 3 match

    result = compute_metrics(cases, outputs)

    expect(result).to(equal({"count": 3, "accuracy": 2 / 3}))


def test_compute_metrics__all_match_is_one():
    result = compute_metrics([{"expected": 1}, {"expected": 2}], [1, 2])

    expect(result).to(equal({"count": 2, "accuracy": 1.0}))


def test_compute_metrics__empty_cases():
    expect(compute_metrics([], [])).to(equal({"count": 0, "accuracy": 0.0}))
