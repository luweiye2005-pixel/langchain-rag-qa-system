"""
认证服务
"""
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.core.database import AsyncSessionLocal
from app.core.redis import redis_client
from app.config import settings
from loguru import logger


async def seed_admin_user():
    """仅在显式配置初始管理员凭据时创建管理员。"""
    if not all(
        [
            settings.INITIAL_ADMIN_USERNAME,
            settings.INITIAL_ADMIN_EMAIL,
            settings.INITIAL_ADMIN_PASSWORD,
        ]
    ):
        logger.info("Initial admin credentials are not configured; skipping seed")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == settings.INITIAL_ADMIN_USERNAME)
        )
        admin = result.scalar_one_or_none()

        if admin is None:
            admin = User(
                username=settings.INITIAL_ADMIN_USERNAME,
                email=settings.INITIAL_ADMIN_EMAIL,
                hashed_password=hash_password(settings.INITIAL_ADMIN_PASSWORD),
                is_admin=True,
            )
            db.add(admin)
            await db.commit()
            logger.info("Default admin user seeded successfully")


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
    try:
        await db.flush()
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("用户名或邮箱已被注册")
    return user


async def _issue_tokens(db: AsyncSession, user: User) -> tuple[str, str]:
    """签发 Access/Refresh Token，并记录一次性 Refresh Token。"""
    access_token = create_access_token(user.id, user.token_version)
    refresh_token = create_refresh_token(user.id, user.token_version)
    payload = decode_token(refresh_token)
    assert payload is not None  # 本服务刚签发的 JWT 必须可解析
    db.add(
        RefreshToken(
            jti=payload["jti"],
            user_id=user.id,
            token_version=user.token_version,
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
    )
    await db.commit()
    return access_token, refresh_token


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
    access_token, refresh_token = await _issue_tokens(db, user)

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


async def refresh_access_token(refresh_token_str: str, db: AsyncSession) -> dict:
    """原子消费 Refresh Token 并轮换为新的 Token 对。"""
    payload = decode_token(refresh_token_str)

    if payload is None or payload.get("type") != "refresh":
        raise ValueError("无效的 Refresh Token")

    user_id, jti = payload.get("sub"), payload.get("jti")
    token_version = payload.get("token_version")
    if not user_id or not jti or token_version is None:
        raise ValueError("无效的 Refresh Token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise ValueError("用户不存在或已被禁用")

    if token_version != user.token_version:
        raise ValueError("Refresh Token 已失效")

    consumed = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.jti == jti,
            RefreshToken.user_id == user.id,
            RefreshToken.token_version == user.token_version,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    if consumed.rowcount != 1:
        await db.rollback()
        raise ValueError("Refresh Token 已被吊销或已使用")

    return dict(zip(("access_token", "refresh_token"), await _issue_tokens(db, user)))


async def change_user_password(
    db: AsyncSession, user: User, old_password: str, new_password: str
) -> None:
    """修改密码"""
    if not verify_password(old_password, user.hashed_password):
        raise ValueError("旧密码不正确")

    user.hashed_password = hash_password(new_password)
    user.token_version += 1  # 递增 token_version 使所有旧 token 失效
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()
