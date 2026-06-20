from src.common.domain.enums.base_enum import BaseEnum


class JwtTokenScope(BaseEnum):
    ACCESS = "access"
    REFRESH = "refresh"
    PASSWORD_RESET = "password-reset"
