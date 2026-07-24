"""
认证相关 API
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    LoginResponse,
    RefreshRequest,
    ChangePasswordRequest,
)
from app.services.auth_service import (
    register_user,
    login_user,
    refresh_access_token,
    change_user_password,
)
from app.config import settings
from app.core.rate_limit import enforce_rate_limit

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户注册"""
    try:
        user = await register_user(db, request.username, request.email, request.password)
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """用户登录"""
    await enforce_rate_limit(
        http_request, "login", request.username, settings.RATE_LIMIT_LOGIN_PER_MINUTE
    )
    try:
        result = await login_user(db, request.username, request.password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """刷新 Access Token"""
    try:
        return TokenResponse(**(await refresh_access_token(request.refresh_token, db)))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.put("/password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    try:
        await change_user_password(
            db, current_user, request.old_password, request.new_password
        )
        return {"message": "密码修改成功，请重新登录"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
