"""``TOOL_SPECS`` — the canonical tool -> mechanism -> timeout -> memory table.

Single source of truth for the per-tool execution mechanics (spec §4.2, plan
§3.3). No timeout/memory/mechanism literal lives anywhere else in the engine:
``run_tool`` reads everything from the ``ToolSpec`` resolved here, keyed by the
02-owned :class:`ToolId`.

Ownership split: 02 owns *which* tools+flags run per ``(is_gov, level)`` (the
whitelist); 04 (here) owns *how* each tool runs (mechanism, hard timeout, memory,
docker image, mount path). The ``flags`` of a :class:`ToolInvocation` are logical
policy; the operational argv (``-duc``, ``-rl``, ``-v`` host path...) is appended
by ``run_tool`` from the matching ``ToolSpec``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from src.scans.domain.enums.tool_id import ToolId

# Extra wall-clock head-room added to a DooD ``docker run`` on top of the tool's
# logical timeout, to cover container create/teardown overhead before SIGKILL.
DOCKER_OVERHEAD_S: int = 15


class ToolMechanism(StrEnum):
    """How ``run_tool`` invokes a given tool (spec §3)."""

    #: Light CLI preinstalled in the fat ``scanners`` image -> ``subprocess.run``.
    SUBPROCESS = "subprocess"
    #: Heavy container (ZAP / hexstrike) -> sibling ``docker run`` via host socket.
    DOOD = "dood"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Execution contract for a single tool (spec §4.2).

    ``timeout_s`` is the HARD per-tool timeout fed to ``subprocess.run(timeout=)``
    or, for DooD, to the ``docker run`` watchdog (``timeout_s + DOCKER_OVERHEAD_S``).
    ``memory`` / ``cpus`` apply only to DooD (``--memory`` / ``--cpus``). ``image``
    is the *pinned* tag of the sibling container (NEVER ``:latest``, spec §7).
    ``mount`` is the in-container path the host shared dir is bind-mounted to.
    ``rate_limited`` marks tools that get ``-rl WORKER_NUCLEI_RATE`` injected;
    ``request_delay`` marks tools that get the ``WORKER_REQUEST_DELAY_MS`` delay.
    ``disable_update_check`` marks nuclei (gets ``-duc`` to avoid the first-run DNS
    failure, spec §7).
    """

    tool: ToolId
    mechanism: ToolMechanism
    timeout_s: int
    memory: str | None = None  # e.g. "2g" — DooD only
    cpus: str | None = None
    image: str | None = None  # pinned tag — DooD only
    mount: str | None = None  # in-container mount of host_shared_dir — DooD only
    rate_limited: bool = False  # inject -rl WORKER_NUCLEI_RATE
    request_delay: bool = False  # inject the per-request delay (ffuf/katana)
    disable_update_check: bool = False  # nuclei -duc (spec §7)
    base_argv: tuple[str, ...] = field(default=())  # leading argv before flags

    @property
    def is_dood(self) -> bool:
        return self.mechanism is ToolMechanism.DOOD

    @property
    def docker_timeout_s(self) -> int:
        """Wall-clock timeout for the ``docker run`` (logical + overhead)."""
        return self.timeout_s + DOCKER_OVERHEAD_S


def _spec(tool: ToolId, mechanism: ToolMechanism, timeout_s: int, **kw: object) -> ToolSpec:
    return ToolSpec(tool=tool, mechanism=mechanism, timeout_s=timeout_s, **kw)  # type: ignore[arg-type]


_SUB = ToolMechanism.SUBPROCESS
_DOOD = ToolMechanism.DOOD

# Pinned image tags for DooD siblings (spec §7: NEVER ``:latest``).
ZAP_IMAGE = "zaproxy/zap-stable:2.15.0"
HEXSTRIKE_IMAGE = "hexstrike/hexstrike-ai:stable"

# Canonical table (spec §4.2 / plan §3.3). ``base_argv`` is the leading argv of the
# tool's command; the whitelist flags (02) and operational flags (-duc/-rl/delay)
# are layered on by ``run_tool``.
_SPECS: tuple[ToolSpec, ...] = (
    _spec(ToolId.NUCLEI, _SUB, 90, rate_limited=True, disable_update_check=True, base_argv=("nuclei", "-u")),
    _spec(ToolId.TESTSSL, _SUB, 60, base_argv=("testssl.sh", "--quiet", "--warnings", "batch")),
    _spec(ToolId.SECURITY_HEADERS, _SUB, 30, base_argv=("security-headers",)),
    _spec(ToolId.WHATWEB, _SUB, 30, base_argv=("whatweb",)),
    _spec(ToolId.NIKTO, _SUB, 90, base_argv=("nikto", "-h")),
    _spec(ToolId.KATANA, _SUB, 60, request_delay=True, base_argv=("katana", "-u")),
    _spec(ToolId.FFUF, _SUB, 90, request_delay=True, base_argv=("ffuf", "-u")),
    _spec(ToolId.SQLMAP, _SUB, 120, base_argv=("sqlmap", "-u", "--batch")),
    _spec(ToolId.SUBFINDER, _SUB, 60, base_argv=("subfinder", "-d")),
    _spec(ToolId.DNSX, _SUB, 60, base_argv=("dnsx",)),
    _spec(
        ToolId.ZAP_BASELINE,
        _DOOD,
        120,
        memory="2g",
        image=ZAP_IMAGE,
        mount="/zap/wrk",
        # -J writes the JSON report into the mounted wrk dir (= the host shared
        # dir the worker reads back); ZAP prints only a summary to stdout.
        base_argv=("zap-baseline.py", "-J", "report.json", "-t"),
    ),
    _spec(
        ToolId.ZAP_FULL_ACTIVE,
        _DOOD,
        240,
        memory="2g",
        image=ZAP_IMAGE,
        mount="/zap/wrk",
        # -J writes the JSON report into the mounted wrk dir (read back by the worker).
        base_argv=("zap-full-scan.py", "-J", "report.json", "-t"),
    ),
    # hexstrike: feature-flagged / time-boxed (spec §10). Timeout bounded to the
    # global budget headroom; only ever appended by resolve_tools when enabled+OK.
    _spec(
        ToolId.HEXSTRIKE,
        _DOOD,
        300,
        image=HEXSTRIKE_IMAGE,
        mount="/data",
        base_argv=("hexstrike",),
    ),
)

#: Immutable registry keyed by :class:`ToolId`.
TOOL_SPECS: "MappingProxyType[ToolId, ToolSpec]" = MappingProxyType({s.tool: s for s in _SPECS})


def spec_for(tool: ToolId) -> ToolSpec:
    """Return the :class:`ToolSpec` for ``tool`` or raise ``KeyError``.

    Every tool in the 02 whitelist MUST have a spec here; a missing one is an
    engine bug, not a user error.
    """
    return TOOL_SPECS[tool]
