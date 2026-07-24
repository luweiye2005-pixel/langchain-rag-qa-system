"""固定窗口限流：优先 Redis，不可用时降级为进程内计数。"""
import threading
import time

from fastapi import HTTPException, Request, status

from app.core.redis import get_redis

# 进程内降级限流（单进程开发场景；多 worker 下各进程独立计数）
_local_lock = threading.Lock()
_local_counters: dict[str, tuple[int, float]] = {}


def _enforce_local_rate_limit(key: str, limit: int) -> None:
    now = time.monotonic()
    with _local_lock:
        count, window_start = _local_counters.get(key, (0, now))
        if now - window_start >= 60:
            count, window_start = 0, now
        count += 1
        _local_counters[key] = (count, window_start)
        if count > limit:
            retry_after = max(int(60 - (now - window_start)), 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后重试",
                headers={"Retry-After": str(retry_after)},
            )


async def enforce_rate_limit(
    request: Request, scope: str, identity: str, limit: int
) -> None:
    """按分钟限制请求；Redis 不可用时降级为本地计数，避免阻断登录。"""
    client_ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:{scope}:{client_ip}:{identity}"

    redis = await get_redis()
    if redis is None:
        _enforce_local_rate_limit(key, limit)
        return

    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        if count > limit:
            ttl = await redis.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后重试",
                headers={"Retry-After": str(max(ttl, 1))},
            )
    except HTTPException:
        raise
    except Exception:
        # Redis 运行中途异常时同样降级，保证开发环境可登录
        _enforce_local_rate_limit(key, limit)
