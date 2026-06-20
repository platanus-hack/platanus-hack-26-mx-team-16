"""connection_accounts

Org-level connection accounts for the Connections feature
(spec product/specs/connections/spec.md §2.1/§4.1). Reusable accounts (webhook, slack,
email, …) that workflows reference as Origins/Destinations.

Revision ID: d3f4a5b6c7e8
Revises: b2e7c1a9d4f0
Create Date: 2026-06-02 13:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd3f4a5b6c7e8'
down_revision: str | None = 'b2e7c1a9d4f0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'connection_accounts',
        sa.Column('uuid', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=30), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='CONNECTED', nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('secret', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.uuid'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('uuid'),
    )
    op.create_index(
        'ix_connection_accounts_tenant_created',
        'connection_accounts',
        ['tenant_id', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_connection_accounts_tenant_created', table_name='connection_accounts')
    op.drop_table('connection_accounts')
