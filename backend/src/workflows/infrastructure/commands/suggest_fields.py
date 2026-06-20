from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.common.application.commands.document_types import SuggestDocumentTypeFieldsCommand
from src.common.domain.buses.commands import CommandHandler
from src.common.infrastructure.event_publisher import EventPublisher
from src.workflows.application.document_types.field_suggester import SuggestDocumentTypeFields
from src.workflows.domain.events.document_type_event import DocumentTypeEvent
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.infrastructure.services.doctype.field_suggester import LLMFieldSuggester


@dataclass
class SuggestDocumentTypeFieldsHandler(CommandHandler[SuggestDocumentTypeFieldsCommand]):
    document_type_repository: DocumentTypeRepository
    event_publisher: EventPublisher | None = field(default=None)

    async def execute(self, command: SuggestDocumentTypeFieldsCommand) -> None:
        await self._publish("FIELDS_SUGGESTING", command)
        try:
            await SuggestDocumentTypeFields(
                document_type_id=command.document_type_id,
                tenant_id=command.tenant_id,
                prompt=command.prompt,
                document_type_repository=self.document_type_repository,
                field_suggester=LLMFieldSuggester.create(),
            ).execute()
        except Exception:
            await self._publish("FIELDS_SUGGESTION_FAILED", command)
            raise
        await self._publish("FIELDS_SUGGESTED", command)

    async def _publish(self, event_type: str, command: SuggestDocumentTypeFieldsCommand) -> None:
        if not self.event_publisher:
            return
        await self.event_publisher.publish(
            DocumentTypeEvent(
                seq=0,
                ts=datetime.now(timezone.utc),
                type=event_type,  # type: ignore[arg-type]
                document_type_id=command.document_type_id,
                payload={},
            )
        )
