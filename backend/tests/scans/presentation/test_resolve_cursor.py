"""``_resolve_cursor`` precedence (spec §3.1): Last-Event-ID > ?since_seq= > 0."""

from expects import equal, expect

from src.scans.presentation.endpoints.stream_scan import _resolve_cursor


def test_last_event_id_numeric_wins_over_since_seq():
    expect(_resolve_cursor("42", 7)).to(equal(42))


def test_last_event_id_absent_falls_back_to_since_seq():
    expect(_resolve_cursor(None, 7)).to(equal(7))


def test_both_absent_is_zero():
    expect(_resolve_cursor(None, None)).to(equal(0))


def test_last_event_id_non_numeric_falls_back_to_since_seq():
    expect(_resolve_cursor("not-a-number", 7)).to(equal(7))


def test_last_event_id_non_numeric_and_no_since_seq_is_zero():
    expect(_resolve_cursor("x", None)).to(equal(0))
