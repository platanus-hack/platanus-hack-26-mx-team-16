"""Enums for the inbound channel dedup ledger ``source_deliveries`` (E6 · §5.9)."""

from src.common.domain.enums.base_enum import BaseEnum


class SourceDeliveryStatus(BaseEnum):
    """Lifecycle of a single inbound channel message.

    ``RECEIVED`` is the delivery-first row written before any side effect.
    ``PROCESSED`` once a case has been resolved/dispatched; ``FAILED`` (with
    ``error``) when a step blew up (e.g. expired WhatsApp media URL) and the
    delivery may be retried.
    """

    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"
