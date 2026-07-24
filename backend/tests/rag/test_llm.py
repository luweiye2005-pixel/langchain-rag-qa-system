"""
LLM 工厂 单元测试
"""
import pytest
from unittest.mock import patch, MagicMock
from app.config import settings


class TestGetLLM:
    """get_llm 函数测试"""

    def test_returns_chat_tongyi(self):
        """返回 ChatTongyi 实例"""
        with patch("app.rag.llm.settings.OPENAI_API_KEY", "test-api-key"), patch(
            "app.rag.llm.ChatTongyi"
        ) as mock_ct:
            mock_ct.return_value = MagicMock()
            from app.rag.llm import get_llm

            result = get_llm()
            assert result is not None
            mock_ct.assert_called_once()

    def test_uses_config_model(self):
        """使用 settings 中的模型名"""
        with patch("app.rag.llm.settings.OPENAI_API_KEY", "test-api-key"), patch(
            "app.rag.llm.ChatTongyi"
        ) as mock_ct:
            mock_ct.return_value = MagicMock()
            from app.rag.llm import get_llm

            get_llm()
            call_kwargs = mock_ct.call_args[1]
            assert call_kwargs["model"] == settings.TONGYI_MODEL

    def test_uses_config_api_key(self):
        """使用 settings 中的 API key"""
        with patch("app.rag.llm.settings.OPENAI_API_KEY", "test-api-key"), patch(
            "app.rag.llm.ChatTongyi"
        ) as mock_ct:
            mock_ct.return_value = MagicMock()
            from app.rag.llm import get_llm

            get_llm()
            call_kwargs = mock_ct.call_args[1]
            assert call_kwargs["dashscope_api_key"] == settings.OPENAI_API_KEY

    def test_default_temperature_is_low(self):
        """默认 temperature 较低（知识库场景需要准确）"""
        with patch("app.rag.llm.settings.OPENAI_API_KEY", "test-api-key"), patch(
            "app.rag.llm.ChatTongyi"
        ) as mock_ct:
            mock_ct.return_value = MagicMock()
            from app.rag.llm import get_llm

            get_llm()
            call_kwargs = mock_ct.call_args[1]
            assert call_kwargs["temperature"] == 0.1

    def test_streaming_enabled_by_default(self):
        """默认开启 streaming"""
        with patch("app.rag.llm.settings.OPENAI_API_KEY", "test-api-key"), patch(
            "app.rag.llm.ChatTongyi"
        ) as mock_ct:
            mock_ct.return_value = MagicMock()
            from app.rag.llm import get_llm

            get_llm()
            call_kwargs = mock_ct.call_args[1]
            assert call_kwargs["streaming"] is True

    def test_custom_kwargs_override_defaults(self):
        """自定义参数覆盖默认值"""
        with patch("app.rag.llm.settings.OPENAI_API_KEY", "test-api-key"), patch(
            "app.rag.llm.ChatTongyi"
        ) as mock_ct:
            mock_ct.return_value = MagicMock()
            from app.rag.llm import get_llm

            get_llm(temperature=0.5, max_tokens=512)
            call_kwargs = mock_ct.call_args[1]
            assert call_kwargs["temperature"] == 0.5
            assert call_kwargs["max_tokens"] == 512

    def test_requires_api_key(self):
        """未配置 API Key 时给出明确提示。"""
        from app.rag.llm import get_llm

        with patch("app.rag.llm.settings.OPENAI_API_KEY", ""):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                get_llm()
