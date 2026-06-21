"""``RunScanCommand`` registration + serialization (05-agent-team plan §9).

The command must be in ``async_tasks_mapping`` (so the SAQ ``handle_command``
resolver can rehydrate it) and round-trip through ``to_dict``/``from_dict`` with a
100%-serializable payload (no domain objects on the wire).
"""

from __future__ import annotations

from uuid import uuid4

from expects import be_a, equal, expect

from src.common.application.data.tasks_mapping import async_tasks_mapping
from src.scans.application.commands.run_scan import RunScanCommand


def test_run_scan_command_is_registered_in_async_tasks_mapping():
    expect("RunScanCommand" in async_tasks_mapping).to(equal(True))
    expect(async_tasks_mapping["RunScanCommand"]).to(equal(RunScanCommand))


def test_to_dict_payload_is_json_serializable():
    import json

    scan_id = uuid4()
    command = RunScanCommand(scan_id=scan_id)
    payload = command.to_dict

    # scan_id serialized to a string (no UUID object on the wire).
    expect(payload["scan_id"]).to(be_a(str))
    expect(payload["scan_id"]).to(equal(str(scan_id)))
    # The whole payload survives a JSON round-trip.
    expect(json.loads(json.dumps(payload))).to(equal(payload))


def test_from_dict_round_trips_the_uuid():
    scan_id = uuid4()
    rebuilt = RunScanCommand.from_dict(RunScanCommand(scan_id=scan_id).to_dict)
    expect(rebuilt.scan_id).to(equal(scan_id))


def test_handler_is_subscribed_in_bus_wiring():
    # The handler must be importable + constructible (the SAQ worker builds it).
    from src.scans.application.commands.run_scan_handler import RunScanHandler

    handler = RunScanHandler()  # all deps optional ⇒ constructs unwired
    expect(handler).to(be_a(RunScanHandler))
    # scans_wiring references the handler (imported lazily to avoid DB at import).
    import src.scans.infrastructure.bus_wiring as wiring

    expect(hasattr(wiring, "scans_wiring")).to(equal(True))
