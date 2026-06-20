"""webhook_destinations

Per-workflow webhook destinations (spec connections §4.3): a workflow may have
many destinations, each with its own URL, signing secret and event
subscriptions. Adds ``destination_id`` to ``workflow_events`` so each delivery
is tied to a destination (per-destination delivery log + charts), and migrates
the legacy single per-workflow webhook config into one destination per workflow,
backfilling existing events.

Revision ID: e5a6b7c8d9f0
Revises: d3f4a5b6c7e8
Create Date: 2026-06-02 14:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5a6b7c8d9f0'
down_revision: str | None = 'd3f4a5b6c7e8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- webhook_destinations ------------------------------------------------
    op.create_table(
        'webhook_destinations',
        sa.Column('uuid', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('secret', sa.String(length=512), nullable=True),
        sa.Column(
            'subscribed_events',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default='["document.extracted", "document.failed"]',
            nullable=False,
        ),
        sa.Column('api_version', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.uuid'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.uuid'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('uuid'),
    )
    op.create_index('ix_webhook_destinations_workflow', 'webhook_destinations', ['workflow_id'], unique=False)
    op.create_index(
        'ix_webhook_destinations_tenant_created',
        'webhook_destinations',
        ['tenant_id', 'created_at'],
        unique=False,
    )

    # --- workflow_events.destination_id --------------------------------------
    op.add_column('workflow_events', sa.Column('destination_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_workflow_events_destination',
        'workflow_events',
        'webhook_destinations',
        ['destination_id'],
        ['uuid'],
        ondelete='SET NULL',
    )
    # Idempotency key now fans out per destination.
    op.drop_constraint('uq_workflow_events_doc_type_job', 'workflow_events', type_='unique')
    op.create_unique_constraint(
        'uq_workflow_events_doc_type_job',
        'workflow_events',
        ['document_id', 'event_type', 'processing_job_id', 'destination_id'],
    )
    op.create_index(
        'ix_workflow_events_destination_created',
        'workflow_events',
        ['destination_id', 'created_at'],
        unique=False,
    )

    # --- migrate legacy single webhook config into a destination -------------
    op.execute(
        """
        INSERT INTO webhook_destinations
            (uuid, tenant_id, workflow_id, name, url, description,
             enabled, secret, subscribed_events, api_version, created_at, updated_at)
        SELECT gen_random_uuid(), w.tenant_id, w.uuid,
               'Default webhook', w.webhook_url,
               'Migrated from workflow webhook config',
               w.webhook_enabled, w.webhook_secret,
               COALESCE(w.webhook_events, '["document.extracted", "document.failed"]'::jsonb),
               NULL, now(), now()
        FROM workflows w
        WHERE w.webhook_url IS NOT NULL AND w.webhook_url <> ''
        """
    )
    # Backfill existing events to their workflow's (single) migrated destination.
    op.execute(
        """
        UPDATE workflow_events e
        SET destination_id = d.uuid
        FROM webhook_destinations d
        WHERE d.workflow_id = e.workflow_id
          AND e.destination_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint('uq_workflow_events_doc_type_job', 'workflow_events', type_='unique')
    op.drop_index('ix_workflow_events_destination_created', table_name='workflow_events')
    op.drop_constraint('fk_workflow_events_destination', 'workflow_events', type_='foreignkey')
    op.drop_column('workflow_events', 'destination_id')
    op.create_unique_constraint(
        'uq_workflow_events_doc_type_job',
        'workflow_events',
        ['document_id', 'event_type', 'processing_job_id'],
    )

    op.drop_index('ix_webhook_destinations_tenant_created', table_name='webhook_destinations')
    op.drop_index('ix_webhook_destinations_workflow', table_name='webhook_destinations')
    op.drop_table('webhook_destinations')
