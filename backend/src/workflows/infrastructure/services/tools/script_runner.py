"""Runner de script tools (PYTHON/JS) — phases-config · F5 · D-D.

``enrich`` corre tools firmadas vía el connector determinista. F5 añade transportes
``PYTHON``/``JS``: el código vive en ``tool_definitions.config``
(``{runtime, entrypoint, code|code_ref, limits}``) y se ejecuta en un **runner
sandbox aislado in-cluster** (gVisor/Firecracker, D-D), NO como Lambda-por-lenguaje.

Contrato de seguridad (ADR 0006 · requiere revisión de seguridad dedicada):
- aislamiento fuerte (gVisor/Firecracker), un sandbox efímero por invocación;
- **sin red** salvo allowlist explícita de la ConnectionAccount;
- límites de CPU/tiempo/memoria;
- **sin acceso a secretos** fuera de los inyectados explícitamente;
- mismo render de args (``@slug.path`` / ``{{token}}``) y mismo ``on_failure`` que HTTP.

Este módulo define la **interfaz** + un default **fail-closed**
(:class:`UnconfiguredScriptRunner`): mientras ops no provisione el sandbox real y
pase la revisión de seguridad, ejecutar código no confiable está **bloqueado** —
el connector degrada la tool (nunca ejecuta sin sandbox).
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from typing import Any, Protocol, runtime_checkable

from src.common.application.logging import get_logger
from src.common.domain.enums.tools import ToolTransport

logger = get_logger(__name__)


class ScriptExecutionError(Exception):
    """Fallo de ejecución/aislamiento del script (lo captura el connector → degraded)."""


class ScriptSandboxNotConfiguredError(ScriptExecutionError):
    """No hay sandbox provisionado: fail-closed (jamás se ejecuta sin aislamiento)."""


@runtime_checkable
class ScriptRunner(Protocol):
    """Ejecuta el código de una script tool dentro del sandbox y devuelve su salida JSON."""

    async def run(
        self,
        *,
        transport: ToolTransport,
        runtime: str | None,
        entrypoint: str | None,
        code: str | None,
        code_ref: str | None,
        args: dict[str, Any],
        limits: dict[str, Any],
    ) -> dict[str, Any]: ...


class UnconfiguredScriptRunner:
    """Default seguro: rechaza toda ejecución (fail-closed). Se reemplaza por el
    runner real (gVisor/Firecracker) cuando ops lo provisione + pase seguridad."""

    async def run(self, **_: Any) -> dict[str, Any]:
        raise ScriptSandboxNotConfiguredError(
            "script sandbox not configured (ToolTransport.PYTHON/JS requires the "
            "in-cluster sandbox runner — see ADR 0006)"
        )


# Defaults de límites (override por tool via config.limits).
_DEFAULT_TIMEOUT_S = 10
_DEFAULT_CPU_S = 5
_DEFAULT_MEM_BYTES = 256 * 1024 * 1024  # 256 MiB
_MAX_OUTPUT_BYTES = 1024 * 1024  # 1 MiB de stdout

_PY_WRAPPER = (
    "{code}\n"
    "import sys as _sys, json as _json\n"
    "_args = _json.loads(_sys.stdin.read() or '{{}}')\n"
    "_sys.stdout.write(_json.dumps({entrypoint}(_args)))\n"
)
_JS_WRAPPER = (
    "{code}\n"
    "const _fs = require('fs');\n"
    "const _args = JSON.parse(_fs.readFileSync(0, 'utf8') || '{{}}');\n"
    "Promise.resolve({entrypoint}(_args)).then(r => process.stdout.write(JSON.stringify(r)));\n"
)


class LocalSubprocessScriptRunner:
    """Runner local con rlimits/timeout/env-scrubbed/tempdir/output-cap.

    ⚠️ **SOLO dev** (default-off, ``TOOLS_SCRIPT_RUNNER=local_subprocess``): NO
    aísla red ni kernel — comparte el host. El runner de PRODUCCIÓN debe ser el
    sandbox in-cluster (gVisor/Firecracker, ADR 0006 · D-D) tras revisión de
    seguridad. Sirve para probar el contrato de script tools en local/CI.
    """

    def __init__(self) -> None:
        logger.warning(
            "script_runner.local_subprocess_enabled",
            note="DEV ONLY — no network/kernel isolation; use the in-cluster sandbox in prod (ADR 0006)",
        )

    async def run(
        self,
        *,
        transport: ToolTransport,
        runtime: str | None,
        entrypoint: str | None,
        code: str | None,
        code_ref: str | None,
        args: dict[str, Any],
        limits: dict[str, Any],
    ) -> dict[str, Any]:
        if not code:
            raise ScriptExecutionError("script tool has no inline code (code_ref fetch not supported here)")
        entry = entrypoint or "main"
        if transport is ToolTransport.PYTHON:
            interpreter, flag, wrapper = self._python_cmd(runtime), "-c", _PY_WRAPPER
        elif transport is ToolTransport.JS:
            interpreter, flag, wrapper = (runtime or "node"), "-e", _JS_WRAPPER
        else:
            raise ScriptExecutionError(f"unsupported script transport {transport}")
        program = wrapper.format(code=code, entrypoint=entry)
        return await self._exec(interpreter, flag, program, args, limits)

    @staticmethod
    def _python_cmd(runtime: str | None) -> str:
        # runtime "python3.12" → binario "python3"; cualquier otro string se usa tal cual.
        if not runtime or runtime.startswith("python"):
            return "python3"
        return runtime

    async def _exec(
        self, interpreter: str, flag: str, program: str, args: dict[str, Any], limits: dict[str, Any]
    ) -> dict[str, Any]:
        timeout_s = float(limits.get("timeout_seconds") or _DEFAULT_TIMEOUT_S)
        workdir = tempfile.mkdtemp(prefix="scripttool-")
        try:
            proc = await asyncio.create_subprocess_exec(
                interpreter,
                flag,
                program,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},  # scrubbed: sin secretos
                preexec_fn=_apply_rlimits(limits),  # noqa: PLW1509 — rlimits en el hijo (Unix)
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=json.dumps(args).encode()), timeout=timeout_s
                )
            except (TimeoutError, asyncio.TimeoutError) as exc:
                proc.kill()
                raise ScriptExecutionError(f"script timed out after {timeout_s}s") from exc
            if proc.returncode != 0:
                raise ScriptExecutionError(
                    f"script exited {proc.returncode}: {stderr.decode('utf-8', 'replace')[:500]}"
                )
            if len(stdout) > _MAX_OUTPUT_BYTES:
                raise ScriptExecutionError("script output exceeds the 1 MiB cap")
            try:
                result = json.loads(stdout.decode("utf-8") or "{}")
            except json.JSONDecodeError as exc:
                raise ScriptExecutionError(f"script output is not JSON: {exc}") from exc
            if not isinstance(result, dict):
                raise ScriptExecutionError("script output root must be a JSON object")
            return result
        finally:
            shutil.rmtree(workdir, ignore_errors=True)


def _apply_rlimits(limits: dict[str, Any]):
    """preexec_fn que aplica rlimits de CPU/memoria/fs en el proceso hijo (Unix).
    En plataformas sin ``resource`` devuelve None (sin límites — dev-only)."""
    try:
        import resource  # noqa: PLC0415 — solo Unix
    except ImportError:
        return None

    cpu_s = int(limits.get("cpu_seconds") or _DEFAULT_CPU_S)
    mem_bytes = int(limits.get("memory_bytes") or _DEFAULT_MEM_BYTES)

    def _set() -> None:
        # Best-effort: un límite rechazado por la plataforma (p. ej. RLIMIT_AS en
        # macOS rompe el arranque de Python) no debe impedir la ejecución — el
        # aislamiento fuerte es el sandbox in-cluster, no este runner dev.
        for res, soft_hard in (
            (resource.RLIMIT_CPU, (cpu_s, cpu_s)),
            (resource.RLIMIT_AS, (mem_bytes, mem_bytes)),
            (resource.RLIMIT_FSIZE, (_MAX_OUTPUT_BYTES, _MAX_OUTPUT_BYTES)),
        ):
            try:
                resource.setrlimit(res, soft_hard)
            except (ValueError, OSError):
                pass

    return _set


def build_script_runner() -> ScriptRunner | None:
    """Factory del runner según ``settings.TOOLS_SCRIPT_RUNNER``. ``None`` (o un
    valor desconocido) ⇒ el connector queda fail-closed (script tools degradan)."""
    from src.common.settings import settings  # noqa: PLC0415

    selector = (getattr(settings, "TOOLS_SCRIPT_RUNNER", "") or "").strip().lower()
    if selector == "local_subprocess":
        return LocalSubprocessScriptRunner()
    return None
