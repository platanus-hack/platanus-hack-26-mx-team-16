"""workflow_permissions

Workflow access control (workflow permissions page). Adds ``access_type`` to
``workflows`` ("organization" | "private") and a ``workflow_members`` table that
holds the explicit member grants gating access to private workflows.

Revision ID: f6b7c8d9e0a1
Revises: e5a6b7c8d9f0
Create Date: 2026-06-02 15:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f6b7c8d9e0a1'
down_revision: str | None = 'e5a6b7c8d9f0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'workflows',
        sa.Column('access_type', sa.String(length=20), server_default='organization', nullable=False),
    )

    op.create_table(
        'workflow_members',
        sa.Column('uuid', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=20), server_default='member', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.uuid'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.uuid'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.uuid'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('uuid'),
        sa.UniqueConstraint('workflow_id', 'user_id', name='uq_workflow_member'),
    )
    op.create_index('ix_workflow_members_workflow', 'workflow_members', ['workflow_id'], unique=False)
    op.create_index('ix_workflow_members_user_tenant', 'workflow_members', ['user_id', 'tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_workflow_members_user_tenant', table_name='workflow_members')
    op.drop_index('ix_workflow_members_workflow', table_name='workflow_members')
    op.drop_table('workflow_members')
    op.drop_column('workflows', 'access_type')
