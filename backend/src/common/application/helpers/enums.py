from src.common.domain.enums.base_enum import BaseEnum


def get_enum_string(enum_value: BaseEnum | None = None) -> str | None:
    if enum_value:
        return str(enum_value)
    return None
