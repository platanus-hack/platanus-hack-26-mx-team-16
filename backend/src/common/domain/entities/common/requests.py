from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class CamelCaseRequest(BaseModel):
    """
    Base model for API requests that automatically converts camelCase fields to snake_case.

    This model accepts input in camelCase format and converts it to snake_case
    for internal processing. All request models should inherit from this class.

    Example:
        Input JSON: {"firstName": "John", "lastName": "Doe"}
        Model fields: first_name="John", last_name="Doe"
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        from_attributes=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    @model_validator(mode="before")
    @classmethod
    def convert_camel_to_snake(cls, data: Any) -> Any:
        """
        Pre-validation hook to ensure all dictionary keys are converted to snake_case.
        This handles nested dictionaries and lists.
        """
        if isinstance(data, dict):
            return cls._convert_keys_to_snake(data)
        return data

    @classmethod
    def _convert_keys_to_snake(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively convert all dictionary keys from camelCase to snake_case.
        """

        def camel_to_snake(name: str) -> str:
            result = []
            for i, char in enumerate(name):
                if char.isupper():
                    if i > 0 and (name[i - 1].islower() or (i < len(name) - 1 and name[i + 1].islower())):
                        result.append("_")
                    result.append(char.lower())
                else:
                    result.append(char)
            return "".join(result)

        converted: dict[str, Any] = {}
        for key, value in data.items():
            snake_key = camel_to_snake(key)

            # Recursively convert nested structures
            if isinstance(value, dict):
                converted[snake_key] = cls._convert_keys_to_snake(value)
            elif isinstance(value, list):
                converted[snake_key] = [
                    cls._convert_keys_to_snake(item) if isinstance(item, dict) else item for item in value
                ]
            else:
                converted[snake_key] = value

        return converted
