"""``run_tool`` — the single point of container/subprocess invocation (spec §3).

Every tool the engine runs goes through this one helper. Light CLIs run by
``subprocess`` inside the fat ``scanners`` image; heavy containers (ZAP, hexstrike)
run as siblings via ``docker run`` over the host socket (DooD, NEVER DinD). Both
paths share the same cancellation gate, hard timeout, rate-limit/UA injection and
output capture, so an isolation flag (``--network``, ``--memory``, pinned tag,
host ``-v``) can never be forgotten on a stray call.

``run_tool`` returns a :class:`ToolResult` with the RAW ``stdout`` — the engine
NEVER parses it. 05-agent-team's deterministic parsers consume ``stdout`` to
produce ``Finding[]``. ``run_tool`` NEVER propagates: a timeout/non-zero/exception
becomes ``ok=False`` + a ``coverage_note`` (the partial-failure policy, §4.3).
"""

from __future__ import annotations

import asyncio
import subprocess  # noqa: S404 - intentional: the engine shells out to scanners
import time
from dataclasses import dataclass

from src.common.application.logging import get_logger
from src.common.domain.legal.constants import (
    SCANNER_USER_AGENT,
    WORKER_NUCLEI_RATE,
    WORKER_REQUEST_DELAY_MS,
)
from src.common.settings import settings
from src.scanning.registry import ToolMechanism, ToolSpec
from src.scanning.watchdog import CancelToken

logger = get_logger()

