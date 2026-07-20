"""
文档加载器
支持 PDF, TXT, CSV, Markdown, DOCX
"""
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    CSVLoader,
    Docx2txtLoader,
)
from langchain_core.documents import Document
from typing import List


LOADER_MAP = {
    "pdf": PyPDFLoader,
    "txt": TextLoader,
    "csv": CSVLoader,
    "md": TextLoader,     # Markdown files can be loaded as text
    "docx": Docx2txtLoader,
}


def load_document(file_path: str, file_type: str) -> List[Document]:
    """
    根据文件类型加载文档

    Args:
        file_path: 文件路径
        file_type: 文件类型 (pdf, txt, csv, md, docx)

    Returns:
        List of LangChain Document objects
    """
    loader_cls = LOADER_MAP.get(file_type.lower())

    if loader_cls is None:
        raise ValueError(f"不支持的文件类型: {file_type}。支持的类型: {list(LOADER_MAP.keys())}")

    # TextLoader needs explicit UTF-8 encoding on Windows
    if file_type == "txt":
        loader = loader_cls(file_path, encoding="utf-8")
    else:
        loader = loader_cls(file_path)
    documents = loader.load()

    return documents
