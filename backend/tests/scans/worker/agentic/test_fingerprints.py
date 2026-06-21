"""Pass-1 fingerprint matching — deterministic, no LLM (spec §2.1, plan §3.1).

``match_fingerprints`` must detect known vendors by script-host, window-global and
launcher selector; a DOM with no signal returns ``[]``; the ~12-vendor JSON loads
and validates its shape.
"""

from __future__ import annotations

from expects import be_empty, contain, equal, expect, have_len

from src.scans.worker.agentic.detector import (
    AgenticSurface,
    load_fingerprints,
    match_fingerprints,
)


def test_fingerprint_table_loads_at_least_twelve_vendors():
    vendors = load_fingerprints()
    expect(len(vendors) >= 12).to(equal(True))
    names = {fp.vendor for fp in vendors}
    for expected in ("Intercom", "Zendesk", "Drift", "Tidio", "Crisp"):
        expect(names).to(contain(expected))


def test_fingerprint_shape_is_valid():
    for fp in load_fingerprints():
        expect(isinstance(fp.script_hosts, list)).to(equal(True))
        expect(isinstance(fp.window_globals, list)).to(equal(True))
        expect(isinstance(fp.launcher_selectors, list)).to(equal(True))


def test_intercom_detected_by_script_host():
    dom = '<script src="https://js.intercomcdn.com/frame.js"></script>'
    surfaces = match_fingerprints(dom, network=None, location_url="https://x.gob.mx")
    expect(surfaces).to(have_len(1))
    surface = surfaces[0]
    expect(surface.vendor).to(equal("Intercom"))
    expect(surface.type).to(equal("chatbot"))
    expect(surface.confidence).to(equal("alta"))


def test_zendesk_detected_by_window_global():
    surfaces = match_fingerprints(
        "<html></html>", network=None, window_globals=["$zopim"]
    )
    expect([s.vendor for s in surfaces]).to(contain("Zendesk"))


def test_drift_detected_by_network_host():
    surfaces = match_fingerprints(
        "<html></html>", network=["https://js.driftt.com/core.js"]
    )
    expect([s.vendor for s in surfaces]).to(contain("Drift"))


def test_tidio_detected_by_script_host():
    dom = '<script src="https://code.tidio.co/abc.js"></script>'
    surfaces = match_fingerprints(dom, network=None)
    expect([s.vendor for s in surfaces]).to(contain("Tidio"))


def test_launcher_selector_literal_in_dom_matches():
    # The selector-substring signal hits when a vendor selector literal appears in
    # the DOM (e.g. an inline class reference), exercising the third signal type.
    dom = "<style>.crisp-client{display:block}</style>"
    surfaces = match_fingerprints(dom, network=None)
    expect([s.vendor for s in surfaces]).to(contain("Crisp"))


def test_crisp_detected_by_dict_network_entry():
    surfaces = match_fingerprints(
        "<html></html>", network=[{"url": "https://client.crisp.chat/l.js"}]
    )
    expect([s.vendor for s in surfaces]).to(contain("Crisp"))


def test_no_signal_returns_empty():
    surfaces = match_fingerprints(
        "<html><body>hello</body></html>", network=["https://example.com/app.js"]
    )
    expect(surfaces).to(be_empty)


def test_surface_is_the_internal_dataclass():
    dom = '<script src="https://client.crisp.chat/l.js"></script>'
    surfaces = match_fingerprints(dom, network=None)
    expect(isinstance(surfaces[0], AgenticSurface)).to(equal(True))
