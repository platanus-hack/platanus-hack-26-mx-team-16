from typing import Any


def sanitize_permissions(permissions_value: Any) -> list[str]:
    """
    Normalizes a value into a list of strings for permissions.

    If the input is a list, tuple, or set, it converts each item to a string.
    If the input is a single value, it wraps it in a list as a string.

    Args:
        permissions_value: The input value to normalize.

    Returns:
        A list of strings.
    """
    if isinstance(permissions_value, (list, tuple, set)):
        return [str(item) for item in permissions_value]

    if permissions_value is None:
        return []

    return [str(permissions_value)]
