"""workflow_phase_executions: per-recipe-phase execution timeline

Backs the "Ejecuciones" tab: one row per recipe phase run by the interpreter
(``PipelineInterpreterWorkflow``), written via the ``record_phase_execution``
activity. Idempotent natural key ``(processing_job_id, seq)``.

Revision ID: 9d7e1b3a2c64
Revises: 218667cf7839
Create Date: 2026-06-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "9d7e1b3a2c64"
down_revision = "218667cf7839"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_phase_executions",
        sa.Column("processing_job_id", sa.UUID(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("phase_id", sa.String(length=120), nullable=False),
        sa.Column("phase_kind", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="RUNNING", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("output_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["processing_job_id"], ["workflow_processing_jobs.uuid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("processing_job_id", "seq", name="uq_workflow_phase_executions_job_seq"),
    )
    op.create_index(
        "ix_workflow_phase_executions_job",
        "workflow_phase_executions",
        ["processing_job_id", "seq"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_phase_executions_job", table_name="workflow_phase_executions")
    op.drop_table("workflow_phase_executions")
