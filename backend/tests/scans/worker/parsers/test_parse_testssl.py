"""``parse_testssl`` — testssl JSON -> Finding[] (05-agent-team plan §9)."""

from __future__ import annotations

import json

from expects import be_empty, contain, equal, expect, have_len

from src.scans.worker.parsers.testssl import parse_testssl


def test_keeps_weaknesses_and_maps_crypto_to_a02():
    stdout = json.dumps(
        [
            {"id": "SSLv3", "severity": "HIGH", "finding": "SSLv3 offered"},
            {"id": "cipher_x", "severity": "MEDIUM", "finding": "weak cipher"},
            {"id": "service", "severity": "INFO", "finding": "HTTP server banner"},
            {"id": "scanTime", "severity": "OK", "finding": "fine"},
        ]
    )

    findings = parse_testssl(stdout)

    expect(findings).to(have_len(2))  # INFO/OK dropped
    severities = sorted(f.severity for f in findings)
    expect(severities).to(equal(["high", "medium"]))
    expect([f.category for f in findings]).to(contain("A02"))
    expect(findings[0].tool).to(equal("testssl"))


def test_hsts_id_maps_to_a02_header():
    stdout = json.dumps([{"id": "HSTS_time", "severity": "LOW", "finding": "HSTS too short"}])

    findings = parse_testssl(stdout)

    expect(findings[0].category).to(equal("A02"))


def test_malformed_json_returns_empty_not_raises():
    expect(parse_testssl("{not json")).to(be_empty)


def test_empty_input_returns_empty():
    expect(parse_testssl("")).to(be_empty)
    expect(parse_testssl("   ")).to(be_empty)


def test_only_ok_info_records_yields_empty():
    stdout = json.dumps([{"id": "x", "severity": "OK", "finding": "ok"}])

    expect(parse_testssl(stdout)).to(be_empty)
