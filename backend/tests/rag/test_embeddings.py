"""
Embedding 模型管理 单元测试
"""
from unittest.mock import MagicMock, patch

import pytest

from app.config import settings


class TestGetEmbeddings:
    """get_embeddings 函数测试"""

    def test_returns_dashscope_embeddings_by_default(self):
        with patch("app.rag.embeddings.settings.EMBEDDING_PROVIDER", "dashscope"), patch(
            "app.rag.embeddings.settings.OPENAI_API_KEY", "sk-test"
        ), patch("app.rag.embeddings.DashScopeEmbeddings") as mock_ds:
            mock_ds.return_value = MagicMock()
            from app.rag.embeddings import get_embeddings

            result = get_embeddings()
            assert result is not None
            mock_ds.assert_called_once()
            call_kwargs = mock_ds.call_args[1]
            assert call_kwargs["model"] == settings.EMBEDDING_MODEL
            assert call_kwargs["dashscope_api_key"] == "sk-test"

    def test_requires_api_key_for_dashscope(self):
        with patch("app.rag.embeddings.settings.EMBEDDING_PROVIDER", "dashscope"), patch(
            "app.rag.embeddings.settings.OPENAI_API_KEY", ""
        ):
            from app.rag.embeddings import get_embeddings

            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                get_embeddings()

    def test_returns_ollama_when_provider_set(self):
        with patch("app.rag.embeddings.settings.EMBEDDING_PROVIDER", "ollama"), patch(
            "app.rag.embeddings.OllamaEmbeddings"
        ) as mock_oe:
            mock_oe.return_value = MagicMock()
            from app.rag.embeddings import get_embeddings

            get_embeddings()
            call_kwargs = mock_oe.call_args[1]
            assert call_kwargs["model"] == settings.EMBEDDING_MODEL
            assert call_kwargs["base_url"] == settings.OLLAMA_BASE_URL

    def test_rejects_unknown_provider(self):
        with patch("app.rag.embeddings.settings.EMBEDDING_PROVIDER", "foo"):
            from app.rag.embeddings import get_embeddings

            with pytest.raises(ValueError, match="EMBEDDING_PROVIDER"):
                get_embeddings()
