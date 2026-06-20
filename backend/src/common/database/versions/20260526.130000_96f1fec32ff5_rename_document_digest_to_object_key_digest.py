"""process_records: rename document_digest to object_key_digest

The field was hashing the S3 object key (the storage path), not the
document content. Renaming makes the semantics explicit.

Revision ID: 96f1fec32ff5
Revises: 757facf360b8
Create Date: 2026-05-26 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "96f1fec32ff5"
down_revision: Union[str, None] = "757facf360b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("process_records", "document_digest", new_column_name="object_key_digest")


def downgrade() -> None:
    op.alter_column("process_records", "object_key_digest", new_column_name="document_digest")
