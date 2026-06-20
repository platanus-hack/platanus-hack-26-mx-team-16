"""Provider label -> internal key mapping.

UI labels (e.g. "Model 1") are mapped to the provider keys
accepted by the OCR service.
"""

PROVIDER_MAP: dict[str, str] = {
    # New UI labels (canonical)
    "Model 1": "gcp",
    "Model 2": "aws",
    "Model 3": "gemini",
    # Legacy UI labels (kept for backward compatibility)
    "Google Vision": "gcp",
    "AWS Textract": "aws",
    "Azure OCR": "gemini",
    "Tesseract (local)": "gemini",
    # Raw internal keys (pass-through)
    "gcp": "gcp",
    "aws": "aws",
    "gemini": "gemini",
}


def normalize_provider(label: str) -> str:
    """Return the internal provider key for a given UI label or raw key."""
    return PROVIDER_MAP.get(label, "gemini")
