import re
from typing import Any


def underscoreize(data: Any) -> Any:
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            new_key = re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()
            new_dict[new_key] = underscoreize(value)
        return new_dict
    if isinstance(data, list):
        return [underscoreize(item) for item in data]
    return data


def object_to_dict(obj: Any) -> dict[str, Any]:
    """
    Convert an object to a dictionary, excluding private attributes.
    """
    return {k: v for k, v in vars(obj).items() if not k.startswith("_")}


def camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def snake_to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def convert_keys_to_snake_case(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {camel_to_snake(k): convert_keys_to_snake_case(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_keys_to_snake_case(i) for i in obj]
    return obj
