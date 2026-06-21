"""Evidence file storage (plan §10: test_evidence_relative_url) — spec §8."""

from __future__ import annotations

from expects import be_true, contain, equal, expect

from src.scanning import evidence as evidence_mod
from src.scanning.evidence import evidence_url, write_evidence


def test_evidence_url_is_relative_and_under_static_prefix() -> None:
    url = evidence_url("scan-1", "3.png")
    expect(url).to(equal("/static/scans/scan-1/3.png"))
    # Never base64, always a relative URL under the static mount prefix.
    expect(url.startswith(evidence_mod.STATIC_SCANS_PREFIX)).to(be_true)


def test_write_evidence_writes_file_and_returns_url(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(evidence_mod, "DATA_DIR", str(tmp_path))

    url = write_evidence("scan-9", "1.png", b"\x89PNG-binary")

    expect(url).to(equal("/static/scans/scan-9/1.png"))
    written = tmp_path / "scan-9" / "1.png"
    expect(written.exists()).to(be_true)
    expect(written.read_bytes()).to(equal(b"\x89PNG-binary"))


def test_evidence_url_strips_path_traversal() -> None:
    # basename guards against ../ escaping the scan dir.
    url = evidence_url("scan-1", "../../etc/passwd")
    expect(url).to(equal("/static/scans/scan-1/passwd"))


def test_static_prefix_matches_persisted_url() -> None:
    # The persisted URL prefix and the static mount prefix must be byte-identical
    # (09's PDF embeds from the same path).
    url = evidence_url("s", "x.png")
    expect(url).to(contain(evidence_mod.STATIC_SCANS_PREFIX + "/"))
