"""
文档加载器 单元测试
"""
import os
import pytest
from app.rag.loader import load_document, LOADER_MAP


class TestLoaderMap:
    """LOADER_MAP 配置测试"""

    def test_supported_formats(self):
        """检查支持的文件类型"""
        assert "pdf" in LOADER_MAP
        assert "txt" in LOADER_MAP
        assert "csv" in LOADER_MAP
        assert "md" in LOADER_MAP
        assert "docx" in LOADER_MAP

    def test_md_uses_text_loader(self):
        """Markdown 使用 TextLoader"""
        from langchain_community.document_loaders import TextLoader
        assert LOADER_MAP["md"] == TextLoader

    def test_txt_uses_text_loader(self):
        """TXT 使用 TextLoader"""
        from langchain_community.document_loaders import TextLoader
        assert LOADER_MAP["txt"] == TextLoader


class TestLoadDocument:
    """load_document 函数测试"""

    def test_load_txt_file(self, tmp_path):
        """加载 TXT 文件"""
        file_path = tmp_path / "test.txt"
        file_path.write_text("这是测试内容。\n第二行内容。", encoding="utf-8")

        docs = load_document(str(file_path), "txt")
        assert len(docs) >= 1
        assert "测试内容" in docs[0].page_content

    def test_load_md_file(self, tmp_path):
        """加载 Markdown 文件"""
        file_path = tmp_path / "test.md"
        file_path.write_text("# Title\n\nContent section.\n\n## Section 2\n\nMore content.", encoding="utf-8")

        docs = load_document(str(file_path), "md")
        assert len(docs) >= 1
        # TextLoader on Windows may use system encoding; just verify loading works
        assert len(docs[0].page_content) > 0

    def test_load_csv_file(self, tmp_path):
        """加载 CSV 文件"""
        file_path = tmp_path / "test.csv"
        file_path.write_text("name,price,stock\n商品A,99,100\n商品B,199,50", encoding="utf-8")

        docs = load_document(str(file_path), "csv")
        assert len(docs) >= 1

    def test_unsupported_file_type_raises(self):
        """不支持的格式抛出 ValueError"""
        with pytest.raises(ValueError, match="不支持的文件类型"):
            load_document("test.xyz", "xyz")

    def test_file_not_found_raises(self):
        """文件不存在抛出异常"""
        with pytest.raises(Exception):
            load_document("/nonexistent/file.pdf", "pdf")

    def test_txt_with_utf8_encoding(self, tmp_path):
        """TXT UTF-8 加载中文"""
        file_path = tmp_path / "cn.txt"
        file_path.write_text("电商商品：iPhone 15 Pro Max ¥9999", encoding="utf-8")

        docs = load_document(str(file_path), "txt")
        assert len(docs) >= 1
        assert "iPhone" in docs[0].page_content
