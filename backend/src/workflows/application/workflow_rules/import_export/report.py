from dataclasses import dataclass, field


@dataclass
class WorkflowRuleImportReport:
    created: int = 0
    overwritten: int = 0
    skipped: int = 0
    renamed: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    unresolved_kb_refs: list[str] = field(default_factory=list)
    unresolved_doc_type_slugs: list[str] = field(default_factory=list)
