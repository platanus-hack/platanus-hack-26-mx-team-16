import base64
from datetime import datetime
from uuid import UUID

from src.common.application.helpers.encryption import get_fernet
from src.common.domain.exceptions.common import InvalidPaginationCursorError

SEPARATOR = "|"
fernet = get_fernet()


def _serialize(input_datetime: datetime, uuid: UUID) -> bytes:
    return f"{input_datetime.isoformat(timespec='microseconds')}{SEPARATOR}{uuid}".encode()


def _deserialize(raw: bytes) -> tuple[datetime, UUID]:
    timestamp_str, uuid_str = raw.decode().split(SEPARATOR)
    return datetime.fromisoformat(timestamp_str), UUID(uuid_str)


def encode_cursor(input_datetime: datetime, uuid: UUID) -> str:
    token = fernet.encrypt(_serialize(input_datetime, uuid))
    return base64.urlsafe_b64encode(token).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        token = base64.urlsafe_b64decode(padded)
        raw = fernet.decrypt(token)
        return _deserialize(raw)
    except Exception:
        raise InvalidPaginationCursorError
