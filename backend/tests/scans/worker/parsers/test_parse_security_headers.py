"""``parse_security_headers`` — shim JSON -> Finding[] (05-agent-team plan §9)."""

from __future__ import annotations

import json

from expects import be_empty, contain, equal, expect, have_len

from src.scans.worker.parsers.security_headers import parse_security_headers


def test_missing_headers_become_a05_findings():
    stdout = json.dumps(
        {
            "url": "https://gob.mx",
            "status": 200,
            "headers": {"x-frame-options": "DENY"},
            "missing": ["content-security-policy", "x-content-type-options"],
        }
    )

    findings = parse_security_headers(stdout)

    expect(findings).to(have_len(2))
    cats = {f.category for f in findings}
    expect(cats).to(equal({"A05"}))
    expect(findings[0].tool).to(equal("security_headers"))


def test_missing_hsts_maps_to_a02():
    stdout = json.dumps({"url": "https://gob.mx", "missing": ["strict-transport-security"]})

    findings = parse_security_headers(stdout)

    expect(findings[0].category).to(equal("A02"))


def test_grade_is_surfaced_in_evidence():
    stdout = json.dumps({"url": "https://gob.mx", "grade": "D", "missing": ["referrer-policy"]})

    findings = parse_security_headers(stdout)

    expect(findings[0].evidence.get("grade")).to(equal("D"))


def test_no_missing_headers_yields_empty():
    stdout = json.dumps({"url": "https://gob.mx", "missing": []})

    expect(parse_security_headers(stdout)).to(be_empty)


def test_shim_error_yields_empty():
    stdout = json.dumps({"url": "https://gob.mx", "error": "ConnectError: boom"})

    expect(parse_security_headers(stdout)).to(be_empty)


def test_malformed_json_returns_empty():
    expect(parse_security_headers("not json")).to(be_empty)
    expect(parse_security_headers("")).to(be_empty)


def test_affected_url_carried():
    stdout = json.dumps({"url": "https://gob.mx", "missing": ["content-security-policy"]})

    findings = parse_security_headers(stdout)

    expect(findings[0].affected_url).to(equal("https://gob.mx"))
