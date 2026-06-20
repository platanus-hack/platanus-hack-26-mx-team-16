from dataclasses import dataclass

from src.assets.domain.services.storage import StorageService
from src.common.domain.services.token_service import TokenService
from src.connections.domain.repositories.connection_account import ConnectionAccountRepository
from src.staff.domain.repositories.staff_user import StaffUserRepository
from src.dashboard.domain.repositories.dashboard_metrics import DashboardMetricsRepository
from src.industries.domain.repositories.industry_repository import IndustryRepository
from src.knowledge_base.domain.repositories.kb_document_repository import KBDocumentRepository
from src.knowledge_base.domain.repositories.kb_embedding_repository import KBEmbeddingRepository
from src.storage.domain.repositories.file_repository import FileRepository
from src.tenants.domain.repositories.tenant import TenantRepository
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository
from src.tenants.domain.repositories.tenant_user import TenantUserRepository
from src.tenants.domain.repositories.tenant_user_invitation import (
    TenantUserInvitationRepository,
)
from src.usage.domain.repositories.process_record import ProcessRecordRepository
from src.users.domain.repositories.email_address import EmailAddressRepository
from src.users.domain.repositories.phone_number import PhoneNumberRepository
from src.users.domain.repositories.user import UserRepository
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.tool import ToolRepository
from src.workflows.domain.repositories.webhook_destination import WebhookDestinationRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_analysis_run import (
    WorkflowAnalysisRunRepository,
)
from src.workflows.domain.repositories.case_event import CaseEventRepository
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository
from src.workflows.domain.repositories.workflow_phase_execution_repository import (
    WorkflowPhaseExecutionRepository,
)
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)
from src.workflows.domain.repositories.workflow_event import WorkflowEventRepository
from src.workflows.domain.repositories.workflow_member import WorkflowMemberRepository
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.domain.rules.repositories.workflow_rule_compilation import (
    WorkflowRuleCompilationRepository,
)
from src.workflows.domain.rules.repositories.workflow_rule_result import (
    WorkflowRuleResultRepository,
)
from src.workflows.domain.run_summary.repositories.run_summary import (
    WorkflowAnalysisRunSummaryRepository,
)


@dataclass
class DomainContext:
    # -> USERS
    user_repository: UserRepository
    email_repository: EmailAddressRepository
    phone_repository: PhoneNumberRepository
    tenant_user_repository: TenantUserRepository

    # -> TENANTS
    tenant_repository: TenantRepository
    tenant_role_repository: TenantRoleRepository
    tenant_user_invitation_repository: TenantUserInvitationRepository

    # -> STAFF (ADR 0001: emisión del claim is_staff + StaffUserDep)
    staff_user_repository: StaffUserRepository

    # -> INDUSTRIES
    industry_repository: IndustryRepository

    # -> DOCUMENTS
    document_repository: WorkflowDocumentRepository
    processing_job_repository: WorkflowProcessingJobRepository
    phase_execution_repository: WorkflowPhaseExecutionRepository
    file_repository: FileRepository

    # -> WORKFLOWS
    workflow_repository: WorkflowRepository
    pipeline_repository: PipelineRepository
    workflow_event_repository: WorkflowEventRepository
    workflow_member_repository: WorkflowMemberRepository
    webhook_destination_repository: WebhookDestinationRepository
    workflow_case_repository: WorkflowCaseRepository
    case_event_repository: CaseEventRepository
    document_type_repository: DocumentTypeRepository
    workflow_rule_repository: WorkflowRuleRepository
    workflow_rule_compilation_repository: WorkflowRuleCompilationRepository
    workflow_rule_result_repository: WorkflowRuleResultRepository
    workflow_analysis_run_repository: WorkflowAnalysisRunRepository
    run_summary_repository: WorkflowAnalysisRunSummaryRepository
    tool_repository: ToolRepository

    # -> KNOWLEDGE BASE
    kb_document_repository: KBDocumentRepository
    kb_embedding_repository: KBEmbeddingRepository

    # -> CONNECTIONS
    connection_account_repository: ConnectionAccountRepository

    # -> USAGE
    process_record_repository: ProcessRecordRepository

    # -> DASHBOARD
    dashboard_metrics_repository: DashboardMetricsRepository

    # -> COMMON
    token_service: TokenService

    # -> ASSETS
    storage_service: StorageService
