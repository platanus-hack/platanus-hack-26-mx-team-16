"""Unit tests for the cursor-pagination helpers (12-api §5.2). DB-less."""

from uuid import uuid4

from expects import be_none, equal, expect

from src.common.presentation.pagination import (
    CursorPage,
    SEVERITY_ORDER,
    decode_severity_cursor,
    encode_severity_cursor,
    severity_rank,
)


def test_severity_rank_orders_critical_first_info_last():
    expect(severity_rank("critical")).to(equal(0))
    expect(severity_rank("info")).to(equal(len(SEVERITY_ORDER) - 1))
    # unknown severities sort last
    expect(severity_rank("???")).to(equal(len(SEVERITY_ORDER)))


def test_severity_cursor_roundtrip():
    u = uuid4()
    cursor = encode_severity_cursor("high", u)
    sev, decoded = decode_severity_cursor(cursor)
    expect(sev).to(equal("high"))
    expect(decoded).to(equal(u))


def test_cursor_page_no_next_when_window_fits_limit():
    rows = [1, 2, 3]
    page = CursorPage.build(rows, limit=5, cursor_of=lambda x: str(x))
    expect(page.items).to(equal([1, 2, 3]))
    expect(page.next_cursor).to(be_none)


def test_cursor_page_trims_and_emits_next_cursor():
    rows = [1, 2, 3, 4]  # limit+1 fetched
    page = CursorPage.build(rows, limit=3, cursor_of=lambda x: f"cur:{x}")
    expect(page.items).to(equal([1, 2, 3]))
    # cursor derived from the last KEPT row (3), not the overflow row (4)
    expect(page.next_cursor).to(equal("cur:3"))
