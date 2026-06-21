"""run_tool dispatch + timeout + partial-failure + DooD flags + rate-limit/UA.

Every external call (subprocess / docker run) is mocked via patching the blocking
``_run_subprocess_blocking`` helper, so no real tool ever runs (plan §10).
"""

from __future__ import annotations

import subprocess

from expects import be_false, be_none, be_true, contain, equal, expect

from src.scanning import runner as runner_mod
from src.scanning.registry import spec_for
from src.scanning.runner import run_tool
from src.scans.domain.enums.tool_id import ToolId
from tests.scanning.conftest import AlwaysCancel, NeverCancel, make_completed


async def test_subprocess_dispatch_returns_raw_stdout(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(cmd, timeout_s):
        captured["cmd"] = cmd
        captured["timeout"] = timeout_s
        return make_completed(stdout='{"ok": true}', returncode=0)

    monkeypatch.setattr(runner_mod, "_run_subprocess_blocking", fake_run)

    result = await run_tool(
        spec_for(ToolId.WHATWEB),
        target="https://x.gob.mx",
        host_shared_dir="/data/scans/abc",
        cancel=NeverCancel(),
    )

    expect(result.ok).to(be_true)
    expect(result.stdout).to(equal('{"ok": true}'))  # raw stdout, never parsed
    expect(result.timed_out).to(be_false)
    expect(result.coverage_note).to(be_none)
    expect(captured["timeout"]).to(equal(30))  # whatweb hard timeout (spec §4.2)


async def test_timeout_sets_timed_out_and_coverage_note(monkeypatch) -> None:
    def fake_run(cmd, timeout_s):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout_s, output="partial")

    monkeypatch.setattr(runner_mod, "_run_subprocess_blocking", fake_run)

    result = await run_tool(
        spec_for(ToolId.NIKTO),
        target="https://x.gob.mx",
        host_shared_dir="/data/scans/abc",
        cancel=NeverCancel(),
    )

    # NEVER propagates: a hung tool degrades to a coverage note (§4.3).
    expect(result.ok).to(be_false)
    expect(result.timed_out).to(be_true)
    expect(result.coverage_note).not_to(be_none)
    expect(result.stdout).to(equal("partial"))  # partial stdout preserved


async def test_partial_failure_non_zero_exit_does_not_raise(monkeypatch) -> None:
    def fake_run(cmd, timeout_s):
        return make_completed(stdout="", stderr="boom", returncode=2)

    monkeypatch.setattr(runner_mod, "_run_subprocess_blocking", fake_run)

    result = await run_tool(
        spec_for(ToolId.TESTSSL),
        target="https://x.gob.mx",
        host_shared_dir="/data/scans/abc",
        cancel=NeverCancel(),
    )

    expect(result.ok).to(be_false)
    expect(result.timed_out).to(be_false)
    expect(result.coverage_note).not_to(be_none)


async def test_arbitrary_exception_does_not_propagate(monkeypatch) -> None:
    def fake_run(cmd, timeout_s):
        raise OSError("no such binary")

    monkeypatch.setattr(runner_mod, "_run_subprocess_blocking", fake_run)

    result = await run_tool(
        spec_for(ToolId.KATANA),
        target="https://x.gob.mx",
        host_shared_dir="/data/scans/abc",
        cancel=NeverCancel(),
    )

    expect(result.ok).to(be_false)
    expect(result.coverage_note).to(contain("OSError"))


async def test_cancel_before_start_skips_tool(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_run(cmd, timeout_s):
        calls["n"] += 1
        return make_completed()

    monkeypatch.setattr(runner_mod, "_run_subprocess_blocking", fake_run)

    result = await run_tool(
        spec_for(ToolId.NUCLEI),
        target="https://x.gob.mx",
        host_shared_dir="/data/scans/abc",
        cancel=AlwaysCancel(),
    )

    expect(calls["n"]).to(equal(0))  # tool never launched
    expect(result.ok).to(be_false)
    expect(result.coverage_note).to(contain("cancelado"))


async def test_dood_command_has_isolation_flags(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(cmd, timeout_s):
        captured["cmd"] = cmd
        captured["timeout"] = timeout_s
        return make_completed(stdout="zap done")

    monkeypatch.setattr(runner_mod, "_run_subprocess_blocking", fake_run)

    await run_tool(
        spec_for(ToolId.ZAP_BASELINE),
        target="https://x.gob.mx",
        host_shared_dir="/data/scans/abc",
        cancel=NeverCancel(),
    )

    cmd = captured["cmd"]
    joined = " ".join(cmd)
    # egress network, memory cap, pinned tag (NOT :latest), HOST -v path (§3.1/§5).
    expect(cmd).to(contain("--network"))
    expect(cmd).to(contain("owliver_egress"))
    expect(cmd).to(contain("--memory"))
    expect(cmd).to(contain("2g"))
    expect(joined).not_to(contain(":latest"))
    expect(joined).to(contain("zaproxy/zap-stable:2.15.0"))
    expect(cmd).to(contain("/data/scans/abc:/zap/wrk"))  # HOST path, not worker path
    # docker run gets the logical timeout + overhead
    expect(captured["timeout"]).to(equal(spec_for(ToolId.ZAP_BASELINE).docker_timeout_s))


async def test_nuclei_run_carries_duc_rate_limit_and_ua(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(cmd, timeout_s):
        captured["cmd"] = cmd
        return make_completed(stdout="[]")

    monkeypatch.setattr(runner_mod, "_run_subprocess_blocking", fake_run)

    await run_tool(
        spec_for(ToolId.NUCLEI),
        target="https://x.gob.mx",
        host_shared_dir="/data/scans/abc",
        cancel=NeverCancel(),
        flags=("-tags", "ssl,tech"),
    )

    cmd = captured["cmd"]
    joined = " ".join(cmd)
    expect(cmd).to(contain("-duc"))  # disable update check (spec §7)
    expect(cmd).to(contain("-rl"))  # rate limit (WORKER_NUCLEI_RATE)
    expect(cmd).to(contain("150"))
    expect(joined).to(contain("Owliver-Scanner/1.0"))  # identifiable UA


async def test_delay_tools_carry_request_delay(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(cmd, timeout_s):
        captured["cmd"] = cmd
        return make_completed()

    monkeypatch.setattr(runner_mod, "_run_subprocess_blocking", fake_run)

    await run_tool(
        spec_for(ToolId.FFUF),
        target="https://x.gob.mx",
        host_shared_dir="/data/scans/abc",
        cancel=NeverCancel(),
    )

    expect(captured["cmd"]).to(contain("-delay"))
