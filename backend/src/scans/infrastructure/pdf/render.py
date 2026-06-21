"""Server-side PDF render of the report (09-reporting §4.2 / spec §4).

``render_report_pdf(report, *, base_url)`` turns the **authenticated** report dict
(``ReportPresenter(public=False).to_dict``) into PDF ``bytes``. The HTML template
is the same two-layer report rendered in-app; evidence screenshots are embedded
from the static route ``base_url + /static/scans/{scan_id}/{n}.png`` (§3.3) — the
SAME prefix the worker persists in ``Finding.evidence`` and the FastAPI static
mount serves (``STATIC_SCANS_PREFIX``) — so the binary is never duplicated.

The renderer is selected by ``settings.PDF_ENGINE``:

- ``"weasyprint"`` — pure-Python HTML/CSS → PDF (Plan B, lightweight, no browser).
- ``"playwright"`` — Chromium headless ``page.pdf()`` (Plan A, full CSS/SVG).

Both engines are **lazy-imported inside this function**, so this module imports
cleanly on a host that has neither installed. The PDF E2E is therefore deferred
until the chosen engine's dependency is present (see ``newDeps``).
"""

from __future__ import annotations

import html as _html
from typing import Any

from src.common.settings import settings


class PdfEngineError(RuntimeError):
    """Raised when no PDF engine is available or the configured one is unknown."""


def _resolve_engine() -> str:
    """The configured PDF engine, lowercased, defaulting to ``weasyprint``.

    Reads ``settings.PDF_ENGINE`` defensively via ``getattr`` so this module
    imports/runs even before the orchestrator adds ``PDF_ENGINE`` to settings.py
    (see settingsAdditions). Factored out so tests can override the engine without
    mutating the strict pydantic ``Settings`` model.
    """
    return str(getattr(settings, "PDF_ENGINE", "weasyprint") or "weasyprint").lower()


def _esc(value: Any) -> str:
    """HTML-escape a scalar for safe interpolation into the template."""
    return _html.escape("" if value is None else str(value))


