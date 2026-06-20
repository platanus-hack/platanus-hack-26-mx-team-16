"""Unit tests for the prompt reference parsers (`@{}`, `#{}`, `{{}}`)."""

from expects import be_empty, be_none, equal, expect

from src.workflows.infrastructure.services.rules.kinds._shared.refs import (
    parse_doc_refs,
    parse_kb_refs,
    parse_tokens,
)


def test_parse_doc_refs__scalar_with_path():
    refs = parse_doc_refs("validate @{cedula}.numero formato")

    expect(len(refs)).to(equal(1))
    expect(refs[0].slug).to(equal("cedula"))
    expect(refs[0].path).to(equal("numero"))
    expect(refs[0].kind).to(equal("scalar"))
    expect(refs[0].raw).to(equal("@{cedula}.numero"))


def test_parse_doc_refs__nested_path():
    refs = parse_doc_refs("@{factura}.emisor.razon_social")

    expect(refs[0].path).to(equal("emisor.razon_social"))
    expect(refs[0].kind).to(equal("scalar"))


def test_parse_doc_refs__array_path_classified_as_array():
    refs = parse_doc_refs("@{factura}.items[].subtotal")

    expect(refs[0].slug).to(equal("factura"))
    expect(refs[0].kind).to(equal("array"))


def test_parse_doc_refs__bare_collection_marker():
    refs = parse_doc_refs("count @{invoice}[]")

    expect(refs[0].slug).to(equal("invoice"))
    expect(refs[0].kind).to(equal("collection"))


def test_parse_doc_refs__bare_slug_is_scalar_no_path():
    refs = parse_doc_refs("attach @{contract}")

    expect(refs[0].slug).to(equal("contract"))
    expect(refs[0].path).to(be_none)
    expect(refs[0].kind).to(equal("scalar"))


def test_parse_doc_refs__deduplicates_by_raw():
    refs = parse_doc_refs("compare @{dni}.rut with @{dni}.rut again")

    expect(len(refs)).to(equal(1))


def test_parse_doc_refs__no_refs_returns_empty():
    refs = parse_doc_refs("plain prompt with no references")

    expect(refs).to(be_empty)


# ---------------- left-boundary guard (C17) ---------------- #


def test_parse_doc_refs__ignores_email_address():
    # An email is not a document ref — a rule prompt mentioning one must compile.
    refs = parse_doc_refs("escribir a soporte@empresa.com si falta el dato")

    expect(refs).to(be_empty)


def test_parse_doc_refs__ignores_chained_at_handle():
    refs = parse_doc_refs("contactar @{cliente}.email o a@b.co")

    # Only the real braced ref is parsed; the bare `a@b.co` email is ignored.
    expect(len(refs)).to(equal(1))
    expect(refs[0].slug).to(equal("cliente"))
    expect(refs[0].path).to(equal("email"))


def test_parse_doc_refs__bare_ref_still_matches_at_word_start():
    refs = parse_doc_refs("compara @solicitud.monto con el limite")

    expect(len(refs)).to(equal(1))
    expect(refs[0].slug).to(equal("solicitud"))
    expect(refs[0].path).to(equal("monto"))


def test_parse_kb_refs__extracts_slugs_in_order():
    slugs = parse_kb_refs("see #{policy_a} and #{policy_b}, also #{policy_a} again")

    expect(slugs).to(equal(["policy_a", "policy_b"]))


def test_parse_kb_refs__no_refs_returns_empty():
    expect(parse_kb_refs("no kb refs here")).to(be_empty)


def test_parse_kb_refs__ignores_chained_hash_after_word():
    # `issue#123` / `color#fff` carry a left word boundary → not KB refs.
    # (A space-prefixed `#slug` is still a legitimate reference; only the
    # chained form is excluded by the lookbehind.)
    slugs = parse_kb_refs("ver issue#123 y el color#fff en el documento")

    expect(slugs).to(be_empty)


def test_parse_kb_refs__bare_ref_still_matches_at_word_start():
    slugs = parse_kb_refs("revisa #comunas antes de validar")

    expect(slugs).to(equal(["comunas"]))


def test_parse_tokens__extracts_unique_in_order():
    tokens = parse_tokens("today is {{today}}, this year {{today.year}}, again {{today}}")

    expect(tokens).to(equal(["today", "today.year"]))


def test_parse_tokens__supports_dotted_names():
    tokens = parse_tokens("hi {{case.name}} from {{tenant.name}}")

    expect(tokens).to(equal(["case.name", "tenant.name"]))


def test_parse_tokens__ignores_non_token_braces():
    tokens = parse_tokens("not a token: { foo } or {  } empty")

    expect(tokens).to(be_empty)
