"""Conteo barato de páginas para el gate de `mode=sync` (E1 · decisión D1).

`POST /v1/extract?mode=sync` solo espera inline si el archivo tiene ≤N páginas;
el conteo ocurre ANTES de despachar (sobre los bytes ya subidos). PDFs se
cuentan con pdfplumber; las imágenes y el audio (E6 · Caso 4: 1 audio = 1
"página" transcrita por ASR) son 1; cualquier otro caso devuelve ``None``
(desconocido ⇒ el caller degrada a 202, nunca error).
"""

from __future__ import annotations

from io import BytesIO

PDF_MAGIC = b"%PDF"
IMAGE_MIMES = {"image/jpeg", "image/jpg", "image/png"}
# E6 · Caso 4 — el extractor `asr` produce UNA LayoutPage por audio, así que el
# gate de páginas lo trata igual que una imagen (1).
AUDIO_MIMES = {
    "audio/ogg",
    "audio/mpeg",
    "audio/mp4",
    "audio/aac",
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
}


def count_pages(content: bytes, mime: str) -> int | None:
    if mime in IMAGE_MIMES or mime in AUDIO_MIMES:
        return 1
    if mime == "application/pdf" or content[:4] == PDF_MAGIC:
        try:
            import pdfplumber

            with pdfplumber.open(BytesIO(content)) as pdf:
                return len(pdf.pages)
        except Exception:  # noqa: BLE001 — PDF corrupto ⇒ desconocido, no error
            return None
    return None
