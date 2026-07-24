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


async def _process_document_impl(document_id: str, revision: int | None = None) -> dict:
    """
    文档处理核心逻辑（供 Celery 任务和直接调用复用）

    流程：
    1. 加载文档文本
    2. 分割为 chunks
    3. 生成 Embeddings 并存储到 Chroma 向量库
    4. 更新数据库状态
    """
    async with AsyncSessionLocal() as db:
        await ensure_document_sqlite_schema(db)
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            logger.info(f"Skipping deleted document task: {document_id}")
            return {"document_id": document_id, "status": "skipped"}

        expected_revision = doc.revision if revision is None else revision
        if doc.revision != expected_revision or doc.status != "pending":
            logger.info(
                f"Skipping stale/duplicate task for {document_id} "
                f"(expected revision {expected_revision}, current {doc.revision}, status {doc.status})"
            )
            return {"document_id": document_id, "status": "skipped"}

        try:
            # Atomically claim this revision. Duplicate Celery deliveries can
            # otherwise both observe ``pending`` and process the same document.
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
                return {"document_id": document_id, "status": "skipped"}
            await db.commit()
            await db.refresh(doc)

            # 1. Load document
            documents = load_document(doc.file_path, doc.file_type)
            logger.info(f"Loaded {len(documents)} pages/sections from {doc.filename}")

            # 2. Split into chunks
            chunks = split_documents(documents, chunk_size=800, chunk_overlap=150)
            logger.info(f"Split into {len(chunks)} chunks")

            if not chunks:
                raise ValueError("文档内容为空，无法提取文本")

            # 3. Generate embeddings and store
            embeddings = get_embeddings()
            texts = [chunk.page_content for chunk in chunks]
            metadatas = []

            for i, chunk in enumerate(chunks):
                meta = {
                    "document_id": doc.id,
                    "filename": doc.filename,
                    "chunk_index": i,
                    "file_type": doc.file_type,
                }
                # Merge existing metadata from loader
                if chunk.metadata:
                    meta.update(chunk.metadata)
                metadatas.append(meta)

            ids = [f"{doc.id}_chunk_{i}" for i in range(len(chunks))]

            # A content update/delete may have happened while embeddings were built.
            # Refresh before mutating Chroma so stale tasks cannot restore old vectors.
            await db.refresh(doc)
            if doc.revision != expected_revision or doc.status != "processing":
                logger.info(f"Discarding stale vectors for document {document_id}")
                return {"document_id": document_id, "status": "skipped"}

            # Replace rather than append so retries/reprocessing cannot leave old chunks.
            replace_document_texts(doc.id, texts, metadatas, ids, embeddings)

            # 4. Update document status
            await db.refresh(doc)
            if doc.revision != expected_revision or doc.status != "processing":
                # This is defensive: the vector operation is serialized, but a newer
                # revision can still be committed between the checks.
                return {"document_id": document_id, "status": "skipped"}
            doc.status = "completed"
            doc.chunk_count = len(chunks)
            await db.commit()

            # Reset vector store cache so new documents are picked up
            reset_vector_store()

            logger.info(f"Document {doc.filename} processed: {len(chunks)} chunks")
            return {
                "document_id": document_id,
                "status": "completed",
                "chunks": len(chunks),
            }

        except Exception as e:
            logger.error(f"Error processing document {doc.filename}: {e}")
            await db.refresh(doc)
            if doc.revision == expected_revision and doc.status == "processing":
                doc.status = "failed"
                doc.error_message = str(e)
                await db.commit()
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
                # 在子线程中创建新的事件循环来运行协程
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