def render_report_html(report: dict[str, Any], *, base_url: str) -> str:
    """Render the two-layer report dict to a self-contained print HTML string.

    Pure (no I/O, no engine) so it is cheap to unit-test: it asserts the template
    references the static screenshot route and never crashes on a minimal report.
    Raises ``KeyError`` if ``executive``/``technical`` are missing — a malformed
    report fails loud rather than producing a blank PDF.
    """
    executive = report["executive"]
    technical = report["technical"]
    meta = report.get("meta", {})

    base = base_url.rstrip("/")
    scan_id = meta.get("scanId", "")
    # Single source of truth for the evidence URL prefix: the same constant the
    # worker persists into Finding.evidence and the FastAPI static mount serves.
    # Read defensively so a malformed/relative shot path still resolves and so
    # this module imports cleanly where settings lacks the key.
    prefix = str(
        getattr(settings, "STATIC_SCANS_PREFIX", "/static/scans") or "/static/scans"
    ).strip("/")

    badges = "".join(
        f'<span class="badge">{_esc(b)}</span>' for b in executive.get("badges", [])
    )

    risks = "".join(
        f'<li><strong>{_esc(r.get("title"))}</strong> '
        f'({_esc(r.get("severity"))}) — {_esc(r.get("whyItMatters"))}</li>'
        for r in executive.get("topRisks", [])
    )

    surface = "".join(
        f'<li>{_esc(s.get("type"))} — {_esc(s.get("vendor"))} '
        f'@ {_esc(s.get("locationUrl"))}</li>'
        for s in executive.get("agenticSurface", [])
    )

    finding_blocks: list[str] = []
    for finding in technical.get("findings", []):
        screenshots = ""
        evidence = finding.get("evidence")
        if isinstance(evidence, dict):
            for shot in evidence.get("screenshots", []) or []:
                # Embed evidence images from the static route so the PDF reuses the
                # exact same binary the in-app report serves (§3.3). If the stored
                # screenshot is already a full evidence URL (begins with the static
                # prefix), embed it as-is rather than double-prefixing.
                shot_str = str(shot)
                if shot_str.startswith(f"/{prefix}/") or shot_str.startswith(
                    f"{prefix}/"
                ):
                    src = f"{base}/{shot_str.lstrip('/')}"
                else:
                    src = f"{base}/{prefix}/{_esc(scan_id)}/{_esc(shot)}"
                screenshots += f'<img class="evidence" src="{src}" />'
        redacted = (
            '<p class="redacted">Evidencia oculta en el reporte público</p>'
            if finding.get("evidenceRedacted")
            else ""
        )
        finding_blocks.append(
            "<section class='finding'>"
            f"<h3>{_esc(finding.get('severity'))} · "
            f"{_esc(finding.get('category'))} — {_esc(finding.get('title'))}</h3>"
            f"<p><b>Impacto:</b> {_esc(finding.get('impact'))}</p>"
            f"<p><b>Remediación:</b> {_esc(finding.get('remediation'))}</p>"
            f"{redacted}{screenshots}"
            "</section>"
        )

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"/>
<style>
  body {{ font-family: sans-serif; color: #1a1f1f; }}
  .grade {{ font-size: 64px; font-weight: 700; }}
  .badge {{ display:inline-block; padding:2px 8px; border:1px solid #999; border-radius:6px; margin-right:6px; }}
  .finding {{ border-top: 1px solid #ddd; padding: 8px 0; }}
  .evidence {{ max-width: 100%; }}
  .redacted {{ color:#888; font-style: italic; }}
</style></head>
<body>
  <header>
    <div class="grade">{_esc(executive.get("overallGrade"))}</div>
    <p>🛡️ Web: {_esc(executive.get("webScore"))} · 🤖 Agéntico: {_esc(executive.get("agenticScore"))}</p>
    <p>{badges}</p>
  </header>
  <section><h2>Owliver te explica</h2><p>{_esc(executive.get("narrative"))}</p></section>
  <section><h2>Top 3 riesgos</h2><ol>{risks}</ol></section>
  <section><h2>Superficie agéntica</h2><ul>{surface}</ul></section>
  <section><h2>Hallazgos técnicos</h2>{''.join(finding_blocks)}</section>
</body></html>"""


def render_report_pdf(report: dict[str, Any], *, base_url: str) -> bytes:
    """Render the report dict to PDF ``bytes`` via ``settings.PDF_ENGINE``.

    The renderer is lazy-imported so this module never hard-depends on a PDF
    library at import time. Raises :class:`PdfEngineError` if the configured
    engine is unknown or its dependency is not installed.
    """
    document = render_report_html(report, base_url=base_url)
    engine = _resolve_engine()

    if engine == "weasyprint":
        try:
            from weasyprint import HTML  # type: ignore[import-not-found]

            return HTML(string=document, base_url=base_url).write_pdf()
        except ImportError as exc:  # pragma: no cover - dep not installed on host
            raise PdfEngineError(
                "PDF_ENGINE=weasyprint but 'weasyprint' is not installed."
            ) from exc
        except OSError as exc:  # pragma: no cover - native libs missing on host
            # WeasyPrint dlopen's Pango/Cairo/GObject at render time; a half-install
            # (wheel present, system libs absent) raises OSError. Map it to the same
            # clean 503 as a missing dependency instead of a 500 — the PDF is a
            # recortable deliverable, not a hard requirement.
            raise PdfEngineError(
                "PDF_ENGINE=weasyprint but its native libraries "
                f"(Pango/Cairo/GObject) are unavailable: {exc}"
            ) from exc

    if engine == "playwright":
        return _render_with_playwright(document)

    raise PdfEngineError(f"Unknown PDF_ENGINE={engine!r} (use weasyprint|playwright).")


def _render_with_playwright(document: str) -> bytes:
    """Chromium headless print-to-PDF (Plan A). Lazy-imported."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - dep not installed on host
        raise PdfEngineError(
            "PDF_ENGINE=playwright but 'playwright' is not installed."
        ) from exc

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(document, wait_until="networkidle")
            return page.pdf(print_background=True)
        finally:
            browser.close()
