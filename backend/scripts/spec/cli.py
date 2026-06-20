"""CLI entry point for the OpenSpec pipeline.

Subcommands (each a stub in v0.1.0; implemented in later phases):

- extract: AST walks → ast-graph.json
- emit:    ast-graph.json → openapi.json
- audit:   openapi.json + ast-graph.json → audit-report.md
- all:     extract && emit && audit
- diff:    show diff between working-tree openapi.json and HEAD
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT_DEFAULT = Path(__file__).resolve().parents[2]
DOCS_REPO_ROOT = BACKEND_ROOT_DEFAULT.parent
OUT_DEFAULT = DOCS_REPO_ROOT / "docs" / "src" / "content" / "api" / "_generated" / "openapi.json"
BUILD_DIR = Path(__file__).resolve().parent / "_build"


def _add_io_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--backend-root",
        type=Path,
        default=BACKEND_ROOT_DEFAULT,
        help=f"Path to the backend root (default: {BACKEND_ROOT_DEFAULT})",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_DEFAULT,
        help=f"Output path for the emitted OpenAPI spec (default: {OUT_DEFAULT})",
    )


def cmd_extract(args: argparse.Namespace) -> int:
    from scripts.spec.extractor import extract_to_file

    out = BUILD_DIR / "ast-graph.json"
    print(f"[extract] backend={args.backend_root}")
    print(f"[extract] out={out}")
    graph = extract_to_file(args.backend_root, out)
    print(
        f"[extract] routes={len(graph.routes)} dtos={len(graph.dtos)} "
        f"use_cases={len(graph.use_cases)} pydantic={graph.meta.pydantic_version}"
    )
    if graph.unresolved.files_skipped:
        print(f"[extract] WARN: skipped {len(graph.unresolved.files_skipped)} files (syntax errors)")
    return 0


def cmd_emit(args: argparse.Namespace) -> int:
    import json
    from scripts.spec.emitter import emit_to_file
    from scripts.spec.models import ASTGraph

    graph_path = BUILD_DIR / "ast-graph.json"
    if not graph_path.exists():
        print(f"[emit]    ERROR: {graph_path} not found. Run 'extract' first.")
        return 1
    graph_data = json.loads(graph_path.read_text())
    # Re-hydrate into a stub ASTGraph (the emitter only needs the data).
    graph = ASTGraph.from_dict(graph_data)  # type: ignore[attr-defined]
    api = emit_to_file(graph, args.backend_root, args.out, allow_unresolved=args.allow_unresolved)
    unresolved = api.x_unresolved_types or []
    print(
        f"[emit]    out={args.out} paths={len(api.paths)} "
        f"schemas={len(api.components.schemas)} unresolved={len(unresolved)}"
    )
    if unresolved:
        print(f"[emit]    WARN: {len(unresolved)} unresolved types (x-unresolved-types)")
        for u in unresolved[:5]:
            print(f"          - {u}")
    if unresolved and not args.allow_unresolved:
        return 2
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    print(f"[audit]   spec={args.spec}")
    print(f"[audit]   no-llm={args.no_llm} model={args.model} fail-under={args.fail_under}")
    print("[audit]   TODO: not implemented yet (Phase 4)")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    print(f"[diff]    out={args.out}")
    print("[diff]    TODO: not implemented yet (Phase 6)")
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    rc = cmd_extract(args)
    if rc != 0:
        return rc
    rc = cmd_emit(args)
    if rc != 0:
        return rc
    audit_args = argparse.Namespace(
        spec=args.out,
        no_llm=args.no_llm,
        model=args.model,
        fail_under=args.fail_under,
        report=BUILD_DIR / "audit-report.md",
    )
    return cmd_audit(audit_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m spec",
        description="Doxiq API OpenSpec pipeline.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract", help="AST walks → ast-graph.json")
    _add_io_flags(p_extract)
    p_extract.set_defaults(func=cmd_extract)

    p_emit = sub.add_parser("emit", help="ast-graph.json → openapi.json")
    _add_io_flags(p_emit)
    p_emit.add_argument(
        "--allow-unresolved",
        action="store_true",
        help="Allow unresolved types in the output without exiting non-zero.",
    )
    p_emit.set_defaults(func=cmd_emit)

    p_audit = sub.add_parser("audit", help="audit openapi.json and write a report")
    p_audit.add_argument(
        "--spec",
        type=Path,
        default=OUT_DEFAULT,
        help="Path to the openapi.json to audit.",
    )
    p_audit.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip the LLM call; use the heuristic auditor only.",
    )
    p_audit.add_argument(
        "--model",
        default=None,
        help="LLM model name (overrides SPEC_AUDITOR_MODEL).",
    )
    p_audit.add_argument(
        "--fail-under",
        type=int,
        default=0,
        help="Exit non-zero if coverage score is below N.",
    )
    p_audit.add_argument(
        "--report",
        type=Path,
        default=BUILD_DIR / "audit-report.md",
        help="Where to write the markdown report.",
    )
    p_audit.set_defaults(func=cmd_audit)

    p_diff = sub.add_parser("diff", help="show diff vs HEAD's openapi.json")
    _add_io_flags(p_diff)
    p_diff.set_defaults(func=cmd_diff)

    p_all = sub.add_parser("all", help="run extract && emit && audit")
    _add_io_flags(p_all)
    p_all.add_argument("--no-llm", action="store_true")
    p_all.add_argument("--model", default=None)
    p_all.add_argument("--fail-under", type=int, default=0)
    p_all.set_defaults(func=cmd_all)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
