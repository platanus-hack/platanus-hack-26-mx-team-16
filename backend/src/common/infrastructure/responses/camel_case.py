import json
from typing import Any

from fastapi.responses import JSONResponse as FastAPIJSONResponse

from src.common.application.helpers.json_encoder import convert_to_camel_case


class CamelCaseJSONResponse(FastAPIJSONResponse):
    """JSON response that converts all dict keys to camelCase before sending.

    Snake_case keys produced by presenters are normalized to camelCase by
    ``convert_to_camel_case``, which also flattens BaseModels, UUIDs,
    datetimes and other non-JSON types in a single pass. Wrap a value in
    ``RawJson`` to opt it out of the key transform (used for JSONB blobs
    whose keys are domain data).
    """

    def render(self, content: Any) -> bytes:
        return json.dumps(convert_to_camel_case(content)).encode("utf-8")
