from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.models.processing.workflow_document import WorkflowDocument


class WorkflowDocumentRepository(ABC):
    @abstractmethod
    async def find_by_id(self, document_id: UUID, tenant_id: UUID) -> WorkflowDocument | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_case(self, case_id: UUID, tenant_id: UUID) -> list[WorkflowDocument]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_case_and_file(self, case_id: UUID, file_id: UUID, tenant_id: UUID) -> list[WorkflowDocument]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_processing_job(self, processing_job_id: UUID) -> list[WorkflowDocument]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_processing_job_ids(self, processing_job_ids: list[UUID], tenant_id: UUID) -> list[WorkflowDocument]:
        """Batch fetch para el SSE replay: una sola query para todos los
        sets que el cliente debe re-hidratar."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_case_ids(self, case_ids: list[UUID], tenant_id: UUID) -> dict[UUID, list[WorkflowDocument]]:
        """Batch fetch para el listado de cases: una sola query devuelve
        los WorkflowDocument agrupados por case_id, evitando el N+1
        cuando el endpoint mapea cada case con sus docs."""
        raise NotImplementedError

    @abstractmethod
    async def create(self, document: WorkflowDocument) -> WorkflowDocument:
        raise NotImplementedError

    @abstractmethod
    async def update(self, document: WorkflowDocument) -> WorkflowDocument:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, document_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError
