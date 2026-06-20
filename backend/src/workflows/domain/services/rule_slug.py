"""Slug helpers for WorkflowRule (E2 · spec case-output §`@rule.<slug>`).

El slug identifica la regla en la proyección x-source del output del caso
(`@rule.dti_score`). Se deriva del nombre AL CREAR la regla y después es
ESTABLE: renombrar la regla NO regenera el slug (a diferencia del updater de
doc-types) — un `@rule.<slug>` referenciado por un output_schema no puede
romperse por un rename cosmético.
"""

from __future__ import annotations

from slugify import slugify

DEFAULT_RULE_SLUG = "rule"


def slugify_rule_name(name: str) -> str:
    base = slugify(name, separator="_")
    if not base:
        return DEFAULT_RULE_SLUG
    # La gramática de @rule.<slug> (parse_doc_refs) exige identificadores que
    # no empiecen por dígito — un slug "3_meses" sería irreferenciable.
    if base[0].isdigit():
        base = f"{DEFAULT_RULE_SLUG}_{base}"
    return base
