"""
知识库文档模型
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, BigInteger, DateTime, ForeignKey, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    filename: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    file_path: Mapped[str] = mapped_column(
        String(1000), nullable=False
    )
    file_type: Mapped[str] = mapped_column(
        String(20), nullable=False  # pdf, txt, csv, md, docx
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer, default=0
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending"  # pending, processing, completed, failed
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    uploaded_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    uploader = relationship("User", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"


async def ensure_document_sqlite_schema(db: AsyncSession) -> None:
    """补齐旧 SQLite 数据库的文档一致性字段（新库由 metadata 直接创建）。"""
    if db.bind is None or db.bind.dialect.name != "sqlite":
        return

    columns = {
        row[1] for row in (await db.execute(text("PRAGMA table_info(documents)"))).all()
    }
    if "revision" not in columns:
        await db.execute(
            text("ALTER TABLE documents ADD COLUMN revision INTEGER NOT NULL DEFAULT 1")
        )
    # SQLite 无法通过 ALTER TABLE 添加 UNIQUE 约束，使用等效唯一索引。
    await db.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_file_hash "
            "ON documents (file_hash)"
        )
    )
    await db.commit()
