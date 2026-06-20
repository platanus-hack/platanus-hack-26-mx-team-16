from datetime import UTC, datetime
from typing import Any

from src.common.domain.entities.common.pagination import Page, Pagination
from src.common.infrastructure.responses.camel_case import CamelCaseJSONResponse


class ApiJSONResponse(CamelCaseJSONResponse):
    def render(self, content: Any) -> bytes:
        is_error_response = isinstance(content, dict) and "errors" in content

        if self.has_jsonable_content(content):
            timestamp = datetime.now(UTC).isoformat()
            if self.is_paginated(content):
                page: Page = content
                content = {
                    "data": page.items,
                    "pagination": Pagination.from_page(page),
                    "timestamp": timestamp,
                }
            else:
                content = {"data": content, "timestamp": timestamp}
        elif is_error_response:
            content["timestamp"] = datetime.now(UTC).isoformat()

        return super().render(content)

    @classmethod
    def is_paginated(cls, content: Any) -> bool:
        return isinstance(content, Page)

    @classmethod
    def has_jsonable_content(cls, content: Any) -> bool:
        is_error_response = isinstance(content, dict) and "errors" in content
        return (
            content is not None
            and not isinstance(content, str | bytes)
            and not is_error_response
            and not (isinstance(content, dict) and "data" in content and "timestamp" in content)
        )
