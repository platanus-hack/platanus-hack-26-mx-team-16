"""Download files from S3 to temporary local paths for OCR processing."""

import logging
import tempfile
from pathlib import Path

from src.common.settings import settings
from src.storage.infrastructure.s3_client import get_s3_client

logger = logging.getLogger(__name__)


def download_file_to_temp(s3_key: str, file_name: str) -> Path:
    """Download an S3 object to a named temp file.

    The caller is responsible for deleting the temp file after use.
    """
    suffix = Path(file_name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        s3 = get_s3_client()
        s3.download_fileobj(settings.AWS_STORAGE_BUCKET_NAME, s3_key, tmp)
        tmp.close()
        logger.debug("Downloaded s3://%s/%s -> %s", settings.AWS_STORAGE_BUCKET_NAME, s3_key, tmp.name)
        return Path(tmp.name)
    except Exception:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        raise
