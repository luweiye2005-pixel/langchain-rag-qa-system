"""
Redis 连接管理
"""
import redis.asyncio as aioredis
from app.config import settings
from loguru import logger

# 全局 Redis 实例
redis_client: aioredis.Redis | None = None


async def init_redis():
    """初始化 Redis 连接"""
    global redis_client
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
            socket_keepalive=True,
            protocol=2,  # RESP2 兼容 Redis 5.x
        )
        await redis_client.ping()
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}, continuing without Redis")
        redis_client = None


async def close_redis():
    """关闭 Redis 连接"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def get_redis() -> aioredis.Redis | None:
    """获取 Redis 客户端"""
    return redis_client
