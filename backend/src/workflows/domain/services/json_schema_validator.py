from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError

from src.common.domain.exceptions.processing import InvalidJsonSchemaError


def validate_document_type_json_schema(schema: dict) -> None:
    if not isinstance(schema, dict):
        raise InvalidJsonSchemaError("schema must be an object")

    if schema.get("type") != "object":
        raise InvalidJsonSchemaError("root type must be 'object'")

    try:
        Draft7Validator.check_schema(schema)
    except SchemaError as err:
        raise InvalidJsonSchemaError(err.message) from err

    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        raise InvalidJsonSchemaError("schema must define at least one field in 'properties'")
