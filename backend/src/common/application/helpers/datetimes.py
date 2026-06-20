from datetime import UTC, date, datetime, time, timezone

import pytz

from src.common.domain.enums.locales import TimeZone


def utc_now() -> datetime:
    return datetime.now(pytz.utc)


def timezoned_now(time_zone: TimeZone = TimeZone.UTC) -> datetime:
    tz = pytz.timezone(time_zone.value)
    return datetime.now(tz)


def normalize_timezone(
    input_datetime: datetime,
    time_zone: TimeZone = TimeZone.UTC,
) -> datetime:
    if input_datetime.tzinfo is None:
        tz_value = pytz.timezone(time_zone.value)
        return input_datetime.replace(tzinfo=tz_value)
    return input_datetime


def localize_datetime(input_datetime: datetime, time_zone: str | None) -> datetime:
    local_timezone = pytz.timezone(time_zone)
    if input_datetime.tzinfo is None:
        return local_timezone.localize(input_datetime)
    return input_datetime.astimezone(local_timezone)


def optional_datetime_string(input_datetime: datetime | None) -> str | None:
    if input_datetime:
        return input_datetime.isoformat()
    return None


def combine_min_time(date_to: date) -> datetime:
    return datetime.combine(date_to, time(0, 0, 0, 0))


def combine_max_time(date_to: date) -> datetime:
    return datetime.combine(date_to, time(23, 59, 59, 999999))


def datetime_to_unix(dt: datetime, time_zone: timezone = UTC) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=time_zone)
    return int(dt.timestamp())


def unix_to_datetime(unix: int, time_zone: timezone = UTC) -> datetime:
    return datetime.fromtimestamp(unix, tz=time_zone)


def date_range_to_datimes(
    date_from: date,
    date_to: date,
    time_zone: timezone = UTC,
) -> tuple[datetime, datetime]:
    """
    Convierte un rango de fechas a datetimes con timezone.

    Bug reparado: replace() no modifica in-place, retorna un nuevo objeto.
    """
    datetime_from = combine_min_time(date_from)
    datetime_to = combine_max_time(date_to)

    # replace() retorna un nuevo objeto, no modifica in-place
    datetime_from = datetime_from.replace(tzinfo=time_zone)
    datetime_to = datetime_to.replace(tzinfo=time_zone)

    return datetime_from, datetime_to


def parse_filter_date_from(value: str | date | None) -> datetime | None:
    """Convert an ISO date string/date to UTC midnight (inclusive start of day)."""
    if value is None:
        return None
    d = date.fromisoformat(value) if isinstance(value, str) else value
    return combine_min_time(d).replace(tzinfo=UTC)


def parse_filter_date_to(value: str | date | None) -> datetime | None:
    """Convert an ISO date string/date to UTC end of day (23:59:59.999999, inclusive)."""
    if value is None:
        return None
    d = date.fromisoformat(value) if isinstance(value, str) else value
    return combine_max_time(d).replace(tzinfo=UTC)


def get_earliest_datetime(input_datetimes: list[datetime | None]) -> datetime:
    cleaned_datetimes = [input_datetime for input_datetime in input_datetimes if input_datetime is not None]
    if not cleaned_datetimes:
        raise ValueError("Need at least one datetime to compare.")
    return min(cleaned_datetimes)
