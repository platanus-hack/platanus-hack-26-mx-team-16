"""``owasp_map`` — static category mapping (05-agent-team plan §9).

template-id/cwe/probe -> exact category; unmapped -> deterministic fallback, never
an exception.
"""

from __future__ import annotations

from expects import be_none, equal, expect

from src.scans.worker.parsers import owasp_map


def test_cwe_maps_to_exact_category():
    expect(owasp_map.category_for_cwe(89)).to(equal("A03"))  # SQLi
    expect(owasp_map.category_for_cwe(79)).to(equal("A03"))  # XSS
    expect(owasp_map.category_for_cwe(327)).to(equal("A02"))  # crypto
    expect(owasp_map.category_for_cwe(918)).to(equal("A10"))  # SSRF


def test_cwe_accepts_string_and_prefixed_forms():
    expect(owasp_map.category_for_cwe("89")).to(equal("A03"))
    expect(owasp_map.category_for_cwe("CWE-89")).to(equal("A03"))


def test_unmapped_cwe_returns_none():
    expect(owasp_map.category_for_cwe(999999)).to(be_none)
    expect(owasp_map.category_for_cwe(None)).to(be_none)
    expect(owasp_map.category_for_cwe("not-a-number")).to(be_none)


def test_nuclei_tags_pick_first_match():
    expect(owasp_map.category_for_nuclei_tags(["misc", "sqli"])).to(equal("A03"))
    expect(owasp_map.category_for_nuclei_tags(["ssl"])).to(equal("A02"))
    expect(owasp_map.category_for_nuclei_tags(["unknown"])).to(be_none)
    expect(owasp_map.category_for_nuclei_tags([])).to(be_none)


def test_header_mapping_with_default():
    expect(owasp_map.category_for_header("strict-transport-security")).to(equal("A02"))
    expect(owasp_map.category_for_header("content-security-policy")).to(equal("A05"))
    expect(owasp_map.category_for_header("x-made-up")).to(equal("A05"))  # default
    expect(owasp_map.category_for_header(None)).to(equal("A05"))


def test_web_category_precedence_cwe_then_tag_then_default():
    # CWE wins over tag.
    expect(owasp_map.web_category(cwe=89, tags=["ssl"])).to(equal("A03"))
    # No CWE -> tag.
    expect(owasp_map.web_category(cwe=None, tags=["ssl"])).to(equal("A02"))
    # Nothing -> default A05.
    expect(owasp_map.web_category()).to(equal("A05"))
