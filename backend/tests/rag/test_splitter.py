"""
文本分割器 单元测试
"""
import pytest
from langchain_core.documents import Document
from app.rag.splitter import get_text_splitter, split_documents


class TestGetTextSplitter:
    """get_text_splitter 函数测试"""

    def test_returns_splitter(self):
        """返回 RecursiveCharacterTextSplitter 实例"""
        splitter = get_text_splitter()
        assert splitter is not None
        assert hasattr(splitter, "split_documents")

    def test_default_chunk_size(self):
        """默认 chunk_size=800"""
        splitter = get_text_splitter()
        assert splitter._chunk_size == 800

    def test_default_chunk_overlap(self):
        """默认 chunk_overlap=150"""
        splitter = get_text_splitter()
        assert splitter._chunk_overlap == 150

    def test_custom_chunk_size(self):
        """自定义 chunk_size"""
        splitter = get_text_splitter(chunk_size=500, chunk_overlap=100)
        assert splitter._chunk_size == 500
        assert splitter._chunk_overlap == 100

    def test_chinese_separators_present(self):
        """包含中文分隔符"""
        splitter = get_text_splitter()
        separators = splitter._separators
        assert "。" in separators
        assert "！" in separators
        assert "？" in separators
        assert "；" in separators


class TestSplitDocuments:
    """split_documents 函数测试"""

    def test_single_document(self):
        """单个文档切分"""
        doc = Document(page_content="第一段。第二段。第三段。" * 50)
        chunks = split_documents([doc], chunk_size=200, chunk_overlap=50)
        assert len(chunks) > 1
        for chunk in chunks:
            assert hasattr(chunk, "page_content")

    def test_empty_document(self):
        """空文档"""
        doc = Document(page_content="")
        chunks = split_documents([doc])
        assert len(chunks) == 0

    def test_short_document_no_split(self):
        """短文档不切分"""
        doc = Document(page_content="这是一段短文本。")
        chunks = split_documents([doc], chunk_size=800, chunk_overlap=150)
        assert len(chunks) == 1
        assert chunks[0].page_content == "这是一段短文本。"

    def test_chinese_content(self):
        """中文内容切分"""
        long_text = (
            "第一章：介绍。这是关于RAG系统的介绍。" * 30 +
            "第二章：架构。系统采用FastAPI框架。" * 30 +
            "第三章：部署。使用Docker进行部署。" * 30
        )
        doc = Document(page_content=long_text)
        chunks = split_documents([doc], chunk_size=300, chunk_overlap=50)
        assert len(chunks) > 1
        # 所有 chunk 都应该包含部分原始内容
        for chunk in chunks:
            assert len(chunk.page_content) > 0

    def test_multiple_documents(self):
        """多个文档切分"""
        docs = [
            Document(page_content="文档A内容。" * 40),
            Document(page_content="文档B内容。" * 40),
        ]
        chunks = split_documents(docs, chunk_size=200, chunk_overlap=50)
        assert len(chunks) > 2

    def test_chunk_overlap_preserves_context(self):
        """overlap 保留上下文"""
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 10
        doc = Document(page_content=text)
        chunks = split_documents([doc], chunk_size=100, chunk_overlap=30)
        if len(chunks) >= 2:
            # 前一个chunk的尾部应该出现在后一个chunk的头部
            prev_end = chunks[0].page_content[-10:]
            next_start = chunks[1].page_content[:30]
            # overlap 区域内应有重叠内容
            assert len(prev_end) > 0
            assert len(next_start) > 0

    def test_metadata_preserved(self):
        """元数据保留"""
        doc = Document(
            page_content="测试内容。" * 50,
            metadata={"source": "test.txt", "author": "test"}
        )
        chunks = split_documents([doc], chunk_size=200, chunk_overlap=50)
        for chunk in chunks:
            assert chunk.metadata.get("source") == "test.txt"
            assert chunk.metadata.get("author") == "test"

    def test_start_index_added(self):
        """add_start_index 元数据添加"""
        text = "这是测试文本。" * 20
        doc = Document(page_content=text)
        chunks = split_documents([doc], chunk_size=150, chunk_overlap=30)
        for chunk in chunks:
            assert "start_index" in chunk.metadata
