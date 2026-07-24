"""
pytest 公共 fixture：环境、数据库表、HTTP 客户端。
注意：环境变量需在导入 app 之前设置。
"""
import os

# 在导入应用模块前确保关键配置可用（本地 .env 已存在时不会覆盖）
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./pytest_integration.db")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-at-least-32-chars!!")
os.environ.setdefault("OPENAI_API_KEY", "test-dashscope-key")
os.environ.setdefault("INITIAL_ADMIN_USERNAME", "admin")
os.environ.setdefault("INITIAL_ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "Admin@123456")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.rate_limit import _local_counters


@pytest.fixture(autouse=True)
def _clear_rate_limit_counters():
    """每个测试前清空进程内限流计数，避免互相干扰。"""
    _local_counters.clear()
    yield
    _local_counters.clear()


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    """带 lifespan 的 AsyncClient；上传目录指向临时目录。"""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr("app.config.settings.UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr("app.api.v1.knowledge.settings.UPLOAD_DIR", str(upload_dir))

    from app.core.database import Base, async_engine
    import app.models  # noqa: F401
    from app.main import app

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_headers(client):
    """确保管理员账号可用并返回 Authorization 头。"""
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()
        if user is None:
            db.add(
                User(
                    username="admin",
                    email="admin@test.local",
                    hashed_password=hash_password("Admin@123456"),
                    is_admin=True,
                    is_active=True,
                )
            )
        else:
            user.hashed_password = hash_password("Admin@123456")
            user.is_admin = True
            user.is_active = True
            user.token_version = getattr(user, "token_version", 0) or 0
        await db.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Admin@123456"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
