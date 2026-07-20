"""
认证服务
"""
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.core.database import AsyncSessionLocal
from app.core.redis import redis_client
from loguru import logger


async def seed_admin_user():
    """初始化管理员用户（admin/123456）"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()

        if admin is None:
            admin = User(
                username="admin",
                email="admin@example.com",
                hashed_password=hash_password("123456"),
                is_admin=True,
            )
            db.add(admin)
            await db.commit()
            logger.info("admin user created: admin/123456")


async def register_user(
    db: AsyncSession, username: str, email: str, password: str
) -> User:
    """注册新用户"""
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise ValueError("用户名已被注册")

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise ValueError("邮箱已被注册")

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(user)
    await db.flush()
    await db.commit()
    return user


async def login_user(db: AsyncSession, username: str, password: str) -> dict:
    """用户登录"""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.hashed_password):
        raise ValueError("用户名或密码错误")

    if not user.is_active:
        raise ValueError("账户已被禁用")

    # Update last login time
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()

    # Generate tokens
    access_token = create_access_token(user.id, user.token_version)
    refresh_token = create_refresh_token(user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


async def refresh_access_token(refresh_token_str: str, db: AsyncSession) -> str:
    """使用 refresh token 刷新 access token"""
    payload = decode_token(refresh_token_str)

    if payload is None or payload.get("type") != "refresh":
        raise ValueError("无效的 Refresh Token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise ValueError("用户不存在或已被禁用")

    # 检查 refresh token 是否在黑名单中
    if redis_client:
        jti = payload.get("jti", "")
        if await redis_client.exists(f"blacklist:refresh:{jti}"):
            raise ValueError("Refresh Token 已被吊销")

    return create_access_token(user.id, user.token_version)


async def change_user_password(
    db: AsyncSession, user: User, old_password: str, new_password: str
) -> None:
    """修改密码"""
    if not verify_password(old_password, user.hashed_password):
        raise ValueError("旧密码不正确")

    user.hashed_password = hash_password(new_password)
    user.token_version += 1  # 递增 token_version 使所有旧 token 失效
    await db.flush()
    await db.commit()

    # 将当前 refresh token 加入黑名单
    if redis_client:
        # 这里需要前端传 refresh_token，简化处理：只依赖 token_version
        pass
