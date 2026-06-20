"""add_requires_password_to_tenant_user_invitations

Revision ID: 61cece5f2883
Revises: 45f7e52f7ca4
Create Date: 2026-05-22 01:12:17.120908

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61cece5f2883'
down_revision: Union[str, None] = '45f7e52f7ca4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'tenant_user_invitations',
        sa.Column(
            'requires_password',
            sa.Boolean(),
            server_default='true',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('tenant_user_invitations', 'requires_password')