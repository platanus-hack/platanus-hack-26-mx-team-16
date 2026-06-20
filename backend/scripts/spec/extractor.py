"""AST-based extractor for the Doxiq backend.

Two passes:

1. **Composition pass.** Read ``backend/config/router.py`` and recover
   the final ``prefix`` and ``tags`` for every sub-router via
   ``api_router.include_router(<name>, prefix=..., tags=...)``.

2. **Per-router pass.** For every sub-router resolved in pass 1, walk
   its file for ``add_api_route(...)`` calls and
   ``@router.<verb>(...)`` decorators. For each captured route, read
   the endpoint function's signature to find Pydantic request/response
   types and docstring.

Plus a DTO scan: every ``*.py`` under
``backend/src/**/presentation/**`` is walked for ``BaseModel``
subclasses, and every ``*.py`` under
``backend/src/**/application/use_cases/**`` is walked for
dataclasses that inherit from ``common.UseCase``.

The extractor never imports or executes the backend. All work is
done with the stdlib ``ast`` module.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

from scripts.spec.models import (
    ASTGraph,
    DTONode,
    FieldNode,
    Meta,
    RouteNode,
    Unresolved,
    UseCaseNode,
    now_iso,
)

HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
PATH_PARAM_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


# ─── helpers ───────────────────────────────────────────────────────────


def _read_module(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as e:
        return None  # caller logs


def _literal_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _literal_list_of_strs(node: ast.AST) -> list[str]:
    if not isinstance(node, ast.List):
        return []
    out: list[str] = []
    for elt in node.elts:
        s = _literal_str(elt)
        if s is not None:
            out.append(s)
    return out


def _kw(call: ast.Call, name: str) -> ast.AST | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _kw_str(call: ast.Call, name: str) -> str | None:
    val = _kw(call, name)
    if val is None:
        # positional
        return None
    return _literal_str(val)


def _resolve_name(node: ast.AST, scope_names: dict[str, str]) -> str | None:
    """Return the resolved FQCN for a Name or Attribute, or None."""
    if isinstance(node, ast.Name):
        return scope_names.get(node.id)
    if isinstance(node, ast.Attribute):
        base = _resolve_name(node.value, scope_names)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    return None


def _build_scope_names(module: ast.Module) -> dict[str, str]:
    """Top-level imports → local name → FQCN."""
    scope: dict[str, str] = {}
    for stmt in module.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                local = alias.asname or alias.name.split(".")[0]
                scope[local] = alias.name
        elif isinstance(stmt, ast.ImportFrom):
            module_name = stmt.module or ""
            for alias in stmt.names:
                local = alias.asname or alias.name
                scope[local] = f"{module_name}.{alias.name}"
    return scope


def _collect_router_assignments(module: ast.Module) -> dict[str, dict[str, Any]]:
    """Top-level ``x = APIRouter(prefix=..., tags=[...])`` and chained assigns.

    Returns: {local_name: {"prefix": str, "tags": [str, ...]}}
    """
    result: dict[str, dict[str, Any]] = {}
    for stmt in module.body:
        if not isinstance(stmt, ast.Assign):
            continue
        value = stmt.value
        if not isinstance(value, ast.Call):
            continue
        func = value.func
        is_api_router = (
            (isinstance(func, ast.Name) and func.id in {"APIRouter", "FastAPI"})
            or (isinstance(func, ast.Attribute) and func.attr in {"APIRouter", "FastAPI"})
        )
        if not is_api_router:
            continue
        prefix = _kw_str(value, "prefix") or ""
        tags = _literal_list_of_strs(_kw(value, "tags") or ast.List(elts=[]))
        info = {"prefix": prefix, "tags": tags}
        for target in stmt.targets:
            if isinstance(target, ast.Name):
                result[target.id] = info
    return result


def _function_signature(
    module: ast.Module, func_name: str
) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef | None, list[ast.arg], ast.AST | None]:
    """Find a top-level function by name and return (def, args, returns)."""
    for stmt in module.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.name == func_name:
            return stmt, stmt.args.args, stmt.returns
    return None, [], None


# ─── Pass 1: composition ──────────────────────────────────────────────


def _collect_include_router_calls(module: ast.Module) -> list[dict[str, Any]]:
    """Find every ``<api>.include_router(<name>, prefix=..., tags=...)`` call.

    Returns a list of {"name": str, "prefix": str, "tags": [str, ...]}.
    The api is matched by name (any variable bound to APIRouter/FastAPI),
    which is permissive but fine for our use — config/router.py has
    exactly one api_router at the top.
    """
    calls: list[dict[str, Any]] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "include_router"):
            continue
        if not node.args:
            continue
        first = node.args[0]
        target = None
        if isinstance(first, ast.Name):
            target = first.id
        elif isinstance(first, ast.Attribute):
            target = ast.unparse(first)  # dotted path
        if not target:
            continue
        prefix = _kw_str(node, "prefix") or ""
        tags_node = _kw(node, "tags")
        tags = _literal_list_of_strs(tags_node) if tags_node is not None else []
        calls.append({"name": target, "prefix": prefix, "tags": tags})
    return calls


def discover_composition(backend_root: Path) -> dict[str, dict[str, Any]]:
    """Return {sub_router_local_name: composition_entry}.

    The composition entry is the **composition-level** data only
    (prefix and tags from the include_router call), NOT the final
    per-route path. The per-router pass combines this with each
    sub-router's local prefix.

    Each entry has:

    - ``file``: path to the sub-router's source file (relative to
      backend root)
    - ``prefix``: the prefix from the include_router call
      (e.g. ``"/v1"``)
    - ``tags``: tags from the include_router call (may be empty;
      the local APIRouter's tags take precedence in the per-router
      pass)
    """
    config_router = backend_root / "config" / "router.py"
    module = _read_module(config_router)
    if module is None:
        return {}

    scope = _build_scope_names(module)
    includes = _collect_include_router_calls(module)

    composition: dict[str, dict[str, Any]] = {}
    for inc in includes:
        target = inc["name"]
        prefix = inc["prefix"]
        tags = inc["tags"]

        if "." not in target:
            fqcn = scope.get(target)
            if not fqcn:
                continue
            module_path = ".".join(fqcn.split(".")[:-1])
            sub_file = (backend_root / module_path.replace(".", "/")).with_suffix(".py")
        else:
            target_module = ".".join(target.split(".")[:-1])
            sub_file = (backend_root / target_module.replace(".", "/")).with_suffix(".py")

        if not sub_file.exists():
            continue

        composition[target] = {
            "file": str(sub_file.relative_to(backend_root)),
            "prefix": prefix,
            "tags": tags,
        }
    return composition


# ─── Pass 2: per-router extraction ────────────────────────────────────


def _type_to_str(node: ast.AST | None) -> str:
    if node is None:
        return "Any"
    try:
        return ast.unparse(node)
    except Exception:
        return "Any"


def _extract_path_params(path: str) -> list[str]:
    return PATH_PARAM_RE.findall(path)


def _walk_routes_in_file(
    file: Path, composition_entry: dict[str, Any]
) -> list[RouteNode]:
    """Walk one sub-router file. Return RouteNode list.

    ``composition_entry`` is the **default** composition entry used when
    a file has only one sub-router. For files with multiple sub-routers
    (e.g. ``workflows/presentation/router.py`` defines six), each
    ``add_api_route`` call is bound to the LHS name, and the matching
    router's local prefix is applied.

    Only **module-level** statements are inspected. We deliberately
    do not recurse into nested functions, classes, or comprehensions
    because those rarely contain real route registration in this
    codebase and a previous version inflated the count by 6x.
    """
    module = _read_module(file)
    if module is None:
        return []

    scope = _build_scope_names(module)
    routes: list[RouteNode] = []

    # Build a map of every sub-router defined in this file:
    # local_name -> {"prefix": str, "tags": [str, ...]}
    local_routers = _collect_router_assignments(module)
    # The composition-level prefix (from include_router) is applied
    # on top of each local prefix. We strip the per-file local prefix
    # from ``composition_entry`` to avoid double-applying it.
    composition_prefix = composition_entry["prefix"]
    composition_tags = composition_entry["tags"]
    merged: dict[str, dict[str, Any]] = {}
    for name, info in local_routers.items():
        merged[name] = {
            "prefix": composition_prefix + info["prefix"],
            "tags": info["tags"] or composition_tags,
        }
    if not merged:
        # No APIRouter assignments found; fall back to a synthetic
        # entry using the composition data.
        merged["__default__"] = composition_entry

    def entry_for(name: str | None) -> dict[str, Any]:
        if name and name in merged:
            return merged[name]
        return merged.get("__default__", composition_entry)

    for node in module.body:
        # add_api_route(...) at module level
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
        elif isinstance(node, ast.Call):
            call = node
        else:
            call = None
        if call is not None and (
            (isinstance(call.func, ast.Name) and call.func.id == "add_api_route")
            or (isinstance(call.func, ast.Attribute) and call.func.attr == "add_api_route")
        ):
            target_name = None
            if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
                target_name = call.func.value.id
            route = _route_from_add_api_route(call, file, entry_for(target_name), scope)
            if route is not None:
                routes.append(route)

        # Decorator routes: @router.get("/path") or @router.<verb>(...)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                if not isinstance(decorator.func, ast.Attribute):
                    continue
                verb = decorator.func.attr.upper()
                if verb not in HTTP_METHODS:
                    continue
                path_arg = decorator.args[0] if decorator.args else None
                path = _literal_str(path_arg) if path_arg is not None else None
                if path is None:
                    continue
                route = _route_from_decorator(node, verb, path, file, composition_entry, scope)
                if route is not None:
                    routes.append(route)

    return routes


def _extract_endpoint_metadata(
    endpoint_fqcn: str,
    file: Path,
    scope: dict[str, str],
) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef | None, str | None, str | None]:
    """Find the endpoint function in ``file`` and return (def, summary, description)."""
    module = _read_module(file)
    if module is None:
        return None, None, None
    func_name = endpoint_fqcn.split(".")[-1]
    def_, _args, _ret = _function_signature(module, func_name)
    if def_ is None:
        return None, None, None
    summary = None
    description = None
    docstring = ast.get_docstring(def_)
    if docstring:
        lines = docstring.strip().splitlines()
        summary = lines[0].strip() if lines else None
        if len(lines) > 1:
            rest = "\n".join(lines[1:]).strip()
            description = rest or None
    return def_, summary, description


def _request_dto_from_endpoint(
    def_node: ast.FunctionDef | ast.AsyncFunctionDef,
    scope: dict[str, str],
) -> str | None:
    """Return FQCN of the first Pydantic-typed parameter, or None.

    We treat any parameter that has a non-``Depends``, non-primitive
    annotation as the request body, since this codebase uses Pydantic
    models for body payloads and primitive types for path/query.
    """
    for arg in def_node.args.args:
        if arg.annotation is None:
            continue
        ann = arg.annotation
        ann_str = _type_to_str(ann)
        if ann_str in {"Depends"} or ann_str.startswith("Depends"):
            continue
        if ann_str in {"Request", "Response", "BackgroundTasks", "WebSocket", "WebSocketDisconnect"}:
            continue
        if ann_str in {"str", "int", "float", "bool", "bytes"}:
            continue
        # Resolve to FQCN
        fqcn = _resolve_name(ann, scope)
        if fqcn:
            return fqcn
        # Could be a deeper expression (e.g. list[X], Optional[Y]) —
        # return the annotation as-is so the emitter can decide.
        return ann_str
    return None


def _route_from_add_api_route(
    call: ast.Call,
    file: Path,
    composition_entry: dict[str, Any],
    scope: dict[str, str],
) -> RouteNode | None:
    path: str | None = _kw_str(call, "path")
    if path is None:
        # positional first arg
        if call.args:
            path = _literal_str(call.args[0])
    if path is None:
        return None

    methods_node = _kw(call, "methods")
    methods = _literal_list_of_strs(methods_node) if methods_node is not None else []
    methods = [m.upper() for m in methods if m.upper() in HTTP_METHODS]
    if not methods:
        return None

    endpoint_node = _kw(call, "endpoint")
    if endpoint_node is None and len(call.args) >= 2:
        # positional: path is args[0], endpoint is args[1]
        endpoint_node = call.args[1]
    endpoint_fqcn = _resolve_name(endpoint_node, scope) if endpoint_node is not None else None
    if not endpoint_fqcn:
        return None

    _def, summary, description = _extract_endpoint_metadata(endpoint_fqcn, file, scope)
    request_dto = _request_dto_from_endpoint(_def, scope) if _def else None

    full_path = composition_entry["prefix"] + path
    return RouteNode(
        method=methods[0],
        path=full_path,
        endpoint_name=endpoint_fqcn.split(".")[-1],
        endpoint_fqcn=endpoint_fqcn,
        file=str(file),
        line=call.lineno,
        tags=list(composition_entry["tags"]),
        summary=summary,
        description=description,
        request_dto_fqcn=request_dto,
        path_params=_extract_path_params(full_path),
    )


def _route_from_decorator(
    def_node: ast.FunctionDef | ast.AsyncFunctionDef,
    method: str,
    path: str,
    file: Path,
    composition_entry: dict[str, Any],
    scope: dict[str, str],
) -> RouteNode | None:
    full_path = composition_entry["prefix"] + path
    fqcn = f"{scope.get('__module__', file.stem)}.{def_node.name}"
    summary, description = (None, None)
    docstring = ast.get_docstring(def_node)
    if docstring:
        lines = docstring.strip().splitlines()
        summary = lines[0].strip() if lines else None
        if len(lines) > 1:
            description = "\n".join(lines[1:]).strip() or None
    request_dto = _request_dto_from_endpoint(def_node, scope)
    return RouteNode(
        method=method,
        path=full_path,
        endpoint_name=def_node.name,
        endpoint_fqcn=fqcn,
        file=str(file),
        line=def_node.lineno,
        tags=list(composition_entry["tags"]),
        summary=summary,
        description=description,
        request_dto_fqcn=request_dto,
        path_params=_extract_path_params(full_path),
    )


# ─── DTO scan ─────────────────────────────────────────────────────────


def _field_node_from_ast(
    target: ast.AST, default: ast.AST | None
) -> tuple[str, bool, ast.AST | None, ast.Call | None]:
    """Return (name, has_default, annotation, field_call).

    ``target`` is an ``ast.AnnAssign`` for ``x: T = ...`` or an
    ``ast.Assign`` for class-level ``x = ...`` (untyped, we skip).
    """
    if not isinstance(target, ast.AnnAssign):
        return "", False, None, None
    if not isinstance(target.target, ast.Name):
        return "", False, None, None
    name = target.target.id
    has_default = target.value is not None
    field_call = None
    if isinstance(target.value, ast.Call):
        f = target.value.func
        if isinstance(f, ast.Name) and f.id == "Field":
            field_call = target.value
        elif isinstance(f, ast.Attribute) and f.attr == "Field":
            field_call = target.value
    return name, has_default, target.annotation, field_call


def _field_metadata(field_call: ast.Call | None) -> dict[str, Any]:
    """Pull description / alias / examples from ``Field(...)`` kwargs."""
    out: dict[str, Any] = {"description": None, "alias": None, "examples": []}
    if field_call is None:
        return out
    desc = _kw_str(field_call, "description")
    if desc:
        out["description"] = desc
    alias = _kw_str(field_call, "alias")
    if alias:
        out["alias"] = alias
    # examples is a list; we just keep it as JSON-friendly list
    ex_node = _kw(field_call, "examples")
    if ex_node is not None and isinstance(ex_node, ast.List):
        out["examples"] = [_literal_value(e) for e in ex_node.elts]
    return out


def _literal_value(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_literal_value(e) for e in node.elts]
    if isinstance(node, ast.Dict):
        return {(_literal_value(k) if k else None): _literal_value(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.Tuple):
        return tuple(_literal_value(e) for e in node.elts)
    return f"<expr:{type(node).__name__}>"


def _is_basemodel_subclass(cls: ast.ClassDef, scope: dict[str, str]) -> bool:
    for base in cls.bases:
        fqcn = _resolve_name(base, scope)
        if fqcn and fqcn.endswith("BaseModel"):
            return True
        if isinstance(base, ast.Name) and base.id == "BaseModel":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "BaseModel":
            return True
    return False


def _classify_dto_file(path: Path) -> tuple[bool, bool]:
    name = path.name.lower()
    is_request = "request" in name
    is_response = "response" in name
    return is_request, is_response


def scan_dtos(backend_root: Path, graph: ASTGraph) -> None:
    presentation = backend_root / "src"
    if not presentation.exists():
        return
    for path in presentation.rglob("*.py"):
        if not any(part == "presentation" for part in path.parts):
            continue
        module = _read_module(path)
        if module is None:
            graph.unresolved.files_skipped.append({"file": str(path), "reason": "syntax error"})
            continue
        scope = _build_scope_names(module)
        is_req, is_res = _classify_dto_file(path)
        for stmt in module.body:
            if not isinstance(stmt, ast.ClassDef):
                continue
            if not _is_basemodel_subclass(stmt, scope):
                continue
            fqcn = f"{'.'.join(path.relative_to(backend_root).with_suffix('').parts)}.{stmt.name}"
            fields: list[FieldNode] = []
            base_fqcns: list[str] = []
            for base in stmt.bases:
                fq = _resolve_name(base, scope)
                if fq:
                    base_fqcns.append(fq)
            for target in stmt.body:
                name, has_default, ann, field_call = _field_node_from_ast(target, None)
                if not name or ann is None:
                    continue
                meta = _field_metadata(field_call)
                required = not has_default and not _is_optional(ann)
                fields.append(
                    FieldNode(
                        name=name,
                        python_type=_type_to_str(ann),
                        required=required,
                        default=None,
                        description=meta["description"],
                        alias=meta["alias"],
                        examples=list(meta["examples"]),
                    )
                )
            graph.dtos.append(
                DTONode(
                    name=stmt.name,
                    qualname=stmt.name,
                    fqcn=fqcn,
                    file=str(path.relative_to(backend_root)),
                    line=stmt.lineno,
                    base_fqcns=base_fqcns,
                    fields=fields,
                    is_request=is_req,
                    is_response=is_res,
                )
            )


def _is_optional(ann: ast.AST) -> bool:
    """Heuristic: ``Optional[X]`` or ``X | None`` annotation."""
    if isinstance(ann, ast.Subscript):
        f = ann.value
        if isinstance(f, ast.Name) and f.id == "Optional":
            return True
        if isinstance(f, ast.Attribute) and f.attr == "Optional":
            return True
    if isinstance(ann, ast.BinOp) and isinstance(ann.op, ast.BitOr):
        # X | None
        right = ann.right
        if isinstance(right, ast.Constant) and right.value is None:
            return True
        if isinstance(right, ast.Name) and right.id == "None":
            return True
    return False


# ─── Use case scan ────────────────────────────────────────────────────


def _is_use_case_subclass(cls: ast.ClassDef, scope: dict[str, str]) -> bool:
    for base in cls.bases:
        fqcn = _resolve_name(base, scope)
        if fqcn and fqcn.endswith("interfaces.use_case.UseCase"):
            return True
        if isinstance(base, ast.Name) and base.id == "UseCase":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "UseCase":
            return True
    return False


def scan_use_cases(backend_root: Path, graph: ASTGraph) -> None:
    base = backend_root / "src"
    if not base.exists():
        return
    for path in base.rglob("*.py"):
        if "application" not in path.parts:
            continue
        if "use_cases" not in path.parts:
            continue
        module = _read_module(path)
        if module is None:
            graph.unresolved.files_skipped.append({"file": str(path), "reason": "syntax error"})
            continue
        scope = _build_scope_names(module)
        for stmt in module.body:
            if not isinstance(stmt, ast.ClassDef):
                continue
            if not _is_use_case_subclass(stmt, scope):
                continue
            if not _has_dataclass_decorator(stmt):
                continue
            fqcn = (
                f"{'.'.join(path.relative_to(backend_root).with_suffix('').parts)}.{stmt.name}"
            )
            fields: list[FieldNode] = []
            return_hint: str | None = None
            for target in stmt.body:
                if isinstance(target, ast.AnnAssign):
                    name, has_default, ann, _ = _field_node_from_ast(target, None)
                    if name and ann is not None:
                        fields.append(
                            FieldNode(
                                name=name,
                                python_type=_type_to_str(ann),
                                required=not has_default and not _is_optional(ann),
                            )
                        )
                elif isinstance(target, ast.FunctionDef) and target.name == "execute":
                    if target.returns is not None:
                        return_hint = _type_to_str(target.returns)
            graph.use_cases.append(
                UseCaseNode(
                    name=stmt.name,
                    qualname=stmt.name,
                    fqcn=fqcn,
                    file=str(path.relative_to(backend_root)),
                    line=stmt.lineno,
                    fields=fields,
                    return_type_hint=return_hint,
                )
            )


def _has_dataclass_decorator(cls: ast.ClassDef) -> bool:
    for dec in cls.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "dataclass":
            return True
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == "dataclass":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == "dataclass":
            return True
    return False


# ─── detect pydantic version ────────────────────────────────────────


def detect_pydantic_version(backend_root: Path) -> str:
    """Scan every import in backend/src for pydantic to determine version."""
    v1, v2 = False, False
    for path in (backend_root / "src").rglob("*.py"):
        module = _read_module(path)
        if module is None:
            continue
        for node in ast.walk(module):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("pydantic"):
                if node.module == "pydantic.v1":
                    v1 = True
                else:
                    v2 = True
            elif isinstance(node, ast.Import) and any(
                a.name == "pydantic" or a.name.startswith("pydantic.") for a in node.names
            ):
                v2 = True
    if v1 and v2:
        return "mixed"
    if v1:
        return "v1"
    if v2:
        return "v2"
    return "none"


# ─── entry point ─────────────────────────────────────────────────────


def extract(backend_root: Path) -> ASTGraph:
    meta = Meta(
        backend_root=str(backend_root),
        pydantic_version=detect_pydantic_version(backend_root),
        generated_at=now_iso(),
    )
    graph = ASTGraph(meta=meta)

    composition = discover_composition(backend_root)
    seen: set[tuple[str, str]] = set()
    for _name, entry in composition.items():
        file = backend_root / entry["file"]
        try:
            routes = _walk_routes_in_file(file, entry)
        except Exception as e:  # defensive: never crash the pipeline
            graph.unresolved.files_skipped.append({"file": entry["file"], "reason": f"walk error: {e}"})
            continue
        for route in routes:
            key = (route.method, route.path)
            if key in seen:
                continue
            seen.add(key)
            graph.routes.append(route)

    scan_dtos(backend_root, graph)
    scan_use_cases(backend_root, graph)
    return graph


def extract_to_file(backend_root: Path, out_path: Path) -> ASTGraph:
    graph = extract(backend_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(graph.to_dict(), indent=2, ensure_ascii=False))
    return graph
