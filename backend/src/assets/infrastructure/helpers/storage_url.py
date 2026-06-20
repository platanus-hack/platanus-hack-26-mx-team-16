from src.common.settings import settings


def build_storage_url(object_key: str) -> str:
    base = settings.AWS_S3_PUBLIC_URL
    if base:
        return f"{base.rstrip('/')}/{object_key}"
    return object_key
