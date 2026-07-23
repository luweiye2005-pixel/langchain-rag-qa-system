"""
security 模块单元测试

测试函数: hash_password, verify_password, create_access_token,
          create_refresh_token, decode_token
"""
import pytest
from datetime import datetime, timezone
from jose import jwt

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.config import settings


# ============================================================
# hash_password
# ============================================================
class TestHashPassword:
    """密码哈希函数测试"""

    def test_returns_different_from_input(self):
        """哈希结果不应等于明文"""
        result = hash_password("123456")
        assert result != "123456"

    def test_returns_bcrypt_format(self):
        """哈希结果应为 bcrypt 格式 ($2b$ 或 $2a$)"""
        result = hash_password("hello")
        assert result.startswith("$2")

    def test_different_passwords_produce_different_hashes(self):
        """不同密码产生不同哈希"""
        h1 = hash_password("password1")
        h2 = hash_password("password2")
        assert h1 != h2

    def test_same_password_produces_different_hash(self):
        """相同密码每次哈希结果不同 (salt)"""
        h1 = hash_password("same_pass")
        h2 = hash_password("same_pass")
        assert h1 != h2

    def test_empty_password(self):
        """空密码也能哈希"""
        result = hash_password("")
        assert result
        assert len(result) > 0

    def test_long_password(self):
        """超长密码"""
        long_pw = "a" * 1000
        result = hash_password(long_pw)
        assert result.startswith("$2")

    def test_unicode_password(self):
        """Unicode 密码（中文等）"""
        result = hash_password("密码123!@#")
        assert result
        assert isinstance(result, str)


# ============================================================
# verify_password
# ============================================================
class TestVerifyPassword:
    """密码验证函数测试"""

    def test_correct_password_returns_true(self):
        """正确密码返回 True"""
        hashed = hash_password("my_secret")
        assert verify_password("my_secret", hashed) is True

    def test_wrong_password_returns_false(self):
        """错误密码返回 False"""
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_empty_password(self):
        """空密码验证"""
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("x", hashed) is False

    def test_case_sensitive(self):
        """密码大小写敏感"""
        hashed = hash_password("Password")
        assert verify_password("password", hashed) is False
        assert verify_password("Password", hashed) is True

    def test_special_characters(self):
        """特殊字符密码"""
        pw = "p@$$w0rd!汉字"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True


# ============================================================
# create_access_token
# ============================================================
class TestCreateAccessToken:
    """Access Token 创建测试"""

    def test_returns_string(self):
        """返回值为字符串"""
        token = create_access_token("user-001")
        assert isinstance(token, str)
        assert len(token) > 10

    def test_token_can_be_decoded(self):
        """生成的 token 可以被解码"""
        token = create_access_token("user-001")
        payload = decode_token(token)
        assert payload is not None

    def test_token_contains_user_id(self):
        """payload 中包含 user_id (sub)"""
        token = create_access_token("user-abc-123")
        payload = decode_token(token)
        assert payload["sub"] == "user-abc-123"

    def test_token_type_is_access(self):
        """token type 为 'access'"""
        token = create_access_token("user-001")
        payload = decode_token(token)
        assert payload["type"] == "access"

    def test_token_has_expiration(self):
        """token 包含过期时间"""
        token = create_access_token("user-001")
        payload = decode_token(token)
        assert "exp" in payload
        # 过期时间应在未来
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert exp > now

    def test_default_token_version_is_zero(self):
        """默认 token_version 为 0"""
        token = create_access_token("user-001")
        payload = decode_token(token)
        assert payload["token_version"] == 0

    def test_custom_token_version(self):
        """自定义 token_version"""
        token = create_access_token("user-001", token_version=5)
        payload = decode_token(token)
        assert payload["token_version"] == 5

    def test_different_users_produce_different_tokens(self):
        """不同用户生成不同 token"""
        t1 = create_access_token("user-A")
        t2 = create_access_token("user-B")
        assert t1 != t2

    def test_token_expiry_matches_config(self):
        """过期时间符合配置 (30分钟)"""
        token = create_access_token("user-001")
        payload = decode_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        delta_minutes = (exp - now).total_seconds() / 60
        # 接近 30 分钟 (允许 1 分钟误差)
        assert 29 <= delta_minutes <= 31


# ============================================================
# create_refresh_token
# ============================================================
class TestCreateRefreshToken:
    """Refresh Token 创建测试"""

    def test_returns_string(self):
        """返回值为字符串"""
        token = create_refresh_token("user-001")
        assert isinstance(token, str)
        assert len(token) > 10

    def test_token_can_be_decoded(self):
        """生成的 token 可以被解码"""
        token = create_refresh_token("user-001")
        payload = decode_token(token)
        assert payload is not None

    def test_token_type_is_refresh(self):
        """token type 为 'refresh'"""
        token = create_refresh_token("user-001")
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_no_token_version_in_refresh(self):
        """Refresh token 不包含 token_version"""
        token = create_refresh_token("user-001")
        payload = decode_token(token)
        assert "token_version" not in payload

    def test_token_has_expiration(self):
        """包含过期时间"""
        token = create_refresh_token("user-001")
        payload = decode_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert exp > now

    def test_token_expiry_is_7_days(self):
        """过期时间约为 7 天"""
        token = create_refresh_token("user-001")
        payload = decode_token(token)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        delta_days = (exp - now).total_seconds() / 86400
        assert 6.9 <= delta_days <= 7.1

    def test_different_users_produce_different_tokens(self):
        """不同用户生成不同 token"""
        t1 = create_refresh_token("user-A")
        t2 = create_refresh_token("user-B")
        assert t1 != t2


# ============================================================
# decode_token
# ============================================================
class TestDecodeToken:
    """Token 解码测试"""

    def test_valid_token_returns_dict(self):
        """有效 token 返回 dict"""
        token = create_access_token("user-001")
        payload = decode_token(token)
        assert isinstance(payload, dict)

    def test_valid_token_has_sub(self):
        """有效 token 包含 sub 字段"""
        token = create_access_token("user-001")
        payload = decode_token(token)
        assert payload["sub"] == "user-001"

    def test_empty_string_returns_none(self):
        """空字符串返回 None"""
        assert decode_token("") is None

    def test_invalid_token_returns_none(self):
        """无效 token 返回 None"""
        assert decode_token("not.a.valid.token") is None

    def test_random_string_returns_none(self):
        """随机字符串返回 None"""
        assert decode_token("random_garbage_string") is None

    def test_none_token_raises(self):
        """None 作为 token 会抛出异常（JWT 库行为）"""
        with pytest.raises(Exception):
            decode_token(None)

    def test_tampered_token_returns_none(self):
        """被篡改的 token 返回 None"""
        token = create_access_token("user-001")
        # 修改 payload 部分但不重新签名
        parts = token.split(".")
        tampered_payload = "eyJzdWIiOiJoYWNrZWQifQ"  # {"sub": "hacked"}
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"
        assert decode_token(tampered_token) is None

    def test_token_with_wrong_secret_returns_none(self):
        """用错误密钥签名的 token 返回 None"""
        wrong_token = jwt.encode(
            {"sub": "user-001", "type": "access"},
            "wrong-secret-key",
            algorithm=settings.JWT_ALGORITHM,
        )
        assert decode_token(wrong_token) is None

    def test_expired_token_returns_none(self):
        """过期 token 返回 None"""
        from datetime import timedelta
        expire = datetime.now(timezone.utc) - timedelta(minutes=1)
        expired_token = jwt.encode(
            {"sub": "user-001", "type": "access", "exp": expire},
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )
        assert decode_token(expired_token) is None
