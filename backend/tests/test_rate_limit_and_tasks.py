"""
限流与文档处理 revision 竞态测试
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.rate_limit import _enforce_local_rate_limit, _local_counters, enforce_rate_limit


class TestLocalRateLimit:
    def test_allows_within_limit(self):
        _local_counters.clear()
        for _ in range(3):
            _enforce_local_rate_limit("k1", limit=3)

    def test_blocks_when_exceeded(self):
        _local_counters.clear()
        for _ in range(2):
            _enforce_local_rate_limit("k2", limit=2)
        with pytest.raises(HTTPException) as exc:
            _enforce_local_rate_limit("k2", limit=2)
        assert exc.value.status_code == 429
        assert "Retry-After" in exc.value.headers


@pytest.mark.asyncio
async def test_enforce_rate_limit_falls_back_without_redis():
    _local_counters.clear()
    request = MagicMock()
    request.client.host = "127.0.0.1"
    with patch("app.core.rate_limit.get_redis", AsyncMock(return_value=None)):
        await enforce_rate_limit(request, "login", "admin", limit=5)
        # 不应抛错
        assert any(k.startswith("rate_limit:login:") for k in _local_counters)


def test_start_processing_uses_thread_when_celery_disabled():
    """默认 USE_CELERY=false 时直接后台线程，绝不调用 Celery.delay。"""
    from app.api.v1 import knowledge as knowledge_api

    started = []

    class FakeThread:
        def __init__(self, target=None, args=(), kwargs=None, daemon=None, **_):
            self.target = target

        def start(self):
            started.append(self.target)

    with patch("app.api.v1.knowledge.settings.USE_CELERY", False), patch(
        "app.api.v1.knowledge.threading.Thread", FakeThread
    ):
        knowledge_api._start_processing("doc-x", 1)

    assert len(started) == 1


@pytest.mark.asyncio
async def test_process_document_skips_stale_revision():
    """revision 不匹配或状态非 pending 时跳过，避免旧任务写回。"""
    from app.tasks.document_tasks import _process_document_impl

    doc = MagicMock()
    doc.id = "doc-1"
    doc.revision = 2
    doc.status = "pending"
    doc.filename = "a.txt"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = doc

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None

    with patch("app.tasks.document_tasks.AsyncSessionLocal", return_value=mock_db):
        with patch(
            "app.tasks.document_tasks.ensure_document_sqlite_schema",
            AsyncMock(),
        ):
            result = await _process_document_impl("doc-1", revision=1)

    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_process_document_skips_when_claim_fails():
    """原子认领失败（已被其他 worker 领取）时跳过。"""
    from app.tasks.document_tasks import _process_document_impl

    doc = MagicMock()
    doc.id = "doc-2"
    doc.revision = 1
    doc.status = "pending"
    doc.filename = "b.txt"

    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = doc
    claim_result = MagicMock()
    claim_result.rowcount = 0

    mock_db = AsyncMock()
    mock_db.execute.side_effect = [select_result, claim_result]
    mock_db.__aenter__.return_value = mock_db
    mock_db.__aexit__.return_value = None

    with patch("app.tasks.document_tasks.AsyncSessionLocal", return_value=mock_db):
        with patch(
            "app.tasks.document_tasks.ensure_document_sqlite_schema",
            AsyncMock(),
        ):
            result = await _process_document_impl("doc-2", revision=1)

    assert result["status"] == "skipped"
