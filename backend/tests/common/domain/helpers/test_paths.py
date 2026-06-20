"""Unit tests for the storage-key filename sanitizer."""

import unicodedata

from expects import equal, expect

from src.common.domain.helpers.paths import safe_storage_key_name


def test_safe_storage_key_name__keeps_plain_ascii_name():
    result = safe_storage_key_name("invoice.pdf")

    expect(result).to(equal("invoice.pdf"))


def test_safe_storage_key_name__preserves_accented_letters_as_nfc():
    # NFD input ("o" + combining acute) — the exact shape that crashed download.
    nfd = "Documentación.pdf"

    result = safe_storage_key_name(nfd)

    expect(result).to(equal(unicodedata.normalize("NFC", nfd)))


def test_safe_storage_key_name__strips_forward_slash_path_components():
    result = safe_storage_key_name("facturas/2024/x.pdf")

    expect(result).to(equal("x.pdf"))


def test_safe_storage_key_name__strips_backslash_path_components():
    result = safe_storage_key_name("C:\\Users\\bob\\report.xlsx")

    expect(result).to(equal("report.xlsx"))


def test_safe_storage_key_name__neutralizes_parent_traversal():
    result = safe_storage_key_name("../../etc/passwd")

    expect(result).to(equal("passwd"))


def test_safe_storage_key_name__removes_control_characters():
    result = safe_storage_key_name("re\x00port\t.csv")

    expect(result).to(equal("report.csv"))


def test_safe_storage_key_name__trims_surrounding_whitespace():
    result = safe_storage_key_name("   spaced.png   ")

    expect(result).to(equal("spaced.png"))


def test_safe_storage_key_name__falls_back_when_none():
    result = safe_storage_key_name(None)

    expect(result).to(equal("unnamed"))


def test_safe_storage_key_name__falls_back_when_only_separators():
    result = safe_storage_key_name("..")

    expect(result).to(equal("unnamed"))


def test_safe_storage_key_name__falls_back_when_only_control_chars():
    result = safe_storage_key_name("\x00\x01\x02")

    expect(result).to(equal("unnamed"))
