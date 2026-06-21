from dataclasses import dataclass

from src.assets.domain.services.storage import StorageService
from src.common.domain.services.token_service import TokenService
from src.scans.domain.repositories.finding import FindingRepository
from src.scans.domain.repositories.public_report import PublicReportRepository
from src.scans.domain.repositories.scan import ScanRepository
from src.scans.domain.repositories.scan_event import ScanEventRepository
from src.sites.domain.repositories.notification_prefs import NotificationPrefsRepository
from src.sites.domain.repositories.site import SiteRepository
from src.sites.domain.repositories.watchlist import WatchlistRepository
from src.tenants.domain.repositories.tenant import TenantRepository
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository
from src.tenants.domain.repositories.tenant_user import TenantUserRepository
from src.tenants.domain.repositories.tenant_user_invitation import (
    TenantUserInvitationRepository,
)
from src.users.domain.repositories.email_address import EmailAddressRepository
from src.users.domain.repositories.phone_number import PhoneNumberRepository
from src.users.domain.repositories.user import UserRepository


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

    # -> COMMON
    token_service: TokenService

    # -> ASSETS
    storage_service: StorageService

    # -> SITES (06-data-model / 12-api)
    site_repository: SiteRepository
    watchlist_repository: WatchlistRepository
    notification_prefs_repository: NotificationPrefsRepository

    # -> SCANS (06-data-model / 12-api)
    scan_repository: ScanRepository
    finding_repository: FindingRepository
    public_report_repository: PublicReportRepository
    scan_event_repository: ScanEventRepository
