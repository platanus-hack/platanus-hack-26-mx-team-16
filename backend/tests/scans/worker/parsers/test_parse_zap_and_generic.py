"""ZAP baseline + generic (nikto/sqlmap) parsers (05-agent-team plan §9)."""

from __future__ import annotations

import json

from expects import be_empty, equal, expect, have_len

from src.scans.worker.parsers.generic import parse_nikto, parse_sqlmap
from src.scans.worker.parsers.zap import parse_zap_baseline


def test_zap_flattens_alerts_and_maps_riskcode():
    stdout = json.dumps(
        {
            "site": [
                {
                    "alerts": [
                        {
                            "name": "SQL Injection",
                            "riskcode": "3",
                            "confidence": "3",
                            "desc": "<p>bad</p>",
                            "solution": "<p>fix it</p>",
                            "cweid": "89",
                            "instances": [{"uri": "https://gob.mx/x?id=1", "param": "id"}],
                        },
                        {"name": "Info leak", "riskcode": "0", "instances": []},
                    ]
                }
            ]
        }
    )

    findings = parse_zap_baseline(stdout)

    expect(findings).to(have_len(2))
    high = findings[0]
    expect(high.severity).to(equal("high"))
    expect(high.category).to(equal("A03"))  # cweid 89
    expect(high.param).to(equal("id"))
    expect(high.affected_url).to(equal("https://gob.mx/x?id=1"))
    expect(high.description).to(equal("bad"))  # html stripped


def test_zap_malformed_returns_empty():
    expect(parse_zap_baseline("{bad")).to(be_empty)
    expect(parse_zap_baseline("")).to(be_empty)


def test_sqlmap_emits_high_a03_on_hit():
    stdout = "Parameter 'id' is vulnerable. Do you want to keep testing?"

    findings = parse_sqlmap(stdout, affected_url="https://gob.mx/x?id=1")

    expect(findings).to(have_len(1))
    expect(findings[0].severity).to(equal("high"))
    expect(findings[0].category).to(equal("A03"))
    expect(findings[0].confidence).to(equal("baja"))


def test_sqlmap_no_hit_returns_empty():
    expect(parse_sqlmap("all tested parameters do not appear to be injectable")).to(be_empty)
    expect(parse_sqlmap("")).to(be_empty)


def test_nikto_summarizes_items():
    stdout = "\n".join(
        [
            "+ Target IP: 1.2.3.4",
            "+ Server: nginx",
            "+ /admin/: Directory indexing found.",
            "+ /backup.zip: Potentially interesting backup file.",
        ]
    )

    findings = parse_nikto(stdout, affected_url="https://gob.mx")

    expect(findings).to(have_len(1))
    expect(findings[0].severity).to(equal("medium"))
    expect(findings[0].category).to(equal("A05"))
    expect(findings[0].evidence["total"]).to(equal(2))  # banner lines excluded


def test_nikto_no_items_returns_empty():
    expect(parse_nikto("+ Target IP: 1.2.3.4\n+ Server: nginx")).to(be_empty)
    expect(parse_nikto("")).to(be_empty)
