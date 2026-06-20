"""Parse the structured references that compile pipelines extract from prompts.

Three notations live in rule prompts and templates:

- ``@slug`` / ``@slug.path`` / ``@slug.items[].subtotal`` — document refs
  (the canonical shorthand). The braced form ``@{slug}.path`` is accepted
  as an equivalent alias.
- ``#kb_slug`` (or ``#{kb_slug}``) — knowledge-base document references.
- ``{{token.name}}`` — runtime tokens validated against the token registry.

The parsers are pure regex-based functions: they don't validate slugs against
any catalogue; that is the caller's responsibility (compile validates against
the workflow document types, the KB resolver and the token registry).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

DocRefKind = Literal["scalar", "array", "collection"]

# Accepts both `@{slug}` and `@slug`. The negative lookbehind `(?<![\w@.])`
# forbids a left word/`@`/`.` boundary so an email (`soporte@empresa.com`) or a
# chained `@handle` in a prompt is NOT mistaken for a document ref — that would
# make any rule whose prompt mentions an address fail to compile.
_DOC_REF_RE = re.compile(
    r"(?<![\w@.])@(?:\{(?P<slug_braced>[a-z0-9][a-z0-9_-]*)\}|(?P<slug_bare>[a-z0-9][a-z0-9_-]*))"
    r"(?P<path>(?:\.[A-Za-z_][\w]*|\[\d*\])*)",
)
# Same guard for `#kb_slug`: `issue#123`, hex colors (`#fff`) and the like must
# not be parsed as KB references.
_KB_REF_RE = re.compile(
    r"(?<![\w#.])#(?:\{(?P<slug_braced>[a-z0-9][a-z0-9_-]*)\}|(?P<slug_bare>[a-z0-9][a-z0-9_-]*))",
)
_TOKEN_RE = re.compile(r"\{\{\s*(?P<name>[A-Za-z_][\w.]*)\s*\}\}")


@dataclass(frozen=True)
class DocRef:
    slug: str
    path: str | None
    kind: DocRefKind
    raw: str


def parse_doc_refs(prompt: str) -> list[DocRef]:
    """Return all document references in the order they appear, deduped by `raw`."""
    seen: dict[str, DocRef] = {}
    for match in _DOC_REF_RE.finditer(prompt):
        slug = match.group("slug_braced") or match.group("slug_bare")
        path = match.group("path") or ""
        raw = match.group(0)
        kind = _classify_doc_ref(path)
        normalized_path = path.lstrip(".") if path else None
        ref = DocRef(slug=slug, path=normalized_path or None, kind=kind, raw=raw)
        seen.setdefault(raw, ref)
    return list(seen.values())


def parse_kb_refs(prompt: str) -> list[str]:
    """Return KB document slugs referenced via `#slug` or `#{slug}`, deduped, in order."""
    seen: dict[str, None] = {}
    for match in _KB_REF_RE.finditer(prompt):
        slug = match.group("slug_braced") or match.group("slug_bare")
        seen.setdefault(slug, None)
    return list(seen.keys())


def parse_tokens(prompt: str) -> list[str]:
    """Return token names referenced via `{{name}}` (preserving order, deduped)."""
    seen: dict[str, None] = {}
    for match in _TOKEN_RE.finditer(prompt):
        seen.setdefault(match.group("name"), None)
    return list(seen.keys())


def _classify_doc_ref(path: str) -> DocRefKind:
    if not path:
        return "scalar"
    if path == "[]":
        return "collection"
    if "[]" in path:
        return "array"
    return "scalar"
