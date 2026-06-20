"""Structural contracts for provider adapters (F12).

A provider adapter bridges a configured :class:`WorkflowSource` /
:class:`WebhookDestination` to its external system. Sources are *polled* for new
documents; destinations *deliver* a result payload. Both are declared as typing
``Protocol`` classes so concrete adapters need only match the method shape — no
inheritance is required.

The ``WEBHOOK`` provider has no adapter here: inbound webhooks arrive via the
``POST /v1/ingest/{token}`` endpoint and outbound webhooks are dispatched by the
existing HTTP destination dispatcher. Adapters cover the OAuth/credential-based
providers (Drive, Email, WhatsApp, Slack), whose flows are external and pending.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.common.domain.models.webhook_destination import WebhookDestination
from src.connections.domain.models.workflow_source import WorkflowSource


@runtime_checkable
class SourceAdapter(Protocol):
    """An inbound provider that yields new documents for ingestion.

    A source adapter knows how to reach an external origin (a Drive folder, an
    inbox, a WhatsApp number) using the credentials referenced by the
    :class:`WorkflowSource` and surface freshly available items.
    """

    async def poll(self, source: WorkflowSource) -> list[dict]:
        """Return newly available items for ``source`` as raw dicts.

        Each dict describes one ingestible document (e.g. a file handle plus
        metadata) in the provider's native shape; the caller is responsible for
        mapping it onto the ingest pipeline. Returns an empty list when nothing
        new is available.
        """
        ...


@runtime_checkable
class DestinationAdapter(Protocol):
    """An outbound provider that delivers a result payload.

    A destination adapter knows how to push ``payload`` to an external system (a
    Slack channel, a Drive folder, an outbound mail) using the credentials
    referenced by the :class:`WebhookDestination`.
    """

    async def deliver(self, destination: WebhookDestination, payload: dict) -> dict:
        """Deliver ``payload`` to ``destination`` and return a result dict.

        The returned dict captures the provider's delivery acknowledgement
        (e.g. a message id, status) for persistence/observability.
        """
        ...
