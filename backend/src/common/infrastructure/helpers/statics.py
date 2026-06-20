from src.common.settings import settings


def get_static_path(path: str) -> str:
    return f"{settings.AWS_CLOUDFRONT_DOMAIN}/{path}"
