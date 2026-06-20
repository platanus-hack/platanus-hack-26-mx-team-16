"""standard_webhooks

Outbound webhooks for STANDARD workflows (spec product/specs/source-webhooks/standard-webhooks.md):
- webhook config columns on ``workflows`` (§4.9)
- new ``workflow_events`` table (§4.1)
- ``error`` column on ``workflow_documents`` (§2.6)

Revision ID: b2e7c1a9d4f0
Revises: c8556becef15
Create Date: 2026-06-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2e7c1a9d4f0'
down_revision: Union[str, None] = 'c8556becef15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- §4.9 webhook config on workflows ---
    op.add_column('workflows', sa.Column('webhook_url', sa.String(length=2048), nullable=True))
    op.add_column(
        'workflows',
        sa.Column('webhook_enabled', sa.Boolean(), server_default='false', nullable=False),
    )
    op.add_column('workflows', sa.Column('webhook_secret', sa.String(length=255), nullable=True))
    op.add_column(
        'workflows',
        sa.Column(
            'webhook_events',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default='["document.extracted", "document.failed"]',
            nullable=False,
        ),
    )

    # --- §2.6 structured error snapshot on workflow_documents ---
    op.add_column(
        'workflow_documents',
        sa.Column('error', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # --- §4.1 workflow_events (append-only outbound events) ---
    op.create_table(
        'workflow_events',
        sa.Column('uuid', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('document_set_id', sa.UUID(), nullable=True),
        sa.Column('document_id', sa.UUID(), nullable=True),
        sa.Column('processing_job_id', sa.String(length=255), nullable=False),
        sa.Column('document_status', sa.String(length=25), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('delivery_status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.uuid'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.uuid'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_set_id'], ['workflow_document_sets.uuid'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['document_id'], ['workflow_documents.uuid'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('uuid'),
        sa.UniqueConstraint('event_id', name='uq_workflow_events_event_id'),
        sa.UniqueConstraint(
            'document_id',
            'event_type',
            'processing_job_id',
            name='uq_workflow_events_doc_type_job',
        ),
    )
    op.create_index(
        'ix_workflow_events_delivery_status', 'workflow_events', ['delivery_status'], unique=False
    )
    op.create_index(
        'ix_workflow_events_tenant_workflow_created',
        'workflow_events',
        ['tenant_id', 'workflow_id', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_workflow_events_tenant_workflow_created', table_name='workflow_events')
    op.drop_index('ix_workflow_events_delivery_status', table_name='workflow_events')
    op.drop_table('workflow_events')

    op.drop_column('workflow_documents', 'error')

    op.drop_column('workflows', 'webhook_events')
    op.drop_column('workflows', 'webhook_secret')
    op.drop_column('workflows', 'webhook_enabled')
    op.drop_column('workflows', 'webhook_url')