#: Wordlist ffuf dir-enum runs against (``-w``). ffuf has no useful default, so we
#: point at dirb's ``common.txt`` (installed via the ``dirb`` apt package in
#: Dockerfile.scanners) — a small, fast list appropriate for the bounded scan.
FFUF_WORDLIST = "/usr/share/dirb/wordlists/common.txt"


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Outcome of a single tool invocation — the raw-stdout contract for 05.

    ``stdout`` is the RAW tool output (JSON/JSONL/text); 05's parsers turn it into
    ``Finding[]`` — this module never parses it. ``ok`` is ``False`` on timeout,
    non-zero exit or any exception. ``coverage_note`` is non-null exactly when the
    tool did not complete cleanly ("tool X no completó"); 05 maps it to a
    low-confidence Finding-meta and into ``scans.coverage`` and CONTINUES.
    """

    tool: str
    ok: bool
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool
    coverage_note: str | None = None


#: Whitelist tokens that are LOGICAL/declarative (02 authors flags as intent, not
#: literal argv) and are NOT valid CLI flags for the pinned tool versions — passing
#: them verbatim makes the tool exit 2 ("flag provided but not defined"), which
#: flips the scan to partial. Each is already the tool's DEFAULT behavior, so
#: dropping them is semantically a no-op:
#:   --root            root-only (whatweb/testssl/security-headers don't crawl)
#:   -no-spider        nuclei does not crawl unless -crawl is given
#:   -passive          subfinder/dnsx are passive by default
#:   -fuzzing-templates / --single-param  removed flags in nuclei v3 / sqlmap
_DECLARATIVE_FLAGS: frozenset[str] = frozenset(
    {"--root", "-no-spider", "-passive", "-fuzzing-templates", "--single-param"}
)


def _inject_operational_flags(spec: ToolSpec, flags: tuple[str, ...]) -> list[str]:
    """Append the engine-owned operational flags to the whitelist ``flags``.

    The whitelist (02) provides logical flags; here we layer the operational ones
    the spec marks: nuclei ``-duc`` (disable update check, spec §7), ``-rl
    WORKER_NUCLEI_RATE`` (rate-limited tools), and ``-delay``/``-rate`` for the
    per-request-delay tools (ffuf/katana). UA is injected via ``-H`` where the tool
    supports a header flag and always set in the subprocess env as a fallback.

    Declarative-only tokens (``_DECLARATIVE_FLAGS``) are dropped here: they encode
    02 policy intent but are not valid argv for the pinned binaries (they would
    exit 2 and force partial coverage); the behavior they request is the default.
    """
    argv: list[str] = [f for f in flags if f not in _DECLARATIVE_FLAGS]
    if spec.disable_update_check:
        argv.append("-duc")
    if spec.rate_limited:
        argv += ["-rl", str(WORKER_NUCLEI_RATE)]
        argv += ["-H", f"User-Agent: {SCANNER_USER_AGENT}"]
    if spec.request_delay:
        # Per-tool politeness mapping (the flag names differ and the registry stays
        # declarative): ffuf takes ``-p <seconds>`` (float ok); katana's ``-delay``
        # is integer-seconds only (it rejects 0.2), so express the same budget as a
        # ``-rate-limit`` (requests/second). ffuf also REQUIRES a wordlist (``-w``).
        delay_s = WORKER_REQUEST_DELAY_MS / 1000.0
        tool = str(spec.tool)
        if tool == "ffuf":
            argv += ["-p", f"{delay_s:g}", "-w", FFUF_WORDLIST]
        elif tool == "katana":
            argv += ["-rate-limit", str(max(1, round(1.0 / delay_s)))]
    return argv


def _build_subprocess_cmd(spec: ToolSpec, target: str, flags: tuple[str, ...]) -> list[str]:
    """argv for a light CLI run inside the ``scanners`` image (spec §3)."""
    return [*spec.base_argv, target, *_inject_operational_flags(spec, flags)]


def _to_host_path(internal_path: str) -> str:
    """Translate a worker-internal scan path to its real HOST path for a DooD ``-v``.

    The worker's scan dir is a host bind-mount; the sibling container is launched by
    the host daemon (over the socket), which only understands host paths. When the
    host path differs from the in-container path (``SCAN_DATA_HOST_DIR`` vs
    ``SCAN_DATA_DIR``) we rewrite the prefix so the sibling (ZAP) mounts the SAME
    directory the worker created and ``chmod 0o777``'d. No-op when they're equal
    (e.g. tests / a setup where the scan dir is already a matching host path).
    """
    data_dir = settings.SCAN_DATA_DIR
    host_dir = settings.SCAN_DATA_HOST_DIR
    if host_dir and host_dir != data_dir and internal_path.startswith(data_dir):
        return host_dir + internal_path[len(data_dir):]
    return internal_path


def _build_dood_cmd(
    spec: ToolSpec,
    target: str,
    host_shared_dir: str,
    flags: tuple[str, ...],
) -> list[str]:
    """argv for a sibling ``docker run`` (DooD, spec §3.2).

    Centralizes EVERY isolation control: ``--network owliver_egress`` (§5),
    ``--memory``/``--cpus`` (§4), the pinned image tag (§7) and the ``-v`` bind of
    the HOST shared dir (§3.1 — the daemon over the socket only knows host paths).
    """
    cmd: list[str] = ["docker", "run", "--rm", "--network", "owliver_egress"]
    if spec.memory:
        cmd += ["--memory", spec.memory]
    if spec.cpus:
        cmd += ["--cpus", spec.cpus]
    if spec.mount:
        # -v points at the HOST path, never the worker's internal path (DooD rule):
        # the sibling is started by the host daemon, which can only see host paths.
        cmd += ["-v", f"{_to_host_path(host_shared_dir)}:{spec.mount}"]
    cmd.append(spec.image or "")  # image presence guaranteed by the registry
    # After the image comes the in-container command: the full base_argv (e.g.
    # "zap-baseline.py", "-t") + the target + the resolved flags.
    cmd += [*spec.base_argv, target]
    cmd += _inject_operational_flags(spec, flags)
    return cmd


def _scanner_env() -> dict[str, str]:
    """Env for the subprocess, pinning the identifiable scanner User-Agent."""
    import os

    env = dict(os.environ)
    env["USER_AGENT"] = SCANNER_USER_AGENT
    env["HTTP_USER_AGENT"] = SCANNER_USER_AGENT
    return env


def _run_subprocess_blocking(cmd: list[str], timeout_s: int) -> subprocess.CompletedProcess[str]:
    """Blocking ``subprocess.run`` (executed via ``asyncio.to_thread``)."""
    return subprocess.run(  # noqa: S603 - argv list, no shell; engine invokes scanners
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
        env=_scanner_env(),
    )


async def run_tool(
    spec: ToolSpec,
    *,
    target: str,
    host_shared_dir: str,
    cancel: CancelToken,
    flags: tuple[str, ...] = (),
) -> ToolResult:
    """Run one tool under its hard timeout, returning raw stdout (spec §3/§4).

    Dispatches by ``spec.mechanism``: ``SUBPROCESS`` -> light CLI in the image;
    ``DOOD`` -> sibling ``docker run`` via the host socket. Cancellation is checked
    BEFORE launching. The whole body is guarded: a timeout sets ``timed_out=True``;
    any other failure sets ``ok=False`` with a ``coverage_note``. NEVER propagates
    (partial-failure policy, §4.3) — the caller's other tools keep running.

    ``flags`` are the resolved whitelist flags for this invocation (from
    ``resolve_tools``); operational flags (-duc/-rl/delay/UA) are layered on here.
    """
    tool_name = str(spec.tool)

    # Cancellation gate — do not even start a tool for a cancelled scan (§4.3).
    if await cancel.is_set():
        logger.info("run_tool.cancelled_before_start", extra={"tool": tool_name})
        return ToolResult(
            tool=tool_name,
            ok=False,
            stdout="",
            stderr="",
            duration_s=0.0,
            timed_out=False,
            coverage_note=f"tool {tool_name} no se ejecutó: scan cancelado",
        )

    if spec.is_dood:
        cmd = _build_dood_cmd(spec, target, host_shared_dir, flags)
        timeout_s = spec.docker_timeout_s
    else:
        cmd = _build_subprocess_cmd(spec, target, flags)
        timeout_s = spec.timeout_s

    started = time.monotonic()
    try:
        completed = await asyncio.to_thread(_run_subprocess_blocking, cmd, timeout_s)
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        logger.warning("run_tool.timeout", extra={"tool": tool_name, "timeout_s": timeout_s})
        partial = exc.stdout or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", "replace")
        return ToolResult(
            tool=tool_name,
            ok=False,
            stdout=partial,
            stderr="",
            duration_s=duration,
            timed_out=True,
            coverage_note=f"tool {tool_name} no completó: timeout tras {timeout_s}s",
        )
    except Exception as exc:  # noqa: BLE001 - partial-failure: NEVER propagate (§4.3)
        duration = time.monotonic() - started
        logger.warning("run_tool.error", extra={"tool": tool_name, "error": str(exc)})
        return ToolResult(
            tool=tool_name,
            ok=False,
            stdout="",
            stderr=str(exc),
            duration_s=duration,
            timed_out=False,
            coverage_note=f"tool {tool_name} no completó: {type(exc).__name__}",
        )

    duration = time.monotonic() - started
    ok = completed.returncode == 0
    if not ok:
        # A non-zero exit is the most common partial-coverage cause (missing nuclei
        # templates, a missing system dep like hexdump for testssl, the target
        # refusing the probe…). The partial-failure policy (§4.3) NEVER raises and
        # the ToolResult.stderr is otherwise swallowed, so log the return code + a
        # stderr snippet here — this is the single place the real reason is visible.
        # Some CLIs (nuclei, subfinder) print usage / argument errors to STDOUT,
        # not stderr — fall back to a stdout tail so an exit-2 isn't an opaque
        # "código 2" with no reason.
        detail = (completed.stderr or "").strip() or (completed.stdout or "").strip()[-500:]
        logger.warning(
            "run_tool.nonzero_exit",
            extra={
                "tool": tool_name,
                "returncode": completed.returncode,
                "duration_s": round(duration, 2),
                "detail": detail[:500],
            },
        )
    else:
        logger.debug(
            "run_tool.ok",
            extra={"tool": tool_name, "duration_s": round(duration, 2)},
        )
    return ToolResult(
        tool=tool_name,
        ok=ok,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        duration_s=duration,
        timed_out=False,
        coverage_note=None if ok else f"tool {tool_name} terminó con código {completed.returncode}",
    )
