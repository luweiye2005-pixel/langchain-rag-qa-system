"""
Redis 连接管理 单元测试
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestInitRedis:
    """init_redis 函数测试"""

    @pytest.mark.asyncio
    async def test_init_redis_success(self):
        """Redis 初始化成功"""
        with patch("app.core.redis.aioredis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(return_value=True)
            mock_redis.from_url.return_value = mock_client

            from app.core.redis import init_redis, redis_client as rc

            await init_redis()

            mock_redis.from_url.assert_called_once()
            mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_redis_failure_graceful(self):
        """Redis 初始化失败不抛异常"""
        with patch("app.core.redis.aioredis") as mock_redis:
            mock_redis.from_url.side_effect = ConnectionError("Connection refused")
            from app.core.redis import init_redis

            # 不应抛出异常
            await init_redis()

    @pytest.mark.asyncio
    async def test_init_redis_sets_global_to_none_on_failure(self):
        """Redis 初始化失败时全局变量设为 None"""
        with patch("app.core.redis.aioredis") as mock_redis:
            mock_redis.from_url.side_effect = Exception("Boom")
            from app.core.redis import init_redis

            await init_redis()
            from app.core.redis import redis_client
            assert redis_client is None


class TestCloseRedis:
    """close_redis 函数测试"""

    @pytest.mark.asyncio
    async def test_close_redis_with_client(self):
        """有关闭连接时正常 close"""
        mock_client = AsyncMock()
        with patch("app.core.redis.redis_client", mock_client):
            from app.core.redis import close_redis

            await close_redis()
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_redis_without_client(self):
        """无连接时不报错"""
        with patch("app.core.redis.redis_client", None):
            from app.core.redis import close_redis

            # 不应抛出异常
            await close_redis()


class TestGetRedis:
    """get_redis 函数测试"""

    @pytest.mark.asyncio
    async def test_returns_client(self):
        """返回 Redis 客户端"""
        mock_client = MagicMock()
        with patch("app.core.redis.redis_client", mock_client):
            from app.core.redis import get_redis
            result = await get_redis()
            assert result is mock_client

    @pytest.mark.asyncio
    async def test_returns_none_when_no_client(self):
        """无客户端时返回 None"""
        with patch("app.core.redis.redis_client", None):
            from app.core.redis import get_redis
            result = await get_redis()
            assert result is None
