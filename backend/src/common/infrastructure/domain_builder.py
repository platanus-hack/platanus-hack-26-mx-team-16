from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.assets.infrastructure.services.s3_storage import S3StorageService
from src.common.domain.contexts.domain import DomainContext
from src.common.infrastructure.services.jwt_token_builder import JwtTokenBuilder
from src.common.infrastructure.services.jwt_token_service import JwtTokenService
from src.common.infrastructure.services.redis_token_store import RedisTokenStore
from src.common.settings import settings
from src.connections.infrastructure.repositories.sql_connection_account import (
    SQLConnectionAccountRepository,
)
from src.dashboard.infrastructure.repositories.sql_dashboard_metrics import (
    SQLDashboardMetricsRepository,
)
from src.industries.infrastructure.repositories.sql_industry_repository import (
    SQLIndustryRepository,
)
from src.staff.infrastructure.repositories.sql_staff_user import SQLStaffUserRepository
from src.knowledge_base.infrastructure.repositories.sql_kb_document_repository import SQLKBDocumentRepository
from src.knowledge_base.infrastructure.repositories.sql_kb_embedding_repository import SQLKBEmbeddingRepository
from src.storage.infrastructure.repositories.s3_file_repository import S3FileRepository
from src.tenants.infrastructure.repositories.sql_tenant import SQLTenantRepository
from src.tenants.infrastructure.repositories.sql_tenant_role import SQLTenantRoleRepository
from src.tenants.infrastructure.repositories.sql_tenant_user import SQLTenantUserRepository
from src.tenants.infrastructure.repositories.sql_tenant_user_invitation import (
    SQLTenantUserInvitationRepository,
)
from src.usage.infrastructure.repositories.sql_process_record import SQLProcessRecordRepository
from src.users.infrastructure.repositories.sql_email_address import SQLEmailAddressRepository
from src.users.infrastructure.repositories.sql_phone_number import SQLPhoneNumberRepository
from src.users.infrastructure.repositories.sql_user import SQLUserRepository
from src.workflows.infrastructure.repositories.sql_document_repository import SQLWorkflowDocumentRepository
from src.workflows.infrastructure.repositories.sql_document_type import SQLDocumentTypeRepository
from src.workflows.infrastructure.repositories.sql_pipeline import SQLPipelineRepository
from src.workflows.infrastructure.repositories.sql_run_summary import (
    SQLWorkflowAnalysisRunSummaryRepository,
)
from src.workflows.infrastructure.repositories.sql_webhook_destination import (
    SQLWebhookDestinationRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow import SQLWorkflowRepository
from src.workflows.infrastructure.repositories.sql_workflow_analysis_run import (
    SQLWorkflowAnalysisRunRepository,
)
from src.workflows.infrastructure.repositories.sql_case_event import SQLCaseEventRepository
from src.workflows.infrastructure.repositories.sql_workflow_case import SQLWorkflowCaseRepository
from src.workflows.infrastructure.repositories.sql_workflow_phase_execution import (
    SQLWorkflowPhaseExecutionRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow_processing_job import (
    SQLWorkflowProcessingJobRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow_event import SQLWorkflowEventRepository
from src.workflows.infrastructure.repositories.sql_workflow_member import SQLWorkflowMemberRepository
from src.workflows.infrastructure.repositories.sql_workflow_rule import SQLWorkflowRuleRepository
from src.workflows.infrastructure.repositories.sql_workflow_rule_compilation import (
    SQLWorkflowRuleCompilationRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow_rule_result import (
    SQLWorkflowRuleResultRepository,
)
from src.workflows.infrastructure.repositories.sql_tool import SQLToolRepository


def build_async_domain(session: AsyncSession) -> DomainContext:
    return DomainContext(
        # -> USERS
        user_repository=SQLUserRepository(session=session),
        email_repository=SQLEmailAddressRepository(session=session),
        phone_repository=SQLPhoneNumberRepository(session=session),
        tenant_user_repository=SQLTenantUserRepository(session=session),
        # -> STAFF (ADR 0001)
        staff_user_repository=SQLStaffUserRepository(session=session),
        # -> TENANTS
        tenant_repository=SQLTenantRepository(session=session),
        tenant_role_repository=SQLTenantRoleRepository(session=session),
        tenant_user_invitation_repository=SQLTenantUserInvitationRepository(session=session),
        # -> INDUSTRIES
        industry_repository=SQLIndustryRepository(session=session),
        # -> DOCUMENTS
        document_repository=SQLWorkflowDocumentRepository(session=session),
        processing_job_repository=SQLWorkflowProcessingJobRepository(session=session),
        phase_execution_repository=SQLWorkflowPhaseExecutionRepository(session=session),
        file_repository=S3FileRepository(session=session),
        # -> WORKFLOWS
        workflow_repository=SQLWorkflowRepository(session=session),
        pipeline_repository=SQLPipelineRepository(session=session),
        workflow_event_repository=SQLWorkflowEventRepository(session=session),
        workflow_member_repository=SQLWorkflowMemberRepository(session=session),
        webhook_destination_repository=SQLWebhookDestinationRepository(session=session),
        workflow_case_repository=SQLWorkflowCaseRepository(session=session),
        case_event_repository=SQLCaseEventRepository(session=session),
        document_type_repository=SQLDocumentTypeRepository(session=session),
        workflow_rule_repository=SQLWorkflowRuleRepository(session=session),
        workflow_rule_compilation_repository=SQLWorkflowRuleCompilationRepository(session=session),
        workflow_rule_result_repository=SQLWorkflowRuleResultRepository(session=session),
        workflow_analysis_run_repository=SQLWorkflowAnalysisRunRepository(session=session),
        run_summary_repository=SQLWorkflowAnalysisRunSummaryRepository(session=session),
        tool_repository=SQLToolRepository(session=session),
        # -> KNOWLEDGE BASE
        kb_document_repository=SQLKBDocumentRepository(session=session),
        kb_embedding_repository=SQLKBEmbeddingRepository(session=session),
        # -> CONNECTIONS
        connection_account_repository=SQLConnectionAccountRepository(session=session),
        # -> USAGE
        process_record_repository=SQLProcessRecordRepository(session=session),
        # -> DASHBOARD
        dashboard_metrics_repository=SQLDashboardMetricsRepository(session=session),
        # -> COMMON
        token_service=JwtTokenService(
            token_builder=JwtTokenBuilder(),
            token_store=RedisTokenStore(redis_client=Redis.from_url(settings.redis_url)),
            # ADR 0001: re-derivar `is_staff` en el refresh (el claim moriría
            # a los 10 min si solo se emitiera en login).
            staff_user_repository=SQLStaffUserRepository(session=session),
        ),
        # -> ASSETS
        storage_service=S3StorageService(),
    )
