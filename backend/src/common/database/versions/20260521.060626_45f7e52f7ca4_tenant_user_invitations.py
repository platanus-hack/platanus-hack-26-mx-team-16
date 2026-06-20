"""tenant_user_invitations

Revision ID: 45f7e52f7ca4
Revises: d4e5f6a7b8c9
Create Date: 2026-05-21 06:06:26.096988

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45f7e52f7ca4'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tenant_user_invitations',
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('tenant_role_id', sa.UUID(), nullable=True),
        sa.Column('token', sa.String(length=128), nullable=False),
        sa.Column(
            'status',
            sa.String(length=25),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('uuid', sa.UUID(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.uuid'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.uuid'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_role_id'], ['tenant_roles.uuid'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('uuid'),
        sa.UniqueConstraint('token', name='uq_tenant_user_invitations_token'),
    )
    # Partial unique: only one PENDING invitation per (tenant_id, email).
    op.create_index(
        'uq_tenant_user_invitations_pending_email',
        'tenant_user_invitations',
        ['tenant_id', 'email'],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.create_index(
        'ix_tenant_user_invitations_tenant_id',
        'tenant_user_invitations',
        ['tenant_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_tenant_user_invitations_tenant_id',
        table_name='tenant_user_invitations',
    )
    op.drop_index(
        'uq_tenant_user_invitations_pending_email',
        table_name='tenant_user_invitations',
    )
    op.drop_table('tenant_user_invitations')