"""Unit tests for the kebab-case slugify helper."""

from expects import equal, expect, match

from src.common.domain.services.slugify import DEFAULT_SLUG, slugify

# Kebab-case slug shape (lowercase alnum words joined by single hyphens).
SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


def test_slugify__lowercases_and_kebab_cases():
    result = slugify("My Knowledge Base FILE")

    expect(result).to(equal("my-knowledge-base-file"))


def test_slugify__strips_diacritics():
    result = slugify("Constitución Política")

    expect(result).to(equal("constitucion-politica"))


def test_slugify__truncates_to_max_length():
    long = "a" * 200

    result = slugify(long, max_length=20)

    expect(len(result)).to(equal(20))


def test_slugify__falls_back_to_default_when_empty():
    result = slugify("")

    expect(result).to(equal(DEFAULT_SLUG))


def test_slugify__falls_back_to_default_when_only_separators():
    result = slugify("   ---   ")

    expect(result).to(equal(DEFAULT_SLUG))


def test_slugify__matches_kb_slug_pattern():
    result = slugify("Política Anti-Lavado 2025!")

    expect(result).to(match(SLUG_PATTERN))
