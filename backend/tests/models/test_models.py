"""
数据模型 单元测试
"""
import pytest
from app.core.database import Base


class TestUserModel:
    """User 模型测试"""

    def test_create_user(self):
        """创建 User 实例"""
        from app.models.user import User

        user = User(
            id="test-001",
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_xxx",
            is_admin=False,
            is_active=True,
            token_version=0,
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_admin is False
        assert user.is_active is True
        assert user.token_version == 0

    def test_create_admin_user(self):
        """创建管理员 User"""
        from app.models.user import User

        user = User(
            username="admin",
            email="admin@example.com",
            hashed_password="hashed_xxx",
            is_admin=True,
        )
        assert user.is_admin is True

    def test_user_repr(self):
        """__repr__ 方法"""
        from app.models.user import User

        user = User(
            id="abc-123", username="test",
            email="t@t.com", hashed_password="x"
        )
        repr_str = repr(user)
        assert "abc-123" in repr_str
        assert "test" in repr_str

    def test_user_table_name(self):
        """表名正确"""
        from app.models.user import User
        assert User.__tablename__ == "users"

    def test_user_base_class(self):
        """继承自 Base"""
        from app.models.user import User
        assert issubclass(User, Base)


class TestConversationModel:
    """Conversation 模型测试"""

    def test_create_conversation(self):
        """创建 Conversation 实例"""
        from app.models.conversation import Conversation

        conv = Conversation(
            user_id="user-1", title="测试会话",
            is_archived=False, is_pinned=False, message_count=0,
        )
        assert conv.title == "测试会话"
        assert conv.user_id == "user-1"
        assert conv.is_archived is False
        assert conv.is_pinned is False
        assert conv.message_count == 0

    def test_conversation_repr(self):
        """__repr__ 方法"""
        from app.models.conversation import Conversation

        conv = Conversation(user_id="user-1", title="测试")
        conv.id = "conv-123"
        assert "conv-123" in repr(conv)
        assert "测试" in repr(conv)

    def test_table_name(self):
        """表名正确"""
        from app.models.conversation import Conversation
        assert Conversation.__tablename__ == "conversations"


class TestMessageModel:
    """Message 模型测试"""

    def test_create_user_message(self):
        """创建用户消息"""
        from app.models.message import Message

        msg = Message(
            conversation_id="conv-1",
            user_id="user-1",
            role="user",
            content="你好",
        )
        assert msg.role == "user"
        assert msg.content == "你好"
        assert msg.sources is None
        assert msg.token_count is None

    def test_create_assistant_message_with_sources(self):
        """创建带来源的 AI 消息"""
        from app.models.message import Message

        sources = [{"doc_name": "test.pdf", "score": 0.85}]
        msg = Message(
            conversation_id="conv-1",
            user_id="user-1",
            role="assistant",
            content="回答内容",
            sources=sources,
            token_count=100,
        )
        assert msg.role == "assistant"
        assert msg.sources == sources
        assert msg.token_count == 100

    def test_message_repr(self):
        """__repr__ 方法"""
        from app.models.message import Message

        msg = Message(conversation_id="c1", user_id="u1", role="user", content="hi")
        msg.id = "msg-1"
        assert "msg-1" in repr(msg)
        assert "user" in repr(msg)

    def test_table_name(self):
        """表名正确"""
        from app.models.message import Message
        assert Message.__tablename__ == "messages"


class TestDocumentModel:
    """Document 模型测试"""

    def test_create_document(self):
        """创建 Document 实例"""
        from app.models.document import Document

        doc = Document(
            filename="test.pdf",
            file_path="/uploads/abc/test.pdf",
            file_type="pdf",
            file_size=1024,
            file_hash="abc123",
            uploaded_by="user-1",
            status="pending",
            chunk_count=0,
        )
        assert doc.filename == "test.pdf"
        assert doc.file_type == "pdf"
        assert doc.status == "pending"
        assert doc.chunk_count == 0
        assert doc.error_message is None

    def test_document_status_values(self):
        """Document 状态值"""
        from app.models.document import Document

        doc = Document(
            filename="t.txt", file_path="/t.txt", file_type="txt",
            file_size=10, file_hash="h", uploaded_by="u",
        )
        doc.status = "completed"
        assert doc.status == "completed"

        doc.status = "failed"
        doc.error_message = "处理失败"
        assert doc.status == "failed"
        assert doc.error_message == "处理失败"

    def test_document_has_revision_and_unique_hash(self):
        """文档 revision 默认从 1 开始，内容哈希为唯一约束。"""
        from app.models.document import Document

        doc = Document(
            filename="t.txt", file_path="/t.txt", file_type="txt",
            file_size=10, file_hash="unique-hash", uploaded_by="u",
        )
        assert str(Document.__table__.c.revision.server_default.arg) == "1"
        assert any(
            constraint.columns.keys() == ["file_hash"]
            for constraint in Document.__table__.constraints
            if hasattr(constraint, "columns")
        )

    @pytest.mark.asyncio
    async def test_sqlite_schema_upgrade_adds_revision_and_unique_index(self):
        """已有 SQLite documents 表可在不使用 Alembic 时补齐一致性字段。"""
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from app.models.document import ensure_document_sqlite_schema

        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.execute(text(
                "CREATE TABLE documents (id TEXT PRIMARY KEY, file_hash TEXT NOT NULL)"
            ))
        session_factory = async_sessionmaker(engine)
        async with session_factory() as session:
            await ensure_document_sqlite_schema(session)
            columns = (await session.execute(text("PRAGMA table_info(documents)"))).all()
            indexes = (await session.execute(text("PRAGMA index_list(documents)"))).all()

        assert "revision" in {column[1] for column in columns}
        assert "uq_documents_file_hash" in {index[1] for index in indexes}
        await engine.dispose()

    def test_document_repr(self):
        """__repr__ 方法"""
        from app.models.document import Document

        doc = Document(
            filename="test.pdf", file_path="/t.pdf", file_type="pdf",
            file_size=100, file_hash="h", uploaded_by="u",
        )
        doc.id = "doc-1"
        assert "doc-1" in repr(doc)
        assert "test.pdf" in repr(doc)

    def test_table_name(self):
        """表名正确"""
        from app.models.document import Document
        assert Document.__tablename__ == "documents"
