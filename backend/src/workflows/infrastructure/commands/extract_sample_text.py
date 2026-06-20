from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.common.application.commands.document_types import ExtractDocumentTypeSampleTextCommand
from src.common.application.logging import get_logger
from src.common.domain.buses.commands import CommandHandler
from src.common.infrastructure.event_publisher import EventPublisher
from src.storage.domain.repositories.file_repository import FileRepository
from src.workflows.application.document_types.sample_text_extractor import (
    ExtractDocumentTypeSampleText,
)
from src.workflows.domain.events.document_type_event import DocumentTypeEvent
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.services.document_text_extractor import DocumentTextExtractor

logger = get_logger(__name__)


@dataclass
class ExtractDocumentTypeSampleTextHandler(CommandHandler[ExtractDocumentTypeSampleTextCommand]):
    document_type_repository: DocumentTypeRepository
    file_repository: FileRepository
    text_extractor: DocumentTextExtractor
    event_publisher: EventPublisher | None = field(default=None)

    async def execute(self, command: ExtractDocumentTypeSampleTextCommand) -> None:
        await self._publish("SAMPLE_TEXT_EXTRACTING", command)
        try:
            await ExtractDocumentTypeSampleText(
                document_type_id=command.document_type_id,
                tenant_id=command.tenant_id,
                document_type_repository=self.document_type_repository,
                file_repository=self.file_repository,
                text_extractor=self.text_extractor,
            ).execute()
        except Exception as e:
            logger.error(
                "extract_sample_text_handler.failed",
                doctype_id=command.document_type_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            await self._publish("SAMPLE_TEXT_FAILED", command)
            raise
        await self._publish("SAMPLE_TEXT_EXTRACTED", command)

    async def _publish(self, event_type: str, command: ExtractDocumentTypeSampleTextCommand) -> None:
        if not self.event_publisher:
            logger.warning("extract_sample_text.no_publisher", event_type=event_type)
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
        logger.info("extract_sample_text.event_sent", event_type=event_type, doctype_id=command.document_type_id)
