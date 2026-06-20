"""Helpers for safely parsing JSON that may be wrapped in markdown fences."""

import json
import logging

logger = logging.getLogger(__name__)


def strip_fences(text: str) -> str:
    """Remove leading/trailing markdown code fences (```...```) from *text*."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0].strip()
    return text


def safe_json_loads(text: str, fallback_key: str = "raw_text") -> dict:
    """Parse *text* as JSON after stripping markdown fences.

    If parsing fails, returns ``{fallback_key: text}`` so callers always
    receive a dict rather than raising an exception.
    """
    clean = strip_fences(text)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        logger.warning("Could not parse JSON response; storing raw text under key '%s'", fallback_key)
        return {fallback_key: text}
