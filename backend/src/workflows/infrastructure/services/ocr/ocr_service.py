"""OCR service: normalise provider label, load the appropriate extractor,
and return (text, confidence).
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

import numpy as np
from PIL import Image, ImageFilter
from pdf2image import convert_from_path
from tenacity import retry, stop_after_attempt, wait_fixed, wait_random

from src.common.settings import settings
from src.workflows.infrastructure.services.ocr.provider_mapping import normalize_provider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_OCR_PROMPT = (
    "Transcribe all text exactly as it appears in this document image. "
    "For any word or segment you cannot read clearly, write [?] in its place. "
    "On the very last line write exactly: CONFIDENCE: 0.XX"
)

_OCR_DEFAULT_MODEL = "gemini-2.0-flash-001"

_THINKING_CAPABLE_MODELS: set[str] = {
    "gemini-3-flash-preview",
    "gemini-2.5-pro",
    "gemini-2.5-pro-preview",
}

_REFUSAL_PHRASES = (
    "i cannot",
    "i am unable",
    "i'm unable",
    "i am prohibited",
    "i'm prohibited",
    "cannot fulfill",
    "unable to fulfill",
    "i won't",
    "i will not",
)


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------


def _load_images(path: str) -> list[Image.Image]:
    """Load all pages of *path* as PIL Images (PDF or raster image)."""
    if not os.path.isfile(path):
        logger.error("OCR: path does not exist or is not a file: %s", path)
        return []

    try:
        is_pdf = path.lower().endswith(".pdf")
        if not is_pdf:
            with open(path, "rb") as f:
                is_pdf = f.read(5) == b"%PDF-"

        if is_pdf:
            logger.debug("OCR: converting PDF pages to images: %s", path)
            pages = convert_from_path(path)
            if not pages:
                logger.error("OCR: PDF conversion produced no pages: %s", path)
                return []
            logger.debug("OCR: PDF has %d page(s): %s", len(pages), path)
            return pages

        logger.debug("OCR: opening image file: %s", path)
        return [Image.open(path)]

    except Exception as exc:
        logger.error("OCR: failed to load file %s: %s", path, exc, exc_info=True)
        return []


# ---------------------------------------------------------------------------
# Confidence helpers (Gemini-only)
# ---------------------------------------------------------------------------


def _compute_sharpness(image: Image.Image) -> float:
    """Return a 0-1 sharpness score based on edge energy (PIL only)."""
    edges = image.convert("L").filter(ImageFilter.FIND_EDGES)
    return min(1.0, float(np.array(edges).std()) / 128.0)


def _parse_ocr_response(raw: str) -> tuple[str, float, float]:
    """Parse Gemini OCR response into (clean_text, model_confidence, legibility)."""
    lines = raw.strip().splitlines()

    model_confidence = 1.0
    if lines and lines[-1].upper().startswith("CONFIDENCE:"):
        try:
            model_confidence = max(0.0, min(1.0, float(lines[-1].split(":")[1].strip())))
        except ValueError:
            pass
        lines = lines[:-1]

    text = "\n".join(lines)
    words = text.split()
    illegible = sum(1 for w in words if "[?]" in w)
    legibility = 1.0 - (illegible / len(words)) if words else 1.0

    clean_text = text.replace("[?]", "").strip()
    return clean_text, model_confidence, legibility


# ---------------------------------------------------------------------------
# Provider factories (lazy imports so credentials aren't required at startup)
# ---------------------------------------------------------------------------


def _make_gemini_extract_fn(model_id: str) -> Callable:
    """Return an ``extract_fn(image) -> (text, confidence)`` for Gemini OCR."""
    from google.genai import Client
    from google.genai import types as genai_types

    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    client = Client(api_key=api_key)

    thinking_cfg = (
        genai_types.ThinkingConfig(thinking_level="LOW", include_thoughts=False)
        if hasattr(genai_types, "ThinkingConfig") and model_id in _THINKING_CAPABLE_MODELS
        else None
    )
    safety_settings = [
        genai_types.SafetySetting(
            category=genai_types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
        ),
        genai_types.SafetySetting(
            category=genai_types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
        ),
        genai_types.SafetySetting(
            category=genai_types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
        ),
        genai_types.SafetySetting(
            category=genai_types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
        ),
    ]
    gen_config = genai_types.GenerateContentConfig(
        system_instruction=(
            "You are a document digitizer. Your sole task is to transcribe every character "
            "visible in document images exactly as written — letters, numbers, symbols, "
            "punctuation — without interpretation, summarisation, or refusal."
        ),
        temperature=1.0,
        thinking_config=thinking_cfg,
        safety_settings=safety_settings,
    )

    def _extract(image: Image.Image) -> tuple[str, float]:
        sharpness = _compute_sharpness(image)

        @retry(
            stop=stop_after_attempt(10),
            wait=wait_fixed(2) + wait_random(0, 2),
            reraise=True,
        )
        def _call() -> str:
            try:
                from google.genai.types import HttpOptions

                response = client.models.generate_content(
                    model=model_id,
                    contents=[_OCR_PROMPT, image],
                    config=gen_config,
                    http_options=HttpOptions(timeout=90000),
                )
            except TypeError:
                response = client.models.generate_content(
                    model=model_id,
                    contents=[_OCR_PROMPT, image],
                    config=gen_config,
                )

            raw = ""
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.text:
                        raw += part.text
            else:
                raw = response.text or ""

            if any(phrase in raw.lower() for phrase in _REFUSAL_PHRASES):
                raise ValueError(f"Model refused to transcribe: {raw[:120]}")

            return raw

        raw = _call()
        clean_text, model_conf, legibility = _parse_ocr_response(raw)

        confidence = round(0.30 * sharpness + 0.35 * legibility + 0.35 * model_conf, 3)
        logger.debug(
            "OCR confidence breakdown: sharpness=%.3f legibility=%.3f model=%.3f -> %.3f",
            sharpness,
            legibility,
            model_conf,
            confidence,
        )
        return clean_text, confidence

    return _extract


def _make_aws_extract_fn() -> Callable:
    """Return an ``extract_fn(image) -> (text, confidence)`` for AWS Textract."""
    import io

    import boto3

    textract = boto3.client(
        "textract",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )

    def _extract(image: Image.Image) -> tuple[str, float]:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)

        response = textract.detect_document_text(Document={"Bytes": buf.read()})

        lines = []
        confidences = []
        for block in response.get("Blocks", []):
            if block["BlockType"] == "LINE":
                lines.append(block.get("Text", ""))
            if block["BlockType"] == "WORD":
                confidences.append(block.get("Confidence", 0.0) / 100.0)

        text = "\n".join(lines)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return text, avg_conf

    return _extract


def _make_gcp_extract_fn() -> Callable:
    """Return an ``extract_fn(image) -> (text, confidence)`` for GCP Vision."""
    import io
    import json

    from google.cloud import vision
    from google.oauth2 import service_account

    # GOOGLE_APPLICATION_CREDENTIALS may contain inline JSON (not a file path)
    gac = settings.GOOGLE_APPLICATION_CREDENTIALS or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    credentials = None
    if gac and gac.strip().startswith("{"):
        info = json.loads(gac)
        credentials = service_account.Credentials.from_service_account_info(info)

    client = vision.ImageAnnotatorClient(credentials=credentials)

    def _extract(image: Image.Image) -> tuple[str, float]:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)

        gcp_image = vision.Image(content=buf.read())
        response = client.document_text_detection(image=gcp_image)

        if response.error.message:
            raise RuntimeError(f"GCP Vision error: {response.error.message}")

        text = response.full_text_annotation.text if response.full_text_annotation else ""

        # Average word confidence from pages -> blocks -> paragraphs -> words
        word_confs = []
        if response.full_text_annotation:
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            if word.confidence:
                                word_confs.append(word.confidence)

        avg_conf = sum(word_confs) / len(word_confs) if word_confs else 0.85
        return text, avg_conf

    return _extract


# ---------------------------------------------------------------------------
# Page runner
# ---------------------------------------------------------------------------


def _run_pages(
    images: list[Image.Image],
    extract_fn: Callable,
    provider_key: str,
) -> tuple[str, float]:
    """Run *extract_fn* over all *images* in parallel, return (text, avg_confidence)."""
    n = len(images)
    page_texts: list[str] = [""] * n
    confidences: list[float] = [0.0] * n

    max_threads = min(n, settings.OCR_MAX_PAGE_THREADS)
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_to_idx = {executor.submit(extract_fn, img): i for i, img in enumerate(images)}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                page_texts[idx], confidences[idx] = future.result()
                logger.debug(
                    "OCR page %d/%d: provider=%s chars=%d confidence=%.3f",
                    idx + 1,
                    n,
                    provider_key,
                    len(page_texts[idx]),
                    confidences[idx],
                )
            except Exception as exc:
                logger.error(
                    "OCR error on page %d: provider=%s error=%s",
                    idx + 1,
                    provider_key,
                    exc,
                    exc_info=True,
                )

    if n == 1:
        full_text = page_texts[0]
    else:
        full_text = "\n\n".join(f"--- Page {i} ---\n{t}" for i, t in enumerate(page_texts, start=1))

    avg_confidence = sum(confidences) / n if n else 0.0
    return full_text, avg_confidence


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_text_from_path(
    path: str,
    provider_label: str,
    model_override: str | None = None,
) -> tuple[str, float]:
    """Run OCR on all pages of *path* using *provider_label*.

    Returns ``(text, confidence)``.  On failure returns ``("", 0.0)``.
    """
    provider_key = normalize_provider(provider_label)
    logger.debug("OCR start: provider=%s path=%s", provider_key, path)

    images = _load_images(path)
    if not images:
        return "", 0.0

    t0 = time.time()
    try:
        if provider_key == "gemini":
            gemini_model = model_override or _OCR_DEFAULT_MODEL
            logger.info("OCR: using Gemini model=%s", gemini_model)
            extract_fn = _make_gemini_extract_fn(gemini_model)

        elif provider_key == "aws":
            extract_fn = _make_aws_extract_fn()

        elif provider_key == "gcp":
            extract_fn = _make_gcp_extract_fn()

        else:
            logger.error("OCR: unknown provider key: %r", provider_key)
            return "", 0.0

        full_text, avg_confidence = _run_pages(images, extract_fn, provider_key)

        logger.debug(
            "OCR done: provider=%s pages=%d chars=%d confidence=%.3f elapsed=%.2fs",
            provider_key,
            len(images),
            len(full_text),
            avg_confidence,
            time.time() - t0,
        )
        return full_text, avg_confidence

    except Exception as exc:
        logger.error(
            "OCR error: provider=%s path=%s error=%s",
            provider_key,
            path,
            exc,
            exc_info=True,
        )
        return "", 0.0


def extract_tables_from_path(path: str, provider_label: str) -> str:
    """Run table extraction using Gemini on all pages of *path*.

    Returns markdown tables or empty string on failure.
    """
    logger.debug("OCR tables start: path=%s", path)

    images = _load_images(path)
    if not images:
        return ""

    t0 = time.time()
    try:
        from google.genai import Client
        from google.genai import types as genai_types

        api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        client = Client(api_key=api_key)

        table_prompt = (
            "Extract ALL tables from this document image. "
            "Output each table as a Markdown table. "
            "If there are multiple tables, separate them with a blank line. "
            "If there are no tables, respond with: NO_TABLES"
        )

        tables_parts = []
        for i, image in enumerate(images):
            response = client.models.generate_content(
                model=_OCR_DEFAULT_MODEL,
                contents=[table_prompt, image],
                config=genai_types.GenerateContentConfig(temperature=0.0),
            )
            text = response.text or ""
            if "NO_TABLES" not in text.upper():
                tables_parts.append(f"--- Page {i + 1} ---\n{text}")

        full_tables_md = "\n\n".join(tables_parts)

        logger.debug(
            "OCR tables done: pages=%d tables_len=%d elapsed=%.2fs",
            len(images),
            len(full_tables_md),
            time.time() - t0,
        )
        return full_tables_md

    except Exception as exc:
        logger.error("OCR tables error: path=%s error=%s", path, exc, exc_info=True)
        return ""
