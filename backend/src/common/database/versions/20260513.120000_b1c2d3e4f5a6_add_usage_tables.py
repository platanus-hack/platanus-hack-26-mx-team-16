"""add_usage_tables

Revision ID: b1c2d3e4f5a6
Revises: 4fd3772c2a94
Create Date: 2026-05-13 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "4fd3772c2a94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "plan_slug",
            sa.String(length=50),
            nullable=False,
            server_default="starter",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column("monthly_page_quota_override", sa.Integer(), nullable=True),
    )

    op.create_table(
        "process_records",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("workflow_slug", sa.String(length=100), nullable=False),
        sa.Column("document_digest", sa.String(length=64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("analysis_run_id", sa.UUID(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.uuid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["workflow_analysis_runs.uuid"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(
        "ix_process_records_tenant_processed_at",
        "process_records",
        ["tenant_id", "processed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_process_records_tenant_processed_at", table_name="process_records")
    op.drop_table("process_records")
    op.drop_column("tenants", "monthly_page_quota_override")
    op.drop_column("tenants", "plan_slug")
