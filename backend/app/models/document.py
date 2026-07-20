"""
知识库文档模型
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, BigInteger, DateTime, ForeignKey, func
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
        String(64), nullable=False, index=True
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
