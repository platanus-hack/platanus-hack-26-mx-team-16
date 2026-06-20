"""``count_pages`` (sync-gate, E1 · D1) — conteo barato de páginas antes de
despachar `mode=sync`. E6 · Caso 4 añade audio (1 audio = 1 "página" ASR).
"""

from expects import be_none, equal, expect

from src.workflows.application.processing_jobs.page_count import count_pages


def test_count_pages__image_is_one():
    expect(count_pages(b"\x89PNG...", "image/png")).to(equal(1))
    expect(count_pages(b"\xff\xd8...", "image/jpeg")).to(equal(1))


def test_count_pages__audio_is_one():
    # E6 · Caso 4: el extractor `asr` produce UNA LayoutPage por audio.
    expect(count_pages(b"OggS...", "audio/ogg")).to(equal(1))
    expect(count_pages(b"ID3...", "audio/mpeg")).to(equal(1))
    expect(count_pages(b"....ftyp", "audio/mp4")).to(equal(1))
    expect(count_pages(b"\xff\xf1", "audio/aac")).to(equal(1))
    expect(count_pages(b"RIFF....WAVE", "audio/wav")).to(equal(1))
    expect(count_pages(b"RIFF....WAVE", "audio/x-wav")).to(equal(1))
    expect(count_pages(b"fLaC", "audio/flac")).to(equal(1))


def test_count_pages__unknown_mime_is_none():
    # AMR no lo soporta Gemini ⇒ no está en AUDIO_MIMES ⇒ desconocido.
    expect(count_pages(b"#!AMR", "audio/amr")).to(be_none)
    expect(count_pages(b"random", "application/zip")).to(be_none)


def test_count_pages__corrupt_pdf_is_none():
    expect(count_pages(b"%PDF-not-really", "application/pdf")).to(be_none)
