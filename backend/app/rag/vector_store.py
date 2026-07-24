"""
Chroma 向量库操作
"""
import os
import threading
from langchain_chroma import Chroma
from app.config import settings


# Global vector store instance with thread-safe lock
_vector_store: Chroma | None = None
_vector_store_lock = threading.Lock()
# Chroma's local persistence is not safe for concurrent document writes/deletes
# within this process.  Keep the lock separate from cache initialization.
_document_write_lock = threading.RLock()


def get_vector_store(embeddings=None) -> Chroma:
    """获取或创建 Chroma 向量存储（线程安全）"""
    global _vector_store

    # Fast path: return cached instance without acquiring lock
    if _vector_store is not None:
        return _vector_store

    with _vector_store_lock:
        # Double-check after acquiring lock
        if _vector_store is not None:
            return _vector_store

        persist_dir = settings.CHROMA_PERSIST_DIR
        os.makedirs(persist_dir, exist_ok=True)

        if embeddings is None:
            from app.rag.embeddings import get_embeddings
            embeddings = get_embeddings()

        _vector_store = Chroma(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=persist_dir,
            collection_metadata={"hnsw:space": "cosine"},
        )

    return _vector_store


def reset_vector_store():
    """重置向量存储（用于文档变更后刷新，线程安全）"""
    global _vector_store
    with _vector_store_lock:
        _vector_store = None


def add_documents_to_store(documents, metadatas, ids):
    """添加文档向量到 Chroma"""
    with _document_write_lock:
        store = get_vector_store()
        store.add_documents(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )


def delete_documents_from_store(doc_id: str):
    """从 Chroma 删除指定文档的所有向量"""
    with _document_write_lock:
        store = get_vector_store()
        # Chroma delete by metadata filter
        store._collection.delete(where={"document_id": doc_id})
        # Don't need to call reset_vector_store since Chroma persists changes automatically


def replace_document_texts(
    document_id: str, texts: list[str], metadatas: list[dict], ids: list[str],
    embeddings=None,
):
    """原子替换一个文档的向量，避免新旧 revision 的向量混杂。"""
    with _document_write_lock:
        store = get_vector_store(embeddings)
        store._collection.delete(where={"document_id": document_id})
        store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
