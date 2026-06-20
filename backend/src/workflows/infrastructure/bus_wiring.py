from src.common.application.commands.document_types import (
    ExtractDocumentTypeSampleTextCommand,
    SuggestDocumentTypeFieldsCommand,
)
from src.common.domain.contexts.bus import BusContext
from src.common.domain.contexts.domain import DomainContext
from src.common.infrastructure.event_publisher import EventPublisher
from src.common.settings import settings
from src.workflows.domain.services.document_text_extractor import DocumentTextExtractor
from src.workflows.infrastructure.commands.extract_sample_text import ExtractDocumentTypeSampleTextHandler
from src.workflows.infrastructure.commands.suggest_fields import SuggestDocumentTypeFieldsHandler
from src.workflows.infrastructure.services.lambda_sample_text_extractor import LambdaSampleTextExtractor
from src.workflows.infrastructure.services.local_sample_text_extractor import LocalSampleTextExtractor


def _build_text_extractor(domain: DomainContext) -> DocumentTextExtractor:
    if settings.EXTRACTION_LAMBDA_ENABLED:
        return LambdaSampleTextExtractor()
    return LocalSampleTextExtractor(storage_service=domain.storage_service)


def workflows_wiring(
    domain: DomainContext,
    bus: BusContext,
    event_publisher: EventPublisher | None = None,
) -> None:
    bus.command_bus.subscribe(
        command=ExtractDocumentTypeSampleTextCommand,
        handler=ExtractDocumentTypeSampleTextHandler(
            document_type_repository=domain.document_type_repository,
            file_repository=domain.file_repository,
            text_extractor=_build_text_extractor(domain),
            event_publisher=event_publisher,
        ),
    )
    bus.command_bus.subscribe(
        command=SuggestDocumentTypeFieldsCommand,
        handler=SuggestDocumentTypeFieldsHandler(
            document_type_repository=domain.document_type_repository,
            event_publisher=event_publisher,
        ),
    )
