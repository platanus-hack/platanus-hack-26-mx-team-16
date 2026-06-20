from uuid import UUID

from pydantic import ConfigDict

from src.common.domain.entities.email_address import RawEmailAddress


class EmailAddress(RawEmailAddress):
    uuid: UUID
    is_verified: bool = False

    model_config = ConfigDict(
        from_attributes=True,
    )
