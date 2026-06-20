"""add analysis_rule position

Revision ID: a1b2c3d4e5f6
Revises: 55c61ec5b69b
Create Date: 2026-05-04 09:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "55c61ec5b69b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_rules",
        sa.Column(
            "position",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT
                uuid,
                ROW_NUMBER() OVER (
                    PARTITION BY workflow_id
                    ORDER BY created_at ASC, uuid ASC
                ) - 1 AS rn
            FROM analysis_rules
        )
        UPDATE analysis_rules ar
        SET position = ranked.rn
        FROM ranked
        WHERE ar.uuid = ranked.uuid;
        """
    )


def downgrade() -> None:
    op.drop_column("analysis_rules", "position")
