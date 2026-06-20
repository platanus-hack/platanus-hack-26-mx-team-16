from collections.abc import Iterator, Sequence


def iter_leaves(node: object) -> Iterator[object]:
    if isinstance(node, dict):
        for value in node.values():
            yield from iter_leaves(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_leaves(item)
    else:
        yield node


def count_fields(node: object) -> int:
    if not isinstance(node, dict):
        return 0
    return sum(1 for _ in iter_leaves(node))


def count_pages(documents: Sequence) -> int:
    """Total de páginas que abarcan los documentos clasificados (vía ``page_range``)."""
    return sum(
        (doc.page_range["to"] - doc.page_range["from"] + 1)
        for doc in documents
        if doc.page_range
    )


def count_validations(items: list | None, *, passed: bool) -> int:
    if not items:
        return 0
    expected = "passed" if passed else "failed"
    return sum(1 for v in items if v.get("status") == expected)
