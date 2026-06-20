"""ORM models for the eval platform (F11 · decision A5).

An ``EvalDatasetORM`` is a tenant-scoped, named collection of golden cases
(input + expected output) pinned to a pipeline. ``EvalRunORM`` records a single
evaluation pass of a pipeline version over a dataset, with aggregate metrics.
"""

from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class EvalDatasetORM(Base, UUIDTenantTimestampMixin):
    """A tenant-scoped, named collection of golden cases for a pipeline."""

    __tablename__ = "eval_datasets"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    pipeline_slug: Mapped[str] = mapped_column(String(120), nullable=False)

    def __repr__(self) -> str:
        return f"<EvalDatasetORM(name={self.name}, pipeline_slug={self.pipeline_slug})>"


class EvalCaseORM(Base, UUIDTenantTimestampMixin):
    """A single golden case: a pointer to an input + its expected output."""

    __tablename__ = "eval_cases"

    dataset_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("eval_datasets.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    expected: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    def __repr__(self) -> str:
        return f"<EvalCaseORM(dataset_id={self.dataset_id}, input_ref={self.input_ref})>"


class EvalRunORM(Base, UUIDTenantTimestampMixin):
    """A single evaluation pass of a pipeline version over a dataset."""

    __tablename__ = "eval_runs"

    dataset_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("eval_datasets.uuid"),
        nullable=False,
        index=True,
    )
    pipeline_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="PENDING")
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    def __repr__(self) -> str:
        return f"<EvalRunORM(dataset_id={self.dataset_id}, status={self.status})>"
