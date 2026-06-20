from src.common.domain.enums.base_enum import BaseEnum


class DocumentExtractorType(BaseEnum):
    """Extractores soportados por la Lambda vnext-tools-extract_text.

    Mantener en sync con ``ExtractorType`` del repo vnext-tools — la fase
    ``extract_text`` pasa el valor crudo y ``POST /v1/pipelines`` lo valida
    contra este enum al publicar una receta (E3).
    """

    TEXTRACT = "textract"
    TEXTRACT_LAYOUT = "textract_layout"
    DOCUMENTAI = "documentai"
    DOCUMENTAI_LAYOUT = "documentai_layout"
    TEXTRACTOR = "textractor"
    TEXTRACTOR_LAYOUT = "textractor_layout"
    MISTRAL_OCR = "mistral_ocr"
    # E3 · Caso 1A: Gemini Vision para manuscritos (receta médica). Texto por
    # página sin geometría — el anclaje bbox degrada, la extracción funciona.
    VLM = "vlm"
    # E6 · Caso 4: Gemini ASR para notas de voz (canal WhatsApp). Espejo de VLM
    # (texto por página sin geometría). ``AUTO`` deja que la Lambda despache por
    # tipo de archivo: pdf/imagen → OCR, audio → ASR (recetas multicanal).
    ASR = "asr"
    AUTO = "auto"
