from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.common.application.commands.users import PersistTenantUserCommand, PersistUserCommand
from src.common.application.queries.users import GetUserByIdQuery
from src.common.domain.buses.commands import CommandBus
from src.common.domain.buses.queries import QueryBus
from src.common.domain.entities.phone_number import RawPhoneNumber
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.user import User
from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.helpers.models import override_dict_properties
from src.common.domain.interfaces.use_case import UseCase
from src.users.application.use_cases.tenant_user.mixins import (
    TenantRoleValidatorMixin,
    TenantUserMixin,
)
from src.users.application.use_cases.user.mixins import UserEmailPhoneNumberMixin
from src.users.domain.repositories.email_address import EmailAddressRepository
from src.users.domain.repositories.phone_number import PhoneNumberRepository


@dataclass
class TenantUserUpdater(TenantUserMixin, TenantRoleValidatorMixin, UserEmailPhoneNumberMixin, UseCase):
    """
    Use case for updating a tenant user in a multi-tenant system.

    Business Rules:
    1. Multi-tenant security: A user can only be updated within their organization context
    2. Email uniqueness: Email must be unique across the entire system
    3. Partial updates: Only provided fields are updated, others remain unchanged
    4. Data preservation: If a new value is invalid, the current value is maintained
    5. Separation of concerns: Personal info (User) and tenant relationship (TenantUser) are separate

    Process:
    1. Validate user exists and belongs to the specified tenant (security)
    2. Update personal information (email, phone) if provided
    3. Update tenant relationship fields (status, role, permissions) if provided
    4. Validate and update role only if the new role exists in the tenant
    5. Persist all changes and return updated user
    """

    tenant_id: UUID
    tenant_user_id: UUID
    payload: dict[str, Any]
    command_bus: CommandBus
    query_bus: QueryBus
    phone_number_repository: PhoneNumberRepository
    email_repository: EmailAddressRepository
    email: str | None = None
    phone_number: RawPhoneNumber | dict[str, Any] | None = None

    async def execute(self) -> TenantUser:
        """
        Execute the tenant user update process.

        Returns:
            TenantUser: The updated tenant user with all current data

        Raises:
            TenantUserNotFoundError: If user doesn't exist or doesn't belong to tenant
            UserEmailAlreadyExistsError: If new email is already used by another user
            UserPhoneNumberAlreadyExistsError: If new phone is already used by another user
        """
        # Step 1: Validate user exists and belongs to the specified tenant
        # This is critical for security - prevents cross-tenant modifications
        tenant_user = await self._get_tenant_user()

        # Step 2: Build updates for tenant relationship fields
        # Only include valid updates, preserving current values for invalid ones
        tenant_user_updates = await self._build_tenant_user_updates()

        # Step 3: Prepare personal information updates (email, phone)
        email = self._build_email()
        phone_number = self._build_phone_number(self.phone_number) if self.phone_number else None

        # Step 4: Validate email and phone uniqueness across the system
        # Only validate if new values are provided
        if email:
            await self.assert_email_is_unique(email, tenant_user.user_id)
        if phone_number:
            await self.assert_phone_number_is_unique(phone_number, tenant_user.user_id)

        # Step 5: Apply tenant relationship updates
        override_dict_properties(tenant_user, tenant_user_updates)

        # Step 6: Update personal information in User entity if needed
        user = await self._fetch_user(tenant_user.user_id)
        if user:
            user_updated = await self._sync_user(user, email, phone_number)
            if user_updated:
                await self.command_bus.dispatch(PersistUserCommand(user=user))

        # Step 7: Persist tenant user changes
        await self.command_bus.dispatch(PersistTenantUserCommand(tenant_user=tenant_user))

        # Step 8: Return fresh data from database
        return await self._get_tenant_user()

    async def _build_tenant_user_updates(self) -> dict[str, Any]:
        """
        Build the updates dictionary for TenantUser fields.

        This method implements partial update logic:
        - Only fields present in payload are updated
        - Invalid values are filtered out (e.g., non-existent role)
        - Current values are preserved for fields not in payload

        Returns:
            dict: Validated updates to apply to TenantUser
        """
        updates = dict(self.payload)

        # Validate and process tenant_role_id
        # Rule: Only update role if it exists in the tenant
        # If role doesn't exist, preserve current role (don't update)
        if tenant_role := updates.get("tenant_role_id"):
            tenant_role_uuid = tenant_role if isinstance(tenant_role, UUID) else UUID(str(tenant_role))

            # Check if role exists in tenant
            role = await self._get_tenant_role(tenant_role_uuid)

            if role is not None:
                # Role exists, include it in updates
                updates["tenant_role_id"] = tenant_role_uuid
            else:
                # Role doesn't exist, remove from updates to preserve current value
                updates.pop("tenant_role_id", None)

        # Convert status string to enum if needed
        if isinstance(status := updates.get("status"), str):
            updates["status"] = TenantUserStatus(status)

        # Filter to only allowed fields for tenant relationship
        allowed = {
            "first_name",
            "last_name",
            "status",
            "tenant_role_id",
            "permissions",
            "is_owner",
            "is_support",
            "photo",
        }
        return {k: updates[k] for k in allowed if k in updates}

    def _build_email(self) -> str | None:
        """
        Build and normalize email from input.

        Returns:
            str | None: Normalized email or None if not provided
        """
        return self.email.strip() if self.email else None

    async def _fetch_user(self, user_id: UUID) -> User | None:
        """
        Fetch the User entity by ID.

        Args:
            user_id: UUID of the user

        Returns:
            User | None: User entity or None if not found
        """
        result = await self.query_bus.ask(GetUserByIdQuery(user_id=user_id))
        return result if isinstance(result, User) else None

    async def _sync_user(
        self,
        user: User,
        email: str | None,
        phone_number: RawPhoneNumber | None,
    ) -> bool:
        """
        Synchronize personal information changes to User entity.

        This handles the "personal info" side of the update, separate from
        the tenant relationship info.

        Args:
            user: User entity to update
            email: New email if provided
            phone_number: New phone number if provided

        Returns:
            bool: True if any changes were made, False otherwise
        """
        updated = False

        # Update email if provided and different from current
        if email:
            current_email = user.email_address.email if user.email_address else None
            if current_email != email:
                user.email_address = await self.email_repository.get_or_create(email=email)
                updated = True

        # Update phone number if provided and different from current
        if phone_number:
            current_phone = user.phone_number.to_raw if user.phone_number else None
            if current_phone != phone_number:
                user.phone_number = await self.phone_number_repository.get_or_create(phone_number=phone_number)
                updated = True

        return updated
