from src.common.application.commands.common import PublishStreamEventCommand, SendEmailCommand
from src.common.application.commands.document_types import (
    ExtractDocumentTypeSampleTextCommand,
    SuggestDocumentTypeFieldsCommand,
)
from src.common.application.commands.knowledge_base import VectorizeKBDocumentCommand
from src.common.application.commands.tenants import SoftDeleteTenantCommand
from src.common.application.commands.users import MergeTenantsCommand
from src.common.domain.buses.commands import Command

async_tasks_mapping: dict[str, type[Command]] = {
    SendEmailCommand.__name__: SendEmailCommand,
    PublishStreamEventCommand.__name__: PublishStreamEventCommand,
    MergeTenantsCommand.__name__: MergeTenantsCommand,
    SoftDeleteTenantCommand.__name__: SoftDeleteTenantCommand,
    VectorizeKBDocumentCommand.__name__: VectorizeKBDocumentCommand,
    ExtractDocumentTypeSampleTextCommand.__name__: ExtractDocumentTypeSampleTextCommand,
    SuggestDocumentTypeFieldsCommand.__name__: SuggestDocumentTypeFieldsCommand,
}
