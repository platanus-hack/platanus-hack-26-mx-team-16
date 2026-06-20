"""add_doctype_keywords_examples

Revision ID: c8556becef15
Revises: 96f1fec32ff5
Create Date: 2026-06-01 15:34:26.136144

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c8556becef15'
down_revision: Union[str, None] = '96f1fec32ff5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('document_types', sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))
    op.add_column('document_types', sa.Column('examples', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))


def downgrade() -> None:
    op.drop_column('document_types', 'examples')
    op.drop_column('document_types', 'keywords')