"""
API 依赖注入 单元测试
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


def _make_mock_result(return_value):
    """构建 mock execute 结果链"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = return_value
    return mock_result


class TestGetCurrentUser:
    """get_current_user 依赖测试"""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        """有效 token 返回用户"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.is_active = True
        mock_user.token_version = 0
        mock_db.execute.return_value = _make_mock_result(mock_user)

        from app.api.deps import get_current_user
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )
        mock_payload = {"sub": "user-123", "type": "access", "token_version": 0}

        with patch("app.api.deps.decode_token", return_value=mock_payload):
            result = await get_current_user(mock_credentials, mock_db)
            assert result is mock_user

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        """无效 token 抛出 401"""
        mock_db = AsyncMock()
        from app.api.deps import get_current_user
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        with patch("app.api.deps.decode_token", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_token_type_raises_401(self):
        """Token type 不是 access 抛出 401"""
        mock_db = AsyncMock()
        from app.api.deps import get_current_user
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="refresh_token"
        )
        mock_payload = {"sub": "user-123", "type": "refresh"}

        with patch("app.api.deps.decode_token", return_value=mock_payload):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_found_raises_401(self):
        """用户不存在抛出 401"""
        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(None)

        from app.api.deps import get_current_user
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )
        mock_payload = {"sub": "user-123", "type": "access", "token_version": 0}

        with patch("app.api.deps.decode_token", return_value=mock_payload):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db)
            assert exc_info.value.status_code == 401
            assert "用户不存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_disabled_user_raises_403(self):
        """被禁用用户抛出 403"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.is_active = False
        mock_db.execute.return_value = _make_mock_result(mock_user)

        from app.api.deps import get_current_user
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )
        mock_payload = {"sub": "user-123", "type": "access", "token_version": 0}

        with patch("app.api.deps.decode_token", return_value=mock_payload):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_token_version_mismatch_raises_401(self):
        """token_version 不匹配抛出 401"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.token_version = 5
        mock_db.execute.return_value = _make_mock_result(mock_user)

        from app.api.deps import get_current_user
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="old_token"
        )
        mock_payload = {"sub": "user-123", "type": "access", "token_version": 3}

        with patch("app.api.deps.decode_token", return_value=mock_payload):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db)
            assert exc_info.value.status_code == 401
            assert "Token 已失效" in exc_info.value.detail


class TestGetAdminUser:
    """get_admin_user 依赖测试"""

    @pytest.mark.asyncio
    async def test_admin_user_passes(self):
        """管理员通过"""
        mock_user = MagicMock()
        mock_user.is_admin = True

        from app.api.deps import get_admin_user
        result = await get_admin_user(mock_user)
        assert result is mock_user

    @pytest.mark.asyncio
    async def test_non_admin_raises_403(self):
        """非管理员抛出 403"""
        mock_user = MagicMock()
        mock_user.is_admin = False

        from app.api.deps import get_admin_user
        with pytest.raises(HTTPException) as exc_info:
            await get_admin_user(mock_user)
        assert exc_info.value.status_code == 403
