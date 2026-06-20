"""Internal data model for the extracted AST graph.

Every field is JSON-serialisable. The graph itself is the on-disk
artefact that the emitter reads.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class FieldNode:
    name: str
    python_type: str
    required: bool
    default: Any = None
    description: str | None = None
    alias: str | None = None
    examples: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DTONode:
    """A Pydantic BaseModel subclass."""

    name: str
    qualname: str
    fqcn: str  # module.qualname — the dedup key
    file: str
    line: int
    base_fqcns: list[str]  # parent classes, fully qualified
    fields: list[FieldNode] = field(default_factory=list)
    is_request: bool = False
    is_response: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["fields"] = [f.to_dict() if isinstance(f, FieldNode) else f for f in d["fields"]]
        return d


@dataclass
class UseCaseNode:
    """A dataclass that inherits from common UseCase."""

    name: str
    qualname: str
    fqcn: str
    file: str
    line: int
    fields: list[FieldNode] = field(default_factory=list)
    return_type_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["fields"] = [f.to_dict() if isinstance(f, FieldNode) else f for f in d["fields"]]
        return d


@dataclass
class RouteNode:
    """A captured HTTP route."""

    method: str  # "GET", "POST", ...
    path: str  # full path including prefix
    endpoint_name: str
    endpoint_fqcn: str
    file: str
    line: int
    tags: list[str] = field(default_factory=list)
    summary: str | None = None
    description: str | None = None
    request_dto_fqcn: str | None = None
    response_dto_fqcn: str | None = None
    path_params: list[str] = field(default_factory=list)
    query_params: list[FieldNode] = field(default_factory=list)
    requires_auth: bool = True
    response_status: int = 200
    # Resolved DTO snapshots, filled by the emitter pass so the
    # emitter doesn't need to re-walk the AST.
    request_dto: DTONode | None = None
    response_dto: DTONode | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["query_params"] = [p.to_dict() if isinstance(p, FieldNode) else p for p in d["query_params"]]
        if self.request_dto is not None:
            d["request_dto"] = self.request_dto.to_dict() if isinstance(self.request_dto, DTONode) else self.request_dto
        if self.response_dto is not None:
            d["response_dto"] = self.response_dto.to_dict() if isinstance(self.response_dto, DTONode) else self.response_dto
        return d


@dataclass
class Unresolved:
    imports: list[str] = field(default_factory=list)
    types: list[str] = field(default_factory=list)
    files_skipped: list[dict[str, str]] = field(default_factory=list)


@dataclass
class Meta:
    backend_root: str
    pydantic_version: str  # "v1" | "v2" | "mixed" | "none"
    generated_at: str
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ASTGraph:
    meta: Meta
    routes: list[RouteNode] = field(default_factory=list)
    use_cases: list[UseCaseNode] = field(default_factory=list)
    dtos: list[DTONode] = field(default_factory=list)
    unresolved: Unresolved = field(default_factory=Unresolved)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.meta.schema_version,
            "meta": self.meta.to_dict(),
            "routes": [r.to_dict() for r in self.routes],
            "use_cases": [u.to_dict() for u in self.use_cases],
            "dtos": [d.to_dict() for d in self.dtos],
            "unresolved": asdict(self.unresolved),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ASTGraph":
        def _fields(items: list[dict[str, Any]]) -> list[FieldNode]:
            return [FieldNode(**item) for item in items]

        routes = []
        for r in d.get("routes", []):
            data = dict(r)
            data["query_params"] = _fields(data.get("query_params", []))
            # request_dto/response_dto are already serialised DTOs in
            # the graph JSON; the emitter doesn't need them rehydrated
            # because it works from the dtos list.
            data.pop("request_dto", None)
            data.pop("response_dto", None)
            routes.append(RouteNode(**data))

        use_cases = []
        for u in d.get("use_cases", []):
            data = dict(u)
            data["fields"] = _fields(data.get("fields", []))
            use_cases.append(UseCaseNode(**data))

        dtos = []
        for x in d.get("dtos", []):
            data = dict(x)
            data["fields"] = _fields(data.get("fields", []))
            dtos.append(DTONode(**data))

        return cls(
            meta=Meta(**d["meta"]),
            routes=routes,
            use_cases=use_cases,
            dtos=dtos,
            unresolved=Unresolved(**d.get("unresolved", {})),
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
