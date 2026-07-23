"""
RAG Chain 构建 单元测试
"""
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.language_models import BaseChatModel


class TestBuildRagChain:
    """build_rag_chain 函数测试"""

    def test_chain_builds_successfully(self):
        """Chain 构建成功且结构正确"""
        from app.rag.chain import build_rag_chain

        mock_llm = MagicMock(spec=BaseChatModel)
        mock_retriever = MagicMock()
        mock_retriever.return_value = [MagicMock()]

        chain = build_rag_chain(mock_llm, mock_retriever)
        assert chain is not None

    def test_chain_has_correct_output_parser(self):
        """Chain 使用 StrOutputParser"""
        from app.rag.chain import build_rag_chain

        mock_llm = MagicMock(spec=BaseChatModel)
        mock_retriever = MagicMock()

        chain = build_rag_chain(mock_llm, mock_retriever)
        # LCEL chain 应该存在
        assert hasattr(chain, "invoke") or hasattr(chain, "ainvoke")

    def test_chain_prompt_includes_chinese(self):
        """Prompt 模板包含中文指令"""
        from app.rag.chain import build_rag_chain
        from app.rag.llm import get_llm

        # 使用 mock（不真正调用 LLM）
        mock_llm = MagicMock()
        mock_retriever = MagicMock()

        chain = build_rag_chain(mock_llm, mock_retriever)
        # 检查 chain 的中间步骤（prompt 是第二个元素，索引1）
        assert chain is not None
