"""LLM-backed FieldSuggester — genera un JSON Schema Draft-7 desde texto extraído."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from textwrap import dedent
from typing import Any

import jsonschema
from tenacity import RetryCallState, RetryError, retry, retry_if_exception_type, stop_after_attempt

from src.common.application.logging import get_logger
from src.workflows.domain.services.field_suggester import FieldSuggester
from src.workflows.infrastructure.agents.builder import AgentEffort, AgentProvider
from src.workflows.infrastructure.services.single_agent_service import SingleAgentService

logger = get_logger()


def _log_retry(state: RetryCallState) -> None:
    logger.warning(
        "field_suggester.retrying",
        attempt=state.attempt_number,
        error=str(state.outcome.exception()),
    )


_MAX_TEXT_CHARS: int = 6_000

_FALLBACK_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft-07/schema",
    "type": "object",
    "properties": {},
    "additionalProperties": True,
}

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["type", "properties"],
    "properties": {
        "$schema": {"type": "string"},
        "type": {"type": "string", "enum": ["object"]},
        "title": {"type": "string"},
        "properties": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["type"],
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["string", "number", "integer", "boolean", "array", "object"],
                        "description": (
                            "Prefer flat scalar types. Use 'object' only for a clearly bounded "
                            "sub-structure. Use 'array' for repeating values or structured groups."
                        ),
                    },
                    "description": {"type": "string"},
                    "format": {
                        "type": "string",
                        "description": "date, date-time, email, phone, uri — when applicable.",
                    },
                    "enum": {"type": "array", "items": {"type": "string"}},
                    "items": {
                        "type": "object",
                        "description": "Schema for array items. Use type=object with properties for structured rows.",
                    },
                    "properties": {
                        "type": "object",
                        "description": "Only present when type=object and nesting is warranted.",
                    },
                    "x-keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "2–5 lowercase domain terms that identify the field semantically.",
                    },
                    "examples": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "1–3 literal sample values taken verbatim from the document text.",
                    },
                },
            },
        },
        "required": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Fields present in every instance of this document type.",
        },
    },
}

_SYSTEM_PROMPT = dedent("""
    You are a JSON Schema builder. Given extracted text from a document,
    identify the most relevant and general fields that characterise documents
    of this type and produce a JSON Schema (Draft-07, type=object).

    Focus on fields that:
    - Appear consistently across instances of this document type.
    - Carry meaningful business or domain value (identifiers, dates, amounts,
      statuses, key descriptors). Skip decorative text, headers and layout noise.
    - If user guidance is provided, prioritise those fields and adopt the suggested names.

    Type rules (apply in order):
    string · number · integer · boolean
    array of strings  — repeating simple values (tags, codes)
    array of objects  — repeating structured rows (line-items, table rows)
    object            — single bounded sub-structure (address block); never just to group fields

    Add format when clearly applicable: date, date-time, email, phone, uri.

    Per-field extras (omit when not useful):
    - x-keywords: 2–5 lowercase domain terms beyond the field name itself.
    - examples: 1–3 literal values copied verbatim from the text; never invented.

    Naming: snake_case identifiers, not display labels.
    Output only the JSON object — no prose, no Markdown fencing.
""").strip()


def _composed_system_prompt() -> str:
    schema_str = json.dumps(_OUTPUT_SCHEMA, ensure_ascii=False)
    suffix = dedent(f"""
        You MUST respond with a single JSON object that conforms exactly to
        the JSON Schema below. No prose, no Markdown fencing — only the JSON object.

        JSON Schema:
        {schema_str}
    """).strip()
    return f"{_SYSTEM_PROMPT}\n\n{suffix}"


@dataclass
class LLMFieldSuggester(FieldSuggester):
    agent_service: SingleAgentService

    @classmethod
    def create(
        cls,
        provider: AgentProvider = AgentProvider.OPENAI,
        effort: AgentEffort = AgentEffort.LITE,
    ) -> "LLMFieldSuggester":
        service = SingleAgentService.from_builder(
            system_prompt=_composed_system_prompt(),
            provider=provider,
            effort=effort,
        )
        return cls(agent_service=service)

    async def suggest(
        self,
        extracted_text: str,
        doctype_name: str,
        prompt: str | None,
    ) -> dict:
        try:
            generated_fields = await self._generate_fields_schema(
                self._build_user_message(extracted_text, doctype_name, prompt))
            return self._to_json_schema(payload=generated_fields, doctype_name=doctype_name)
        except RetryError:
            logger.error("field_suggester.all_attempts_failed", doctype=doctype_name)
            return {**_FALLBACK_SCHEMA, "title": doctype_name}

    @retry(
        retry=retry_if_exception_type((jsonschema.ValidationError, ValueError)),
        stop=stop_after_attempt(3),
        before_sleep=_log_retry,
    )
    async def _generate_fields_schema(self, user_message: str) -> dict:
        result = await self.agent_service.arun_json(user_message)
        jsonschema.validate(result, _OUTPUT_SCHEMA)
        return result

    @staticmethod
    def _to_json_schema(payload: dict, doctype_name: str) -> dict:
        result: dict = {
            "$schema": "https://json-schema.org/draft-07/schema",
            "type": "object",
            "title": payload.get("title") or doctype_name,
            "properties": payload["properties"],
        }
        if required := payload.get("required"):
            result["required"] = required
        return result

    @staticmethod
    def _build_user_message(extracted_text: str, doctype_name: str, prompt: str | None) -> str:
        parts = [f"Document type: {doctype_name}"]
        if prompt:
            parts.append(f"User guidance: {prompt}")
        parts.append(f"Extracted text:\n{LLMFieldSuggester._clean_text(extracted_text)}")
        return "\n\n".join(parts)

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()[:_MAX_TEXT_CHARS]
