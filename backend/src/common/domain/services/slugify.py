"""Kebab-case slug helper used across the project.

Produces lowercase ASCII slugs matching `^[a-z0-9][a-z0-9_-]{0,99}$`. Underscores
that already exist in the source string are preserved (so callers that mix `_`
and `-` get stable round-trips); everything else collapses to `-`.
"""

from slugify import slugify as _slugify

DEFAULT_SLUG = "kb"
MAX_SLUG_LENGTH = 100


def slugify(text: str, *, max_length: int = MAX_SLUG_LENGTH, default: str = DEFAULT_SLUG) -> str:
    base = _slugify(text, max_length=max_length, separator="-", lowercase=True)
    return base or default
