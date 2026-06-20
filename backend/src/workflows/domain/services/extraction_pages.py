"""Helper for deriving the unique page numbers covered by an extraction.

Given the `mapped_extraction` tree produced by the `extract_fields` Lambda
(leaves shaped `{value, page_number, bbox: [{page_number}], ...}`), walks
the structure and returns a sorted list of unique `page_number`s with
visual evidence on the page. Used by the workflow activity that finalizes
each `WorkflowDocument`.
"""

from __future__ import annotations


def collect_extraction_pages(mapped_output: dict | None) -> list[int]:
    if not mapped_output:
        return []
    pages: set[int] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if "value" in node and "bbox" in node:
                pn = node.get("page_number")
                if isinstance(pn, int):
                    pages.add(pn)
                for hit in node.get("bbox") or []:
                    if isinstance(hit, dict):
                        p = hit.get("page_number")
                        if isinstance(p, int):
                            pages.add(p)
                return
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(mapped_output)
    return sorted(pages)
