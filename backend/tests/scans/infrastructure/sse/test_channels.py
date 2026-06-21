"""``scan_events_channel`` — single source of truth for the channel name (10 §3.1)."""

from uuid import uuid4

from expects import equal, expect

from src.scans.infrastructure.sse.channels import scan_events_channel


def test_channel_is_scan_id_events():
    scan_id = uuid4()
    expect(scan_events_channel(scan_id)).to(equal(f"scan:{scan_id}:events"))


def test_channel_accepts_str_scan_id():
    expect(scan_events_channel("abc-123")).to(equal("scan:abc-123:events"))
