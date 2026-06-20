"""OpenAPI 3.1.0 dataclass model.

A flat, mutation-friendly representation that round-trips to JSON.
Every dataclass has a ``to_dict()`` method that drops ``None``
fields and converts the tree to a plain dict suitable for
``json.dump``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


@dataclass
class Reference:
    ref: str

    def to_dict(self) -> dict[str, Any]:
        return {"$ref": self.ref}


@dataclass
class Schema:
    type: str | None = None
    format: str | None = None
    description: str | None = None
    enum: list[Any] | None = None
    default: Any | None = None
    items: "Schema | Reference | None" = None
    properties: dict[str, "Schema | Reference"] | None = None
    required: list[str] | None = None
    additionalProperties: "bool | Schema | Reference | None" = None
    anyOf: list["Schema | Reference"] | None = None
    oneOf: list["Schema | Reference"] | None = None
    nullable: bool | None = None
    example: Any | None = None
    # extensions
    x_snake_name: str | None = None
    x_unresolved: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        d["type"] = self.type
        if self.format is not None:
            d["format"] = self.format
        if self.description is not None:
            d["description"] = self.description
        if self.enum is not None:
            d["enum"] = self.enum
        if self.default is not None:
            d["default"] = self.default
        if self.items is not None:
            d["items"] = self.items.to_dict() if hasattr(self.items, "to_dict") else self.items
        if self.properties is not None:
            d["properties"] = {k: v.to_dict() for k, v in self.properties.items()}
        if self.required is not None:
            d["required"] = self.required
        if self.additionalProperties is not None:
            d["additionalProperties"] = (
                self.additionalProperties.to_dict()
                if hasattr(self.additionalProperties, "to_dict")
                else self.additionalProperties
            )
        if self.anyOf is not None:
            d["anyOf"] = [x.to_dict() for x in self.anyOf]
        if self.oneOf is not None:
            d["oneOf"] = [x.to_dict() for x in self.oneOf]
        if self.nullable is not None:
            d["nullable"] = self.nullable
        if self.example is not None:
            d["example"] = self.example
        if self.x_snake_name is not None:
            d["x-snake-name"] = self.x_snake_name
        if self.x_unresolved is not None:
            d["x-unresolved"] = self.x_unresolved
        return _drop_none(d)


@dataclass
class MediaType:
    schema: Schema | Reference | None = None
    example: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.schema is not None:
            d["schema"] = self.schema.to_dict()
        if self.example is not None:
            d["example"] = self.example
        return d


@dataclass
class RequestBody:
    description: str | None = None
    content: dict[str, MediaType] = field(default_factory=dict)
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _drop_none(
            {
                "description": self.description,
                "content": {k: v.to_dict() for k, v in self.content.items()},
                "required": self.required,
            }
        )


@dataclass
class Response:
    description: str = "OK"
    content: dict[str, MediaType] = field(default_factory=dict)
    headers: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"description": self.description}
        if self.content:
            d["content"] = {k: v.to_dict() for k, v in self.content.items()}
        if self.headers:
            d["headers"] = self.headers
        return d


@dataclass
class Parameter:
    name: str
    in_: str  # "path" | "query" | "header" | "cookie"
    description: str | None = None
    required: bool = False
    schema: Schema | Reference | None = None
    example: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"name": self.name, "in": self.in_}
        if self.description is not None:
            d["description"] = self.description
        if self.required:
            d["required"] = True
        if self.schema is not None:
            d["schema"] = self.schema.to_dict()
        if self.example is not None:
            d["example"] = self.example
        return d


@dataclass
class Operation:
    tags: list[str] = field(default_factory=list)
    summary: str | None = None
    description: str | None = None
    operationId: str | None = None
    parameters: list[Parameter] = field(default_factory=list)
    requestBody: RequestBody | None = None
    responses: dict[str, Response] = field(default_factory=dict)
    security: list[dict[str, list[str]]] | None = None
    deprecated: bool = False

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.tags:
            d["tags"] = self.tags
        if self.summary is not None:
            d["summary"] = self.summary
        if self.description is not None:
            d["description"] = self.description
        if self.operationId is not None:
            d["operationId"] = self.operationId
        if self.parameters:
            d["parameters"] = [p.to_dict() for p in self.parameters]
        if self.requestBody is not None:
            d["requestBody"] = self.requestBody.to_dict()
        d["responses"] = {k: v.to_dict() for k, v in self.responses.items()}
        if self.security is not None:
            d["security"] = self.security
        if self.deprecated:
            d["deprecated"] = True
        return d


@dataclass
class PathItem:
    ref: str | None = None
    summary: str | None = None
    description: str | None = None
    get: Operation | None = None
    post: Operation | None = None
    put: Operation | None = None
    patch: Operation | None = None
    delete: Operation | None = None
    head: Operation | None = None
    options: Operation | None = None
    parameters: list[Parameter] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.ref is not None:
            d["$ref"] = self.ref
        if self.summary is not None:
            d["summary"] = self.summary
        if self.description is not None:
            d["description"] = self.description
        for verb, op in (
            ("get", self.get),
            ("post", self.post),
            ("put", self.put),
            ("patch", self.patch),
            ("delete", self.delete),
            ("head", self.head),
            ("options", self.options),
        ):
            if op is not None:
                d[verb] = op.to_dict()
        if self.parameters:
            d["parameters"] = [p.to_dict() for p in self.parameters]
        return d


@dataclass
class Server:
    url: str
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _drop_none({"url": self.url, "description": self.description})


@dataclass
class Tag:
    name: str
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _drop_none({"name": self.name, "description": self.description})


@dataclass
class SecurityScheme:
    type: str
    description: str | None = None
    name: str | None = None  # for apiKey
    in_: str | None = None  # for apiKey
    scheme: str | None = None  # for http
    bearerFormat: str | None = None  # for http bearer
    flows: dict[str, Any] | None = None  # for oauth2

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"type": self.type}
        if self.description is not None:
            d["description"] = self.description
        if self.name is not None:
            d["name"] = self.name
        if self.in_ is not None:
            d["in"] = self.in_
        if self.scheme is not None:
            d["scheme"] = self.scheme
        if self.bearerFormat is not None:
            d["bearerFormat"] = self.bearerFormat
        if self.flows is not None:
            d["flows"] = self.flows
        return d


@dataclass
class Components:
    schemas: dict[str, Schema | Reference] = field(default_factory=dict)
    securitySchemes: dict[str, SecurityScheme] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.schemas:
            d["schemas"] = {k: v.to_dict() for k, v in self.schemas.items()}
        if self.securitySchemes:
            d["securitySchemes"] = {k: v.to_dict() for k, v in self.securitySchemes.items()}
        return d


@dataclass
class Info:
    title: str
    version: str
    description: str | None = None
    contact: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"title": self.title, "version": self.version}
        if self.description is not None:
            d["description"] = self.description
        if self.contact is not None:
            d["contact"] = self.contact
        return d


@dataclass
class OpenAPI:
    openapi: str = "3.1.0"
    info: Info = field(default_factory=lambda: Info(title="API", version="0.0.0"))
    servers: list[Server] = field(default_factory=list)
    tags: list[Tag] = field(default_factory=list)
    paths: dict[str, PathItem] = field(default_factory=dict)
    components: Components = field(default_factory=Components)
    security: list[dict[str, list[str]]] | None = None
    # Extensions
    x_unresolved_types: list[str] | None = None
    x_unresolved_generics: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "openapi": self.openapi,
            "info": self.info.to_dict(),
        }
        if self.servers:
            d["servers"] = [s.to_dict() for s in self.servers]
        if self.tags:
            d["tags"] = [t.to_dict() for t in self.tags]
        d["paths"] = {k: v.to_dict() for k, v in self.paths.items()}
        if self.components.schemas or self.components.securitySchemes:
            d["components"] = self.components.to_dict()
        if self.security is not None:
            d["security"] = self.security
        if self.x_unresolved_types is not None:
            d["x-unresolved-types"] = self.x_unresolved_types
        if self.x_unresolved_generics is not None:
            d["x-unresolved-generics"] = self.x_unresolved_generics
        return d
