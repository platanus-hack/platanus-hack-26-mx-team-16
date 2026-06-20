"""add_dashboard_indexes

Adds the composite index that the tenant-scoped dashboard aggregations
in `src.dashboard.infrastructure.repositories.sql_dashboard_metrics`
rely on. Existing indexes on `workflow_documents` are workflow-scoped
(`ix_wf_docs_workflow_status`, `ix_wf_docs_tenant_workflow`); neither
covers the dashboard's filter pattern (`tenant_id` first, then
`status`, then `created_at` for monthly/today windows).

Without this index every dashboard request triggers a sequential scan
over the whole `workflow_documents` table, which is unacceptable past
a few hundred thousand rows.

Revision ID: d4e5f6a7b8c9
Revises: b1c2d3e4f5a6
Create Date: 2026-05-19 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEX_NAME = "ix_wf_docs_tenant_status_created"


def upgrade() -> None:
    op.create_index(
        _INDEX_NAME,
        "workflow_documents",
        ["tenant_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="workflow_documents")
