"""``parse_nuclei`` — JSONL stdout -> Finding[] (05-agent-team plan §9).

Pure unit tests over trimmed real-shaped nuclei ``-jsonl`` lines. No DB, no LLM.
"""

from __future__ import annotations

import json

from expects import be_empty, be_none, equal, expect, have_len

from src.scans.worker.parsers.nuclei import parse_nuclei


def _line(**over) -> str:
    entry = {
        "template-id": "CVE-2021-1234",
        "matched-at": "https://gob.mx/login",
        "info": {
            "name": "Example Vuln",
            "severity": "high",
            "tags": ["cve", "sqli"],
            "classification": {"cvss-score": 8.8, "cwe-id": ["CWE-89"]},
        },
    }
    entry.update(over)
    return json.dumps(entry)


def test_maps_severity_cvss_and_category_from_cwe():
    stdout = _line()

    findings = parse_nuclei(stdout)

    expect(findings).to(have_len(1))
    f = findings[0]
    expect(f.severity).to(equal("high"))
    expect(f.cvss).to(equal(8.8))
    expect(f.category).to(equal("A03"))  # CWE-89 SQLi -> A03
    expect(f.tool).to(equal("nuclei"))
    expect(f.source).to(equal("owasp"))
    expect(f.affected_url).to(equal("https://gob.mx/login"))


def test_unknown_severity_falls_back_to_info():
    stdout = _line(info={"name": "x", "severity": "bogus", "classification": {}})

    findings = parse_nuclei(stdout)

    expect(findings[0].severity).to(equal("info"))


def test_category_falls_back_to_tag_then_default():
    # No CWE; tag "ssl" -> A02.
    stdout = _line(info={"name": "x", "severity": "low", "tags": ["ssl"], "classification": {}})

    findings = parse_nuclei(stdout)

    expect(findings[0].category).to(equal("A02"))


def test_no_cwe_no_known_tag_defaults_to_a05():
    stdout = _line(info={"name": "x", "severity": "low", "tags": ["weirdtag"], "classification": {}})

    findings = parse_nuclei(stdout)

    expect(findings[0].category).to(equal("A05"))


def test_missing_cvss_yields_none():
    stdout = _line(info={"name": "x", "severity": "medium", "classification": {}})

    findings = parse_nuclei(stdout)

    expect(findings[0].cvss).to(be_none)


def test_empty_input_returns_empty_list():
    expect(parse_nuclei("")).to(be_empty)
    expect(parse_nuclei("\n  \n")).to(be_empty)


def test_malformed_line_is_skipped_not_fatal():
    stdout = "\n".join(["{not json", _line(), "also bad"])

    findings = parse_nuclei(stdout)

    expect(findings).to(have_len(1))


def test_multiple_lines_each_become_a_finding():
    stdout = "\n".join([_line(), _line(**{"template-id": "T2"})])

    findings = parse_nuclei(stdout)

    expect(findings).to(have_len(2))
