"""Legal/ethics constants — single source of truth (spec §2.5, §4).

These are imported by the worker (04), the API (12) and the robots policy so the
identifiable User-Agent and the two distinct rate limits are defined **once**.
"""

from __future__ import annotations

from typing import Final

# §2.5 — identifiable User-Agent emitted on EVERY outgoing scan/robots request so
# the operator of a scanned site can identify and contact the traffic origin.
# Imported by the worker (04, ``run_tool``) and by the robots policy.
SCANNER_USER_AGENT: Final[str] = "Owliver-Scanner/1.0 (+contacto)"

# §4.1 — API rate limit, per user, on ``POST /scans``: 5 scans / hour.
# ``(limit, window_seconds)``. 12-api feeds this into the existing Redis
# ``create_rate_limit_dependency`` factory (fixed_window: INCR + TTL). NOT slowapi.
API_SCAN_RATE_LIMIT: Final[tuple[int, int]] = (5, 3600)

# §4.2 — worker (per-target) rate limits, applied by 04 in ``run_tool()``.
# Nuclei ``-rl`` requests/second toward the target.
WORKER_NUCLEI_RATE: Final[int] = 150

# §4.2 — delay (milliseconds) between requests for ``ffuf`` / ``katana`` toward
# the target. Minimizes impact on the scanned host.
WORKER_REQUEST_DELAY_MS: Final[int] = 200
