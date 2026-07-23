"""
认证服务 单元测试
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone


def _make_mock_result(return_value):
    """构建 mock execute 结果链: db.execute() -> result.scalar_one_or_none()"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = return_value
    return mock_result


# ============================================================
# register_user
# ============================================================
class TestRegisterUser:
    """注册用户测试"""

    @pytest.mark.asyncio
    async def test_register_success(self):
        """注册成功"""
        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(None)  # 无重复

        from app.services.auth_service import register_user

        with patch("app.services.auth_service.hash_password", return_value="hashed_abc"):
            user = await register_user(mock_db, "newuser", "new@test.com", "pass123")

            assert user.username == "newuser"
            assert user.email == "new@test.com"
            assert user.hashed_password == "hashed_abc"
            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self):
        """重复用户名抛异常"""
        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(MagicMock())  # 用户名重复

        from app.services.auth_service import register_user

        with pytest.raises(ValueError, match="用户名已被注册"):
            await register_user(mock_db, "existinguser", "new@test.com", "pass123")

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self):
        """重复邮箱抛异常"""
        mock_db = AsyncMock()
        # 第一次查询用户名：无重复，第二次查询邮箱：有重复
        r1 = _make_mock_result(None)
        r2 = _make_mock_result(MagicMock())
        mock_db.execute.side_effect = [r1, r2]

        from app.services.auth_service import register_user

        with pytest.raises(ValueError, match="邮箱已被注册"):
            await register_user(mock_db, "newuser", "existing@test.com", "pass123")


# ============================================================
# login_user
# ============================================================
class TestLoginUser:
    """登录测试"""

    def _make_user(self):
        user = MagicMock()
        user.id = "user-123"
        user.username = "admin"
        user.email = "admin@test.com"
        user.is_admin = True
        user.is_active = True
        user.hashed_password = "hashed_pw"
        user.token_version = 0
        user.created_at = datetime.now(timezone.utc)
        return user

    @pytest.mark.asyncio
    async def test_login_success(self):
        """登录成功返回 token"""
        mock_db = AsyncMock()
        mock_user = self._make_user()
        mock_db.execute.return_value = _make_mock_result(mock_user)

        from app.services.auth_service import login_user

        with patch("app.services.auth_service.verify_password", return_value=True):
            with patch("app.services.auth_service.create_access_token", return_value="access-token"):
                with patch("app.services.auth_service.create_refresh_token", return_value="refresh-token"):
                    result = await login_user(mock_db, "admin", "correct_pass")

                    assert result["access_token"] == "access-token"
                    assert result["refresh_token"] == "refresh-token"
                    assert result["user"]["username"] == "admin"
                    assert result["user"]["is_admin"] is True

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        """密码错误抛异常"""
        mock_db = AsyncMock()
        mock_user = self._make_user()
        mock_db.execute.return_value = _make_mock_result(mock_user)

        from app.services.auth_service import login_user

        with patch("app.services.auth_service.verify_password", return_value=False):
            with pytest.raises(ValueError, match="用户名或密码错误"):
                await login_user(mock_db, "admin", "wrong_pass")

    @pytest.mark.asyncio
    async def test_login_user_not_found(self):
        """用户不存在抛异常"""
        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_mock_result(None)

        from app.services.auth_service import login_user

        with pytest.raises(ValueError, match="用户名或密码错误"):
            await login_user(mock_db, "nonexistent", "pass")

    @pytest.mark.asyncio
    async def test_login_disabled_user(self):
        """被禁用用户登录抛异常"""
        mock_db = AsyncMock()
        mock_user = self._make_user()
        mock_user.is_active = False
        mock_db.execute.return_value = _make_mock_result(mock_user)

        from app.services.auth_service import login_user

        with patch("app.services.auth_service.verify_password", return_value=True):
            with pytest.raises(ValueError, match="账户已被禁用"):
                await login_user(mock_db, "disabled", "pass")


# ============================================================
# refresh_access_token
# ============================================================
class TestRefreshAccessToken:
    """刷新 Token 测试"""

    @pytest.mark.asyncio
    async def test_refresh_success(self):
        """刷新成功"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.is_active = True
        mock_user.token_version = 0
        mock_db.execute.return_value = _make_mock_result(mock_user)

        from app.services.auth_service import refresh_access_token

        mock_payload = {"sub": "user-123", "type": "refresh", "jti": "xxx"}
        with patch("app.services.auth_service.decode_token", return_value=mock_payload):
            with patch("app.services.auth_service.create_access_token", return_value="new-access-token"):
                with patch("app.services.auth_service.redis_client", None):
                    result = await refresh_access_token("valid_refresh", mock_db)
                    assert result == "new-access-token"

    @pytest.mark.asyncio
    async def test_refresh_invalid_token_type(self):
        """Token type 不是 refresh 抛异常"""
        mock_db = AsyncMock()
        mock_payload = {"sub": "user-123", "type": "access"}

        from app.services.auth_service import refresh_access_token

        with patch("app.services.auth_service.decode_token", return_value=mock_payload):
            with pytest.raises(ValueError, match="无效的 Refresh Token"):
                await refresh_access_token("access_token", mock_db)

    @pytest.mark.asyncio
    async def test_refresh_null_payload(self):
        """Token 解析失败"""
        mock_db = AsyncMock()

        from app.services.auth_service import refresh_access_token

        with patch("app.services.auth_service.decode_token", return_value=None):
            with pytest.raises(ValueError, match="无效的 Refresh Token"):
                await refresh_access_token("invalid", mock_db)


# ============================================================
# change_user_password
# ============================================================
class TestChangeUserPassword:
    """修改密码测试"""

    @pytest.mark.asyncio
    async def test_change_password_success(self):
        """修改密码成功"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.hashed_password = "old_hashed"
        mock_user.token_version = 3

        from app.services.auth_service import change_user_password

        with patch("app.services.auth_service.verify_password", return_value=True):
            with patch("app.services.auth_service.hash_password", return_value="new_hashed"):
                with patch("app.services.auth_service.redis_client", None):
                    await change_user_password(mock_db, mock_user, "old_pass", "new_pass")

                    assert mock_user.hashed_password == "new_hashed"
                    assert mock_user.token_version == 4  # 递增

    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self):
        """旧密码错误"""
        mock_db = AsyncMock()
        mock_user = MagicMock()

        from app.services.auth_service import change_user_password

        with patch("app.services.auth_service.verify_password", return_value=False):
            with pytest.raises(ValueError, match="旧密码不正确"):
                await change_user_password(mock_db, mock_user, "wrong_old", "new_pass")
