from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.assets.infrastructure.services.s3_storage import S3StorageService
from src.common.domain.contexts.domain import DomainContext
from src.common.infrastructure.services.jwt_token_builder import JwtTokenBuilder
from src.common.infrastructure.services.jwt_token_service import JwtTokenService
from src.common.infrastructure.services.redis_token_store import RedisTokenStore
from src.common.settings import settings
from src.scans.infrastructure.repositories.sql_agentic_surface import (
    SQLAgenticSurfaceRepository,
)
from src.scans.infrastructure.repositories.sql_finding import SQLFindingRepository
from src.scans.infrastructure.repositories.sql_public_report import SQLPublicReportRepository
from src.scans.infrastructure.repositories.sql_scan import SQLScanRepository
from src.scans.infrastructure.repositories.sql_scan_event import SQLScanEventRepository
from src.sites.infrastructure.repositories.sql_notification_prefs import (
    SQLNotificationPrefsRepository,
)
from src.sites.infrastructure.repositories.sql_site import SQLSiteRepository
from src.sites.infrastructure.repositories.sql_watchlist import SQLWatchlistRepository
from src.tenants.infrastructure.repositories.sql_tenant import SQLTenantRepository
from src.tenants.infrastructure.repositories.sql_tenant_role import SQLTenantRoleRepository
from src.tenants.infrastructure.repositories.sql_tenant_user import SQLTenantUserRepository
from src.tenants.infrastructure.repositories.sql_tenant_user_invitation import (
    SQLTenantUserInvitationRepository,
)
from src.users.infrastructure.repositories.sql_email_address import SQLEmailAddressRepository
from src.users.infrastructure.repositories.sql_phone_number import SQLPhoneNumberRepository
from src.users.infrastructure.repositories.sql_user import SQLUserRepository


def build_async_domain(session: AsyncSession) -> DomainContext:
    return DomainContext(
        # -> USERS
        user_repository=SQLUserRepository(session=session),
        email_repository=SQLEmailAddressRepository(session=session),
        phone_repository=SQLPhoneNumberRepository(session=session),
        tenant_user_repository=SQLTenantUserRepository(session=session),
        # -> TENANTS
        tenant_repository=SQLTenantRepository(session=session),
        tenant_role_repository=SQLTenantRoleRepository(session=session),
        tenant_user_invitation_repository=SQLTenantUserInvitationRepository(session=session),
        # -> COMMON
        token_service=JwtTokenService(
            token_builder=JwtTokenBuilder(),
            token_store=RedisTokenStore(redis_client=Redis.from_url(settings.redis_url)),
        ),
        # -> ASSETS
        storage_service=S3StorageService(),
        # -> SITES
        site_repository=SQLSiteRepository(session=session),
        watchlist_repository=SQLWatchlistRepository(session=session),
        notification_prefs_repository=SQLNotificationPrefsRepository(session=session),
        # -> SCANS
        scan_repository=SQLScanRepository(session=session),
        finding_repository=SQLFindingRepository(session=session),
        public_report_repository=SQLPublicReportRepository(session=session),
        scan_event_repository=SQLScanEventRepository(session=session),
        agentic_surface_repository=SQLAgenticSurfaceRepository(session=session),
    )
