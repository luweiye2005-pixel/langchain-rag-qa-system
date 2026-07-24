"""
关键 API 集成测试：auth / chat / knowledge / voice
外部 LLM、ASR、TTS、文档处理均 Mock。
"""
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_login_and_refresh_token_rotation(client, admin_headers):
    """登录成功后 refresh 会轮换 refresh_token，旧 token 失效。"""
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Admin@123456"},
    )
    assert login.status_code == 200
    body = login.json()
    old_refresh = body["refresh_token"]
    assert body["access_token"]
    assert body["user"]["is_admin"] is True

    refreshed = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["refresh_token"]
    assert new_refresh != old_refresh

    reused = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert reused.status_code == 401


@pytest.mark.asyncio
async def test_chat_sse_returns_tokens_and_done(client, admin_headers):
    """聊天 SSE 在 mock LLM 流时返回 token/done。"""

    async def fake_stream(*, question, conversation_id, history=None):
        yield {"type": "token", "content": "你好"}
        yield {"type": "token", "content": "世界"}
        yield {
            "type": "sources",
            "documents": [
                {
                    "doc_id": "d1",
                    "doc_name": "a.txt",
                    "chunk_id": "0",
                    "content_snippet": "片段",
                    "score": 0.1,
                    "citation_index": 1,
                }
            ],
        }
        yield {"type": "done"}

    with patch("app.api.v1.chat.get_chat_service") as mock_get:
        service = MagicMock()
        service.stream_chat = fake_stream
        mock_get.return_value = service

        resp = await client.post(
            "/api/v1/chat",
            headers=admin_headers,
            json={"message": "测试问题", "conversation_id": None},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        text = resp.text
        assert '"type": "token"' in text or '"type":"token"' in text
        assert "你好" in text
        assert '"type": "done"' in text or '"type":"done"' in text


@pytest.mark.asyncio
async def test_knowledge_upload_lists_document(client, admin_headers):
    """管理员上传文本后可在列表中看到文档。"""
    import uuid

    unique = f"hello knowledge base {uuid.uuid4()}"
    with patch("app.api.v1.knowledge._start_processing") as mock_start:
        files = {
            "file": ("demo.txt", io.BytesIO(unique.encode("utf-8")), "text/plain"),
        }
        upload = await client.post(
            "/api/v1/knowledge/upload",
            headers=admin_headers,
            files=files,
        )
        assert upload.status_code in (200, 201), upload.text
        data = upload.json()
        assert data["filename"] == "demo.txt"
        assert data["status"] == "pending"
        mock_start.assert_called_once()

        listed = await client.get(
            "/api/v1/knowledge/documents?size=100",
            headers=admin_headers,
        )
        assert listed.status_code == 200
        docs = listed.json()["documents"]
        assert any(d["id"] == data["id"] for d in docs)


@pytest.mark.asyncio
async def test_voice_asr_and_tts_and_voices(client, admin_headers):
    """语音音色列表、ASR、TTS 接口可用（底层 SDK Mock）。"""
    voices = await client.get("/api/v1/voice/voices", headers=admin_headers)
    assert voices.status_code == 200
    payload = voices.json()
    assert len(payload["voices"]) >= 1
    assert payload["current"]

    with patch("app.api.v1.voice.recognize_audio", return_value="语音问题"):
        with patch("app.api.v1.voice.asyncio.to_thread", new_callable=AsyncMock) as to_thread:
            to_thread.return_value = "语音问题"
            asr = await client.post(
                "/api/v1/voice/asr",
                headers=admin_headers,
                files={"audio": ("rec.wav", io.BytesIO(b"RIFF....wav"), "audio/wav")},
            )
            assert asr.status_code == 200, asr.text
            assert asr.json()["text"] == "语音问题"

    with patch("app.api.v1.voice.asyncio.to_thread", new_callable=AsyncMock) as to_thread:
        to_thread.return_value = b"RIFFWAVDATA"
        tts = await client.post(
            "/api/v1/voice/tts",
            headers=admin_headers,
            json={"text": "你好"},
        )
        assert tts.status_code == 200, tts.text
        assert tts.headers["content-type"].startswith("audio/wav")
        assert tts.content == b"RIFFWAVDATA"


@pytest.mark.asyncio
async def test_login_to_chat_minimal_flow(client, admin_headers):
    """最小链路：登录后发送问题，收到 token 与 done。"""

    async def fake_stream(*, question, conversation_id, history=None):
        assert question == "知识库里有什么"
        yield {"type": "token", "content": "有商品资料"}
        yield {"type": "done"}

    with patch("app.api.v1.chat.get_chat_service") as mock_get:
        service = MagicMock()
        service.stream_chat = fake_stream
        mock_get.return_value = service

        resp = await client.post(
            "/api/v1/chat",
            headers=admin_headers,
            json={"message": "知识库里有什么"},
        )
        assert resp.status_code == 200
        assert "有商品资料" in resp.text
        assert "done" in resp.text
