"""Renders user-authored templates by substituting `{{token}}` placeholders.

There is exactly one renderer for the project: rule-prompt evaluators and
`synthesis_runner` both consume `TokenPromptRenderer` so the registry of
allowed tokens stays the source of truth. `assert_valid` is the contract
called when saving a template (rule prompt, synthesis_template) — it raises
`UnknownTokenError` listing typos or tokens that haven't been registered.

`@DOC_TYPE.field` placeholders that synthesis templates may carry are NOT
substituted here: they depend on the per-run document set, so the
synthesis_runner resolves them before handing the text to this renderer.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.common.domain.exceptions._base import DomainError
from src.workflows.domain.services import token_registry, token_resolver
from src.workflows.domain.services.token_resolver import TokenContext


@dataclass
class RenderedPrompt:
    text: str
    unresolved_tokens: list[str] = field(default_factory=list)


class PromptRenderError(DomainError):
    pass


class UnknownTokenError(PromptRenderError):
    def __init__(self, tokens: list[str]):
        super().__init__(
            code="processing.UnknownTemplateToken",
            message=f"Template references unknown tokens: {tokens}",
            status_code=400,
            context={"tokens": tokens},
        )


class RendererNotConfiguredError(PromptRenderError):
    def __init__(self) -> None:
        super().__init__(
            code="processing.RendererNotConfigured",
            message="TokenPromptRenderer.render() requires a TokenContext",
            status_code=500,
        )


_TOKEN_SUBSTITUTION_RE = re.compile(r"\{\{\s*(?P<name>[A-Za-z_][\w.]*)\s*\}\}")


class PromptRenderer(ABC):
    @abstractmethod
    def assert_valid(self, template: str) -> None:
        """Raise `UnknownTokenError` if `template` references unregistered tokens."""

    @abstractmethod
    async def render(self, template: str) -> RenderedPrompt:
        """Resolve every `{{token}}` against the bound context and return the text."""


@dataclass
class TokenPromptRenderer(PromptRenderer):
    """Resolves `{{token}}` placeholders against the project token registry.

    Each instance is bound to one `TokenContext` (one render per run/case).
    Save-time validation runs without a context via `assert_valid`.
    """

    ctx: TokenContext | None = None

    def assert_valid(self, template: str) -> None:
        tokens = token_registry.parse_tokens(template)
        unknown = [t for t in tokens if not token_registry.is_known(t)]
        if unknown:
            raise UnknownTokenError(unknown)

    async def render(self, template: str) -> RenderedPrompt:
        if self.ctx is None:
            raise RendererNotConfiguredError
        self.assert_valid(template)
        tokens = token_registry.parse_tokens(template)
        resolved = token_resolver.resolve_all(tokens, self.ctx)
        text = _TOKEN_SUBSTITUTION_RE.sub(
            lambda m: token_resolver.to_prompt_value(resolved[m.group("name")]),
            template,
        )
        return RenderedPrompt(text=text, unresolved_tokens=[])
