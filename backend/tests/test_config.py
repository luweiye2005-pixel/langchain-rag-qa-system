"""
配置管理 单元测试
"""
import pytest


class TestSettings:
    """Settings 配置类测试"""

    def test_settings_instance_exists(self):
        """settings 实例存在"""
        from app.config import settings
        assert settings is not None

    def test_default_database_url(self):
        """默认数据库 URL"""
        from app.config import settings
        assert "postgresql" in settings.DATABASE_URL or "sqlite" in settings.DATABASE_URL

    def test_tongyi_model_default(self):
        """默认通义千问模型"""
        from app.config import settings
        assert settings.TONGYI_MODEL == "qwen-max"

    def test_jwt_algorithm(self):
        """JWT 算法配置"""
        from app.config import settings
        assert settings.JWT_ALGORITHM == "HS256"

    def test_access_token_expire(self):
        """Access Token 过期时间"""
        from app.config import settings
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30

    def test_refresh_token_expire(self):
        """Refresh Token 过期时间"""
        from app.config import settings
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7

    def test_chroma_collection_name(self):
        """Chroma collection 名称"""
        from app.config import settings
        assert settings.CHROMA_COLLECTION_NAME == "knowledge_base"

    def test_upload_limit(self):
        """上传大小限制"""
        from app.config import settings
        assert settings.MAX_UPLOAD_SIZE_MB == 50

    def test_cors_origins_is_list(self):
        """CORS origins 是列表"""
        from app.config import settings
        assert isinstance(settings.CORS_ORIGINS, list)
        assert len(settings.CORS_ORIGINS) > 0

    def test_case_sensitive_config(self):
        """配置大小写敏感"""
        from app.config import settings
        # 确保 model_config 中 case_sensitive=True
        assert settings.model_config.get("case_sensitive") is True

    def test_env_file_config(self):
        """环境文件配置"""
        from app.config import settings
        assert settings.model_config.get("env_file") == ".env"

    def test_rate_limit_chat(self):
        """聊天限流配置"""
        from app.config import settings
        assert settings.RATE_LIMIT_CHAT_PER_MINUTE == 20

    def test_rate_limit_login(self):
        """登录限流配置"""
        from app.config import settings
        assert settings.RATE_LIMIT_LOGIN_PER_MINUTE == 5
