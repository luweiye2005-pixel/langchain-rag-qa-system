"""
Embedding 模型管理 (Ollama bge-m3)
"""
from langchain_community.embeddings import OllamaEmbeddings
from app.config import settings


def get_embeddings() -> OllamaEmbeddings:
    """获取 Ollama Embeddings 实例"""
    return OllamaEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )
