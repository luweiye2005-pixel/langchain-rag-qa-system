"""
Embedding 模型管理 单元测试
"""
import pytest
from unittest.mock import patch, MagicMock
from app.config import settings


class TestGetEmbeddings:
    """get_embeddings 函数测试"""

    def test_returns_ollama_embeddings(self):
        """返回 OllamaEmbeddings 实例"""
        with patch("app.rag.embeddings.OllamaEmbeddings") as mock_oe:
            mock_oe.return_value = MagicMock()
            from app.rag.embeddings import get_embeddings

            result = get_embeddings()
            assert result is not None
            mock_oe.assert_called_once()

    def test_uses_config_model(self):
        """使用 settings 中的模型名"""
        with patch("app.rag.embeddings.OllamaEmbeddings") as mock_oe:
            mock_oe.return_value = MagicMock()
            from app.rag.embeddings import get_embeddings

            get_embeddings()
            call_kwargs = mock_oe.call_args[1]
            assert call_kwargs["model"] == settings.EMBEDDING_MODEL

    def test_uses_config_base_url(self):
        """使用 settings 中的 base_url"""
        with patch("app.rag.embeddings.OllamaEmbeddings") as mock_oe:
            mock_oe.return_value = MagicMock()
            from app.rag.embeddings import get_embeddings

            get_embeddings()
            call_kwargs = mock_oe.call_args[1]
            assert call_kwargs["base_url"] == settings.OLLAMA_BASE_URL
