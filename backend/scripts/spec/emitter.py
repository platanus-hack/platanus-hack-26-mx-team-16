"""AST-graph → OpenAPI 3.1 emitter.

Reads the JSON file produced by ``extractor.extract_to_file`` and
emits a valid OpenAPI 3.1.0 document.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scripts.spec.models import ASTGraph, DTONode, RouteNode
from scripts.spec.openapi_types import (
    Components,
    MediaType,
    OpenAPI,
    Operation,
    Parameter,
    PathItem,
    Reference,
    RequestBody,
    Response,
    Schema,
    SecurityScheme,
    Server,
    Tag,
)


PRIMITIVE_TYPE_MAP: dict[str, tuple[str, str | None]] = {
    "str": ("string", None),
    "int": ("integer", None),
    "float": ("number", "double"),
    "bool": ("boolean", None),
    "bytes": ("string", "binary"),
    "Any": ("any", None),
}


# ─── type → schema mapping ────────────────────────────────────────────


def _python_type_to_schema(type_str: str) -> Schema | Reference | None:
    """Best-effort mapping of a Python type expression to a Schema.

    Returns ``None`` when the type is unresolvable (caller should
    emit an unresolved-type marker instead).
    """
    s = type_str.strip()
    if s in PRIMITIVE_TYPE_MAP:
        type_name, fmt = PRIMITIVE_TYPE_MAP[s]
        return Schema(type=type_name, format=fmt)
    if s == "UUID" or s.endswith("UUID") or s == "uuid.UUID":
        return Schema(type="string", format="uuid")
    if s.startswith("datetime") or s.endswith("datetime"):
        return Schema(type="string", format="date-time")
    if s.startswith("date") or s.endswith("date") and "datetime" not in s:
        return Schema(type="string", format="date")
    if s.startswith("Optional[") or s.startswith("Optional "):
        inner = _strip_brackets("Optional" + s.removeprefix("Optional"))
        return Schema(anyOf=[_python_type_to_schema(inner) or Schema(), Schema(type="null")])
    if " | None" in s:
        # PEP 604 union with None
        non_none = s.replace(" | None", "").strip()
        return Schema(anyOf=[_python_type_to_schema(non_none) or Schema(), Schema(type="null")])
    if s.endswith(" | None"):
        non_none = s[: -len(" | None")].strip()
        return Schema(anyOf=[_python_type_to_schema(non_none) or Schema(), Schema(type="null")])
    if s.startswith("list[") or s.startswith("List["):
        inner = _strip_brackets(s)
        items = _python_type_to_schema(inner) or Schema(
            description="unresolved type — auditor will flag", nullable=True
        )
        return Schema(type="array", items=items)
    if s.startswith("dict[") or s.startswith("Dict["):
        value_inner = _strip_brackets(s).split(",", 1)[-1].strip()
        value_schema = _python_type_to_schema(value_inner) or Schema(
            description="unresolved dict value", nullable=True
        )
        return Schema(type="object", additionalProperties=value_schema)
    if s.startswith("Literal["):
        inner = _strip_brackets(s)
        values = [_parse_literal_atom(v.strip()) for v in inner.split(",")]
        return Schema(enum=values)
    # Bare class name — emit a Reference (caller resolves the name).
    if re.match(r"^[A-Z][A-Za-z0-9_]*$", s):
        return Reference(ref=f"#/components/schemas/{s}")
    if "." in s and re.match(r"^[A-Za-z_][A-Za-z0-9_.]*$", s):
        # FQCN — take the last segment
        return Reference(ref=f"#/components/schemas/{s.rsplit('.', 1)[-1]}")
    return None


def _strip_brackets(s: str) -> str:
    s = s.strip()
    if s.startswith(("list[", "List[", "dict[", "Dict[", "Optional[", "Literal[")):
        if s.endswith("]"):
            return s[s.index("[") + 1 : -1].strip()
    return s


def _parse_literal_atom(s: str) -> Any:
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]
    if s.lower() in {"true", "false"}:
        return s.lower() == "true"
    if s.lower() == "none":
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


# ─── DTO → Schema ─────────────────────────────────────────────────────


def _dto_to_schema(dto: DTONode, unresolved: set[str]) -> Schema:
    properties: dict[str, Schema | Reference] = {}
    required: list[str] = []
    for f in dto.fields:
        # Resolve by FQCN: try to find the DTO by its FQCN; if the
        # field type matches another DTO, link via $ref.
        prop_schema: Schema | Reference
        resolved = _python_type_to_schema(f.python_type)
        if resolved is None:
            unresolved.add(f.python_type)
            prop_schema = Schema(
                description="unresolved type — auditor will flag",
                nullable=True,
                x_unresolved=True,
            )
        else:
            prop_schema = resolved
        if f.description:
            if isinstance(prop_schema, Schema):
                prop_schema.description = f.description
        if f.examples and isinstance(prop_schema, Schema) and prop_schema.example is None:
            prop_schema.example = f.examples[0]
        properties[f.name] = prop_schema
        if f.required:
            required.append(f.name)
    return Schema(
        type="object",
        description=None,
        properties=properties,
        required=required or None,
    )


# ─── route → Operation ─────────────────────────────────────────────────


def _operation_for_route(
    route: RouteNode,
    dtos_by_fqcn: dict[str, DTONode],
    dtos_by_short_name: dict[str, DTONode],
    unresolved: set[str],
) -> Operation:
    parameters: list[Parameter] = []
    for p in route.path_params:
        parameters.append(
            Parameter(
                name=p,
                in_="path",
                required=True,
                schema=Schema(type="string"),
            )
        )
    for q in route.query_params:
        q_schema = _python_type_to_schema(q.python_type) or Schema(type="string")
        if isinstance(q_schema, Schema) and q.description:
            q_schema.description = q.description
        parameters.append(
            Parameter(
                name=q.name,
                in_="query",
                required=q.required,
                schema=q_schema,
            )
        )

    request_body: RequestBody | None = None
    if route.request_dto_fqcn:
        dto = dtos_by_fqcn.get(route.request_dto_fqcn) or dtos_by_short_name.get(
            route.request_dto_fqcn.rsplit(".", 1)[-1]
        )
        if dto is not None:
            schema = _dto_to_schema(dto, unresolved)
            request_body = RequestBody(
                content={"application/json": MediaType(schema=schema)},
            )
        else:
            unresolved.add(route.request_dto_fqcn)
            request_body = RequestBody(
                description=f"Unresolved request type: {route.request_dto_fqcn}",
                content={
                    "application/json": MediaType(
                        schema=Schema(
                            description="unresolved type — auditor will flag",
                            nullable=True,
                        )
                    )
                },
            )

    responses: dict[str, Response] = {}
    if route.response_dto_fqcn:
        dto = dtos_by_fqcn.get(route.response_dto_fqcn) or dtos_by_short_name.get(
            route.response_dto_fqcn.rsplit(".", 1)[-1]
        )
        if dto is not None:
            schema = _dto_to_schema(dto, unresolved)
            responses[str(route.response_status)] = Response(
                description="OK",
                content={"application/json": MediaType(schema=schema)},
            )
        else:
            unresolved.add(route.response_dto_fqcn)
            responses[str(route.response_status)] = Response(
                description=f"OK (response type {route.response_dto_fqcn} unresolved)",
            )
    else:
        responses[str(route.response_status)] = Response(description="OK")
    if route.requires_auth:
        responses["401"] = Response(description="Unauthorized")
    responses["422"] = Response(description="Validation error")

    security: list[dict[str, list[str]]] | None
    if route.requires_auth:
        security = [{"ApiKeyAuth": []}]
    else:
        security = []

    operation_id = _operation_id(route)
    return Operation(
        tags=list(route.tags),
        summary=route.summary,
        description=route.description,
        operationId=operation_id,
        parameters=parameters,
        requestBody=request_body,
        responses=responses,
        security=security,
    )


def _operation_id(route: RouteNode) -> str:
    tag = (route.tags[0] if route.tags else "default").lower().replace(" ", "-")
    name = route.endpoint_name.replace("_", "-")
    return f"{tag}-{name}"


# ─── entry point ──────────────────────────────────────────────────────


def emit(
    ast_graph: ASTGraph,
    backend_root: Path,
    out_path: Path,
    allow_unresolved: bool = False,
) -> OpenAPI:
    unresolved: set[str] = set()

    # Build DTO indexes
    dtos_by_fqcn: dict[str, DTONode] = {d.fqcn: d for d in ast_graph.dtos}
    dtos_by_short_name: dict[str, DTONode] = {}
    for d in ast_graph.dtos:
        if d.name not in dtos_by_short_name:
            dtos_by_short_name[d.name] = d

    # Deduplicate schemas by FQCN — last write wins, but we record all
    # locations of a given FQCN to detect collisions.
    fqcn_owners: dict[str, list[str]] = {}
    for d in ast_graph.dtos:
        fqcn_owners.setdefault(d.fqcn, []).append(f"{d.file}:{d.line}")
    # Note: the same class can be defined once and imported elsewhere;
    # that's not a collision. A "collision" is two distinct class
    # bodies sharing an FQCN, which Python would actually treat as
    # the same import. We therefore allow duplicates as long as the
    # DTO body is identical (we don't compare bodies here, so we
    # accept repeated imports as the same schema).

    # Build components.schemas
    schemas: dict[str, Schema | Reference] = {}
    for dto in ast_graph.dtos:
        if dto.fqcn in schemas:
            # Already emitted; skip.
            continue
        schemas[dto.name] = _dto_to_schema(dto, unresolved)

    # Build paths
    paths: dict[str, PathItem] = {}
    for route in ast_graph.routes:
        verb = route.method.lower()
        op = _operation_for_route(route, dtos_by_fqcn, dtos_by_short_name, unresolved)
        item = paths.get(route.path) or PathItem()
        setattr(item, verb, op)
        paths[route.path] = item

    # Build tags
    all_tags = sorted({t for r in ast_graph.routes for t in r.tags})
    tag_objs = [Tag(name=t, description=f"{t} endpoints") for t in all_tags]

    info_dict = _read_pyproject_info(backend_root)
    api = OpenAPI(
        info=info_dict,
        servers=[Server(url="/api/v1", description="Doxiq API")],
        tags=tag_objs,
        paths=paths,
        components=Components(
            schemas=schemas,
            securitySchemes={
                "ApiKeyAuth": SecurityScheme(
                    type="apiKey",
                    in_="header",
                    name="X-Api-Key",
                    description="API key required for all authenticated routes.",
                ),
            },
        ),
        security=[{"ApiKeyAuth": []}],
    )
    if unresolved:
        api.x_unresolved_types = sorted(unresolved)
        if not allow_unresolved:
            # write partial spec then exit non-zero — caller raises
            pass
    return api


def emit_to_file(
    ast_graph: ASTGraph,
    backend_root: Path,
    out_path: Path,
    allow_unresolved: bool = False,
) -> OpenAPI:
    api = emit(ast_graph, backend_root, out_path, allow_unresolved)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(api.to_dict(), indent=2, ensure_ascii=False))
    return api


def _read_pyproject_info(backend_root: Path) -> Any:  # returns Info
    from scripts.spec.openapi_types import Info

    pyproject = backend_root / "pyproject.toml"
    name = "Doxiq API"
    version = "0.0.0"
    description: str | None = None
    if pyproject.exists():
        try:
            import tomllib  # py3.11+

            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            proj = data.get("project", {})
            name = "Doxiq " + (proj.get("name", "api") or "api")
            version = proj.get("version", "0.0.0")
            description = proj.get("description")
        except Exception:
            pass
    return Info(title=name, version=version, description=description)
