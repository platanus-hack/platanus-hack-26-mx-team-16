"""File-based evidence storage (spec §8, plan §7).

Screenshots/artefacts of each finding are written as FILES into the shared volume
``/data/scans/{scan_id}/{n}.png`` and served by a FastAPI static route. The
``evidence`` jsonb field of a ``Finding`` (shape owned by 06) stores the RELATIVE
URL, never the binary:

- NO base64 in jsonb (inflates the DB).
- NO MinIO (useless extra service for the demo).

The persisted URL and the static mount prefix MUST be byte-identical so the PDF
export (09) embeds from the same path. ``STATIC_SCANS_PREFIX`` / ``DATA_DIR`` are
the single source for both sides.
"""

from __future__ import annotations

import os
from pathlib import Path

from src.common.settings import settings

#: Root dir of the shared scans volume on the worker/API (mounts the host
#: ``/data/scans``). Read from settings with a stable default.
DATA_DIR: str = getattr(settings, "SCAN_DATA_DIR", "/data/scans")

#: URL prefix the static mount serves the volume under. The persisted relative
#: evidence URL begins with this prefix; 09's PDF export reuses it byte-for-byte.
STATIC_SCANS_PREFIX: str = getattr(settings, "STATIC_SCANS_PREFIX", "/static/scans")


def scan_dir(scan_id: object) -> Path:
    """Absolute on-disk directory for a scan's evidence (``/data/scans/{id}``)."""
    return Path(DATA_DIR) / str(scan_id)


def ensure_scan_dir(scan_id: object) -> Path:
    """Create (if needed) and return the scan's evidence directory.

    DooD scanners (ZAP baseline/full-active) bind-mount this host dir at
    ``/zap/wrk`` and run as a NON-root user (uid 1000); make it world-writable so
    they can write their report/yaml there (otherwise ZAP exits with
    ``Permission denied`` and the scan flips to partial coverage).
    """
    path = scan_dir(scan_id)
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o777)
    return path


def evidence_url(scan_id: object, filename: str) -> str:
    """Relative URL stored in ``Finding.evidence`` (``/static/scans/{id}/{name}``).

    This is what gets persisted into jsonb — NEVER the binary. Byte-identical to
    what the static mount serves and what 09 embeds in the PDF.
    """
    name = os.path.basename(filename)
    return f"{STATIC_SCANS_PREFIX}/{scan_id}/{name}"


def write_evidence(scan_id: object, filename: str, data: bytes) -> str:
    """Write ``data`` to ``/data/scans/{id}/{filename}`` and return its relative URL.

    Returns the relative URL to store in ``Finding.evidence`` (NOT base64). The
    caller (05 when capturing a screenshot/artefact) persists only this string.
    """
    directory = ensure_scan_dir(scan_id)
    name = os.path.basename(filename)
    (directory / name).write_bytes(data)
    return evidence_url(scan_id, name)


def mount_static_scans(app: object) -> None:
    """Mount the scans evidence volume as a FastAPI static route (spec §8).

    Idempotent and lazy-importing ``StaticFiles`` so this module imports cleanly
    even where FastAPI/Starlette is not installed. The directory is created if
    missing so the mount never fails on a fresh host.
    """
    from starlette.staticfiles import StaticFiles  # lazy: keep module import light

    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    app.mount(  # type: ignore[attr-defined]
        STATIC_SCANS_PREFIX,
        StaticFiles(directory=DATA_DIR, check_dir=False),
        name="scans-evidence",
    )
