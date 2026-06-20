"""Slug helpers for DocumentType.

Slugs are unique per workflow and auto-derived from the doctype name. When
multiple doctypes share the same name in a workflow, subsequent ones are
disambiguated with a numeric suffix (`cedula`, `cedula_1`, `cedula_2`, …).
"""

from slugify import slugify

DEFAULT_SLUG = "doctype"


def slugify_doctype_name(name: str) -> str:
    base = slugify(name, separator="_")
    return base or DEFAULT_SLUG


def compute_unique_slug(base: str, existing_slugs: set[str]) -> str:
    if base not in existing_slugs:
        return base
    counter = 1
    while f"{base}_{counter}" in existing_slugs:
        counter += 1
    return f"{base}_{counter}"
