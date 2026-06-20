from functools import lru_cache

from cryptography.fernet import Fernet

from src.common.settings import settings


@lru_cache
def get_fernet() -> Fernet:
    return Fernet(settings.SECRET_KEY)
