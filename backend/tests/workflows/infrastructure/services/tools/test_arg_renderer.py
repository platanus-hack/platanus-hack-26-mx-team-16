"""E3: enrich arg/URL rendering — rule syntax (@slug, {{token}}) + {placeholders}."""

from datetime import UTC, datetime
from uuid import uuid4

from expects import be_a, equal, expect, raise_error

from src.workflows.domain.rules.kind_protocol import EvalDocumentInput
from src.workflows.infrastructure.services.tools.arg_renderer import (
    ToolConfigRenderError,
    UnresolvedRefError,
    collect_doc_refs,
    collect_tokens,
    render_args,
    render_path,
)


def _doc(slug: str = "oficio", fields: dict | None = None) -> EvalDocumentInput:
    return EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug=slug,
        extracted_fields=fields or {"numero": "123", "juzgado": {"nombre": "Quinto Civil"}},
    )


# ── collection ──────────────────────────────────────────────────────────────


def test_collect__finds_bare_braced_refs_and_tokens_full_string_only():
    args = {
        "a": "@oficio.numero",
        "b": "@{oficio}.juzgado.nombre",
        "c": "{{now}}",
        "d": "texto con @oficio.numero adentro",  # not full-string → ignored
        "nested": {"e": ["{{today}}"]},
    }

    refs = collect_doc_refs(args)
    tokens = collect_tokens(args)

    expect(sorted(r.path for r in refs)).to(equal(["juzgado.nombre", "numero"]))
    expect(tokens).to(equal(["now", "today"]))


# ── render_args ─────────────────────────────────────────────────────────────


def test_render_args__resolves_bare_and_braced_doc_refs():
    args = {"q": "@oficio.numero", "court": "@{oficio}.juzgado.nombre", "static": "x"}

    rendered = render_args(args, documents=[_doc()], tokens={})

    expect(rendered).to(equal({"q": "123", "court": "Quinto Civil", "static": "x"}))


def test_render_args__resolves_system_token_to_json_safe_value():
    moment = datetime(2026, 6, 9, 12, 0, tzinfo=UTC)

    rendered = render_args({"at": "{{now}}"}, documents=[], tokens={"now": moment})

    expect(rendered).to(equal({"at": moment.isoformat()}))


def test_render_args__missing_document_raises_unresolved():
    expect(lambda: render_args({"q": "@poliza.numero"}, documents=[_doc("oficio")], tokens={})).to(
        raise_error(UnresolvedRefError)
    )


def test_render_args__missing_field_raises_unresolved():
    expect(lambda: render_args({"q": "@oficio.no_existe"}, documents=[_doc()], tokens={})).to(
        raise_error(UnresolvedRefError)
    )


def test_render_args__undeclared_token_is_config_error():
    expect(lambda: render_args({"x": "{{nope}}"}, documents=[], tokens={})).to(
        raise_error(ToolConfigRenderError)
    )


# ── render_path ─────────────────────────────────────────────────────────────


def test_render_path__substitutes_quotes_and_reports_consumed_keys():
    rendered, consumed = render_path("/policies/{policy_id}/check", {"policy_id": "AB 1", "q": "x"})

    expect(rendered).to(equal("/policies/AB%201/check"))
    expect(consumed).to(equal({"policy_id"}))


def test_render_path__unknown_placeholder_is_config_error():
    expect(lambda: render_path("/p/{missing}", {"q": "x"})).to(raise_error(ToolConfigRenderError))


def test_render_path__non_scalar_value_is_unresolved():
    expect(lambda: render_path("/p/{obj}", {"obj": {"a": 1}})).to(raise_error(UnresolvedRefError))


def test_render_path__without_placeholders_passes_through():
    rendered, consumed = render_path("/lookup", {"q": "x"})

    expect(rendered).to(equal("/lookup"))
    expect(consumed).to(be_a(set))
    expect(len(consumed)).to(equal(0))
