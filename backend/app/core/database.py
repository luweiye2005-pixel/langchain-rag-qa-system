"""
数据库连接管理
支持 PostgreSQL (生产) 和 SQLite (本地开发)
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings
from loguru import logger


def _get_engine_kwargs(db_url: str) -> dict:
    """根据数据库类型返回不同的引擎参数"""
    is_sqlite = "sqlite" in db_url.lower()
    kwargs = {"echo": False}
    if is_sqlite:
        # timeout: 等待写锁的秒数；WAL 在连接建立后启用
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    else:
        kwargs.update({
            "pool_size": 20, "max_overflow": 10,
            "pool_recycle": 3600, "pool_pre_ping": True,
        })
    return kwargs


engine_kwargs = _get_engine_kwargs(settings.DATABASE_URL)
async_engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def configure_sqlite() -> None:
    """启用 SQLite WAL，降低文档后台线程与 API 的读写互锁。"""
    if "sqlite" not in settings.DATABASE_URL.lower():
        return
    from sqlalchemy import text

    async with async_engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA busy_timeout=30000"))


class Base(DeclarativeBase):
    """SQLAlchemy 基类"""
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI 依赖注入：获取数据库会话

    注意：调用此依赖的 handler 必须在写操作后显式调用 await db.commit()，
    因为 FastAPI 的 yield 清理在响应发送后才执行。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
