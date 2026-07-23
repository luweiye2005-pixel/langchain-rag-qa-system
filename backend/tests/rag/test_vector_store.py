"""
Chroma 向量库 单元测试
"""
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document


class TestGetVectorStore:
    """get_vector_store 函数测试"""

    def test_creates_chroma_instance(self):
        """创建 Chroma 实例"""
        with patch("app.rag.vector_store.Chroma") as mock_chroma:
            mock_chroma.return_value = MagicMock()
            # 先重置全局变量
            from app.rag.vector_store import reset_vector_store, get_vector_store

            reset_vector_store()
            mock_embeddings = MagicMock()

            store = get_vector_store(mock_embeddings)
            mock_chroma.assert_called_once()
            assert store is not None

    def test_returns_cached_instance(self):
        """第二次调用返回缓存实例（不再创建新对象）"""
        with patch("app.rag.vector_store.Chroma") as mock_chroma:
            mock_chroma.return_value = MagicMock()
            from app.rag.vector_store import reset_vector_store, get_vector_store

            reset_vector_store()
            mock_embeddings = MagicMock()

            store1 = get_vector_store(mock_embeddings)
            store2 = get_vector_store(mock_embeddings)

            # Chroma 只应被调用一次（缓存）
            assert mock_chroma.call_count == 1
            assert store1 is store2


class TestResetVectorStore:
    """reset_vector_store 函数测试"""

    def test_resets_global_instance(self):
        """重置后下次调用会创建新实例"""
        with patch("app.rag.vector_store.Chroma") as mock_chroma:
            from app.rag.vector_store import reset_vector_store, get_vector_store

            # 每次调用 Chroma() 返回不同的 mock
            mock_chroma.side_effect = [MagicMock(), MagicMock()]

            reset_vector_store()
            mock_embeddings = MagicMock()
            store1 = get_vector_store(mock_embeddings)
            assert mock_chroma.call_count == 1

            reset_vector_store()
            store2 = get_vector_store(mock_embeddings)
            assert mock_chroma.call_count == 2
            assert store1 is not store2


class TestAddDocumentsToStore:
    """add_documents_to_store 函数测试"""

    def test_adds_documents_with_metadata(self):
        """添加文档带元数据"""
        with patch("app.rag.vector_store.Chroma") as mock_chroma:
            mock_store = MagicMock()
            mock_chroma.return_value = mock_store
            from app.rag.vector_store import reset_vector_store, add_documents_to_store

            reset_vector_store()
            docs = [Document(page_content="测试内容", metadata={"source": "test.txt"})]
            metadatas = [{"doc_id": "1", "filename": "test.txt"}]
            ids = ["doc1_chunk_0"]

            add_documents_to_store(docs, metadatas, ids)
            mock_store.add_documents.assert_called_once_with(
                documents=docs, metadatas=metadatas, ids=ids
            )
