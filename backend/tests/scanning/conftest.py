"""Shared fixtures/fakes for the scanning-engine tests.

All external tools (subprocess / docker run) are MOCKED — these tests prove the
ENGINE logic, never run a real scanner.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

import pytest


@dataclass
class FakeRedis:
    """Minimal async Redis stand-in for CancelToken (GET only)."""

    store: dict[str, str]

    async def get(self, key: str) -> str | None:
        return self.store.get(key)


class NeverCancel:
    """CancelToken-shaped stub whose flag is never set."""

    async def is_set(self) -> bool:
        return False


class AlwaysCancel:
    """CancelToken-shaped stub whose flag is always set."""

    async def is_set(self) -> bool:
        return True


def make_completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["x"], returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def never_cancel() -> NeverCancel:
    return NeverCancel()


@pytest.fixture
def always_cancel() -> AlwaysCancel:
    return AlwaysCancel()
