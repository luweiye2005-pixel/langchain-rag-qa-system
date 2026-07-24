"""
文档处理异步任务
"""
import asyncio
from app.tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from sqlalchemy import select, update
from app.models.document import Document, ensure_document_sqlite_schema
from app.rag.loader import load_document
from app.rag.splitter import split_documents
from app.rag.embeddings import get_embeddings
from app.rag.vector_store import (
    replace_document_texts,
    reset_vector_store,
)
from loguru import logger


async def _claim_document(document_id: str, revision: int | None) -> dict | None:
    """认领待处理文档并立刻释放数据库连接，避免 Embedding 期间锁住 SQLite。"""
    async with AsyncSessionLocal() as db:
        await ensure_document_sqlite_schema(db)
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            logger.info(f"Skipping deleted document task: {document_id}")
            return None

        expected_revision = doc.revision if revision is None else revision
        if doc.revision != expected_revision or doc.status != "pending":
            logger.info(
                f"Skipping stale/duplicate task for {document_id} "
                f"(expected revision {expected_revision}, current {doc.revision}, status {doc.status})"
            )
            return None

        claim = await db.execute(
            update(Document)
            .where(
                Document.id == document_id,
                Document.revision == expected_revision,
                Document.status == "pending",
            )
            .values(status="processing")
        )
        if claim.rowcount != 1:
            logger.info(f"Skipping already-claimed task for document {document_id}")
            return None
        await db.commit()

        return {
            "id": doc.id,
            "filename": doc.filename,
            "file_path": doc.file_path,
            "file_type": doc.file_type,
            "revision": expected_revision,
        }


async def _is_still_processing(document_id: str, expected_revision: int) -> bool:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        return (
            doc is not None
            and doc.revision == expected_revision
            and doc.status == "processing"
        )


async def _mark_completed(document_id: str, expected_revision: int, chunk_count: int) -> bool:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(Document)
            .where(
                Document.id == document_id,
                Document.revision == expected_revision,
                Document.status == "processing",
            )
            .values(status="completed", chunk_count=chunk_count, error_message=None)
        )
        await db.commit()
        return result.rowcount == 1


async def _mark_failed(document_id: str, expected_revision: int, error_message: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Document)
            .where(
                Document.id == document_id,
                Document.revision == expected_revision,
                Document.status == "processing",
            )
            .values(status="failed", error_message=error_message)
        )
        await db.commit()


async def _process_document_impl(document_id: str, revision: int | None = None) -> dict:
    """
    文档处理核心逻辑（供 Celery 任务和直接调用复用）

    流程：
    1. 认领文档并关闭 DB 会话
    2. 加载/切分/Embedding（不占用数据库连接）
    3. 回写 completed/failed
    """
    claimed = await _claim_document(document_id, revision)
    if claimed is None:
        return {"document_id": document_id, "status": "skipped"}

    expected_revision = claimed["revision"]
    filename = claimed["filename"]

    try:
        documents = load_document(claimed["file_path"], claimed["file_type"])
        logger.info(f"Loaded {len(documents)} pages/sections from {filename}")

        chunks = split_documents(documents, chunk_size=800, chunk_overlap=150)
        logger.info(f"Split into {len(chunks)} chunks")
        if not chunks:
            raise ValueError("文档内容为空，无法提取文本")

        embeddings = get_embeddings()
        texts = [chunk.page_content for chunk in chunks]
        metadatas = []
        for i, chunk in enumerate(chunks):
            meta = {
                "document_id": claimed["id"],
                "filename": filename,
                "chunk_index": i,
                "file_type": claimed["file_type"],
            }
            if chunk.metadata:
                meta.update(chunk.metadata)
            metadatas.append(meta)
        ids = [f"{claimed['id']}_chunk_{i}" for i in range(len(chunks))]

        if not await _is_still_processing(document_id, expected_revision):
            logger.info(f"Discarding stale vectors for document {document_id}")
            return {"document_id": document_id, "status": "skipped"}

        # Replace rather than append so retries/reprocessing cannot leave old chunks.
        # 已在后台线程中运行，直接调用同步向量写入即可。
        replace_document_texts(claimed["id"], texts, metadatas, ids, embeddings)

        if not await _mark_completed(document_id, expected_revision, len(chunks)):
            logger.info(f"Document {document_id} changed during embedding; skip complete")
            return {"document_id": document_id, "status": "skipped"}

        reset_vector_store()
        logger.info(f"Document {filename} processed: {len(chunks)} chunks")
        return {
            "document_id": document_id,
            "status": "completed",
            "chunks": len(chunks),
        }

    except Exception as e:
        logger.error(f"Error processing document {filename}: {e}")
        await _mark_failed(document_id, expected_revision, str(e))
        raise


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document(self, document_id: str, revision: int | None = None) -> dict:
    """
    Celery 异步文档处理任务

    Celery task 必须是同步函数，通过以下方式调度内部的 async 逻辑：
    - 如果已有运行中的事件循环 → 在线程池中运行
    - 如果没有事件循环 → 直接 asyncio.run()
    """
    logger.info(f"Processing document: {document_id}")

    async def _run():
        return await _process_document_impl(document_id, revision)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _run())
                return future.result()
        else:
            return asyncio.run(_run())
    except RuntimeError:
        return asyncio.run(_run())


def run_process_in_thread(document_id: str, revision: int | None = None):
    """在独立线程中运行异步文档处理（无 Celery 回退方案）

    在子线程中创建全新的事件循环，避免与主线程的循环冲突。
    用于开发环境或 Celery 不可用时的直接调用。
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_process_document_impl(document_id, revision))
    finally:
        loop.close()


# 保留 process_document_sync 别名以保持向后兼容
process_document_sync = run_process_in_thread
