from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class DocumentORM(Base, UUIDTenantTimestampMixin):
    __tablename__ = "documents"

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)

    def __repr__(self) -> str:
        return f"<DocumentORM(uuid={self.uuid}, file_name={self.file_name})>"
