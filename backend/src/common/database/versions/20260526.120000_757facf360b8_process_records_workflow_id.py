"""process_records: replace workflow_slug with workflow_id FK

Revision ID: 757facf360b8
Revises: 61cece5f2883
Create Date: 2026-05-26 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "757facf360b8"
down_revision: Union[str, None] = "61cece5f2883"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("process_records")}
    fks = {fk["name"] for fk in inspector.get_foreign_keys("process_records")}

    if "workflow_slug" in columns:
        op.drop_column("process_records", "workflow_slug")
    if "workflow_id" not in columns:
        op.add_column(
            "process_records",
            sa.Column("workflow_id", sa.UUID(), nullable=True),
        )
    if "fk_process_records_workflow_id" not in fks:
        op.create_foreign_key(
            "fk_process_records_workflow_id",
            "process_records",
            "workflows",
            ["workflow_id"],
            ["uuid"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    op.drop_constraint("fk_process_records_workflow_id", "process_records", type_="foreignkey")
    op.drop_column("process_records", "workflow_id")
    op.add_column(
        "process_records",
        sa.Column("workflow_slug", sa.String(length=100), nullable=False, server_default=""),
    )
    op.alter_column("process_records", "workflow_slug", server_default=None)
