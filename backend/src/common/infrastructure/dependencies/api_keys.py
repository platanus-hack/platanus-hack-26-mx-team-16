from fastapi import Security
from fastapi.security.api_key import APIKeyHeader

from src.common.domain.exceptions.common import InvalidAdminApiKeyError
from src.common.settings import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_admin_api_key(api_key: str = Security(api_key_header)):
    if api_key == settings.ADMIN_API_KEY:
        return api_key
    raise InvalidAdminApiKeyError
