from src.common.application.commands.knowledge_base import VectorizeKBDocumentCommand
from src.common.domain.contexts.bus import BusContext
from src.common.domain.contexts.domain import DomainContext
from src.knowledge_base.application.command.vectorize_kb_document import VectorizeKBDocumentHandler


def knowledge_base_wiring(
    domain: DomainContext,
    bus: BusContext,
):
    #  C O M M A N D S
    bus.command_bus.subscribe(
        command=VectorizeKBDocumentCommand,
        handler=VectorizeKBDocumentHandler(
            document_repository=domain.kb_document_repository,
            embedding_repository=domain.kb_embedding_repository,
        ),
    )
