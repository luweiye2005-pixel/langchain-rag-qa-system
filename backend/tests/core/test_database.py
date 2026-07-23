"""
数据库连接管理 单元测试
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestGetEngineKwargs:
    """_get_engine_kwargs 函数测试"""

    def test_sqlite_detection(self):
        """检测 SQLite URL 并返回对应参数"""
        from app.core.database import _get_engine_kwargs

        kwargs = _get_engine_kwargs("sqlite+aiosqlite:///test.db")
        assert kwargs["echo"] is False
        assert "connect_args" in kwargs
        assert kwargs["connect_args"] == {"check_same_thread": False}

    def test_postgresql_returns_pool_kwargs(self):
        """PostgreSQL URL 返回连接池参数"""
        from app.core.database import _get_engine_kwargs

        kwargs = _get_engine_kwargs("postgresql+asyncpg://user:pass@localhost/db")
        assert kwargs["echo"] is False
        assert kwargs["pool_size"] == 20
        assert kwargs["max_overflow"] == 10
        assert kwargs["pool_recycle"] == 3600
        assert kwargs["pool_pre_ping"] is True

    def test_postgresql_no_connect_args(self):
        """PostgreSQL 不添加 connect_args"""
        from app.core.database import _get_engine_kwargs

        kwargs = _get_engine_kwargs("postgresql+asyncpg://localhost/db")
        assert "connect_args" not in kwargs

    def test_case_insensitive_sqlite_detection(self):
        """SQLite 检测大小写不敏感"""
        from app.core.database import _get_engine_kwargs

        kwargs = _get_engine_kwargs("SQLITE+aiosqlite:///test.db")
        assert "connect_args" in kwargs


class TestAsyncEngine:
    """async_engine 配置测试"""

    def test_engine_created(self):
        """引擎已创建"""
        from app.core.database import async_engine
        assert async_engine is not None

    def test_async_session_factory_created(self):
        """会话工厂已创建"""
        from app.core.database import AsyncSessionLocal
        assert AsyncSessionLocal is not None


class TestBase:
    """Base 声明基类测试"""

    def test_base_is_declarative(self):
        """Base 是 SQLAlchemy 声明基类"""
        from app.core.database import Base
        from sqlalchemy.orm import DeclarativeBase
        assert issubclass(Base, DeclarativeBase)


class TestGetDb:
    """get_db 依赖注入测试"""

    @pytest.mark.asyncio
    async def test_yields_session(self):
        """yield 一个 AsyncSession"""
        from app.core.database import get_db
        from sqlalchemy.ext.asyncio import AsyncSession

        gen = get_db()
        session = await gen.__anext__()
        assert session is not None
        # cleanup
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass
