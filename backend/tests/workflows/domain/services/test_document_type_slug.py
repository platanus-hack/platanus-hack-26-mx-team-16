from expects import equal, expect

from src.workflows.domain.services.document_type_slug import (
    compute_unique_slug,
    slugify_doctype_name,
)


def test_slugify_doctype_name__lowercases_and_underscore_separates():
    expect(slugify_doctype_name("Cedula de Identidad")).to(equal("cedula_de_identidad"))


def test_slugify_doctype_name__strips_diacritics():
    expect(slugify_doctype_name("Cédula")).to(equal("cedula"))


def test_slugify_doctype_name__falls_back_when_name_has_no_slug_chars():
    expect(slugify_doctype_name("!!!")).to(equal("doctype"))


def test_compute_unique_slug__returns_base_when_unused():
    expect(compute_unique_slug("cedula", set())).to(equal("cedula"))


def test_compute_unique_slug__appends_suffix_starting_at_one():
    expect(compute_unique_slug("cedula", {"cedula"})).to(equal("cedula_1"))


def test_compute_unique_slug__skips_taken_suffixes():
    expect(compute_unique_slug("cedula", {"cedula", "cedula_1", "cedula_2"})).to(equal("cedula_3"))


def test_compute_unique_slug__ignores_unrelated_slugs():
    expect(compute_unique_slug("invoice", {"cedula", "cedula_1"})).to(equal("invoice"))
