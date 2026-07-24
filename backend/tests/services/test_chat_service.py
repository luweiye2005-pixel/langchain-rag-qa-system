from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.schemas.chat import ChatHistoryMessage
from app.services.chat_service import ChatService


class TestChatService:
    @pytest.mark.asyncio
    async def test_uses_history_and_assigns_continuous_citations(self):
        service = ChatService()
        relevant_first = SimpleNamespace(
            page_content="第一个片段",
            metadata={"filename": "first.pdf", "document_id": "doc-1", "chunk_index": "0"},
        )
        irrelevant = SimpleNamespace(
            page_content="无关片段",
            metadata={"filename": "ignored.pdf"},
        )
        relevant_second = SimpleNamespace(
            page_content="第二个片段",
            metadata={"filename": "second.pdf", "document_id": "doc-2", "chunk_index": "1"},
        )
        service._vector_store = MagicMock()
        service._vector_store.similarity_search_with_score.return_value = [
            (relevant_first, 0.1),
            (irrelevant, 0.9),
            (relevant_second, 0.2),
        ]

        streamed_messages = []

        async def astream(messages):
            streamed_messages.extend(messages)
            yield SimpleNamespace(content="回答")

        service._llm = MagicMock()
        service._llm.astream.side_effect = astream

        events = [
            event
            async for event in service.stream_chat(
                question="当前问题",
                conversation_id="conversation-1",
                history=[
                    ChatHistoryMessage(role="user", content="历史问题"),
                    ChatHistoryMessage(role="assistant", content="历史回答"),
                ],
            )
        ]

        assert events[0] == {"type": "token", "content": "回答"}
        sources = events[1]["documents"]
        assert [source["citation_index"] for source in sources] == [1, 2]
        assert [source["doc_name"] for source in sources] == ["first.pdf", "second.pdf"]
        assert [message.content for message in streamed_messages[1:-1]] == ["历史问题", "历史回答"]
