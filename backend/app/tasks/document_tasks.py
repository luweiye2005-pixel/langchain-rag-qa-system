"""
文档处理异步任务
"""
import asyncio
from app.tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.document import Document
from app.rag.loader import load_document
from app.rag.splitter import split_documents
from app.rag.embeddings import get_embeddings
from app.rag.vector_store import (
    get_vector_store,
    add_documents_to_store,
    reset_vector_store,
)
from loguru import logger


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document(self, document_id: str) -> dict:
    """
    处理文档异步任务：

    1. 加载文档文本
    2. 分割为 chunks
    3. 生成 Embeddings
    4. 存储到 Chroma 向量库
    5. 更新数据库状态
    """
    logger.info(f"Processing document: {document_id}")

    async def _process():
        async with AsyncSessionLocal() as db:
            # Load document record
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if doc is None:
                raise ValueError(f"Document not found: {document_id}")

            try:
                # Update status to processing
                doc.status = "processing"
                await db.commit()

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
                    # Merge existing metadata
                    if chunk.metadata:
                        meta.update(chunk.metadata)
                    metadatas.append(meta)

                ids = [f"{doc.id}_chunk_{i}" for i in range(len(chunks))]

                # 4. Add to vector store
                store = get_vector_store(embeddings)
                store.add_texts(
                    texts=texts,
                    metadatas=metadatas,
                    ids=ids,
                )

                # 5. Update document status
                doc.status = "completed"
                doc.chunk_count = len(chunks)
                await db.commit()

                # Reset vector store cache
                reset_vector_store()

                logger.info(f"Document {doc.filename} processed: {len(chunks)} chunks")
                return {
                    "document_id": document_id,
                    "status": "completed",
                    "chunks": len(chunks),
                }

            except Exception as e:
                logger.error(f"Error processing document {doc.filename}: {e}")
                doc.status = "failed"
                doc.error_message = str(e)
                await db.commit()
                raise

    # Run async function in sync context
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _process())
                return future.result()
        else:
            return asyncio.run(_process())
    except RuntimeError:
        return asyncio.run(_process())


def run_process_in_thread(document_id: str):
    """在独立线程中运行异步文档处理（无 Celery 回退方案）"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(process_document_sync(document_id))
    finally:
        loop.close()


async def process_document_sync(document_id: str) -> dict:
    """
    同步处理文档（无 Celery 回退方案）
    直接在事件循环中运行，不阻塞
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise ValueError(f"Document not found: {document_id}")

        try:
            doc.status = "processing"
            await db.commit()

            # 1. Load
            documents = load_document(doc.file_path, doc.file_type)
            logger.info(f"Loaded {len(documents)} pages/sections from {doc.filename}")

            # 2. Split
            chunks = split_documents(documents, chunk_size=800, chunk_overlap=150)
            logger.info(f"Split into {len(chunks)} chunks")

            if not chunks:
                raise ValueError("文档内容为空，无法提取文本")

            # 3. Embed & store
            embeddings = get_embeddings()
            texts = [chunk.page_content for chunk in chunks]
            metadatas = []
            for i, chunk in enumerate(chunks):
                meta = {
                    "document_id": doc.id, "filename": doc.filename,
                    "chunk_index": i, "file_type": doc.file_type,
                }
                if chunk.metadata:
                    meta.update(chunk.metadata)
                metadatas.append(meta)

            ids = [f"{doc.id}_chunk_{i}" for i in range(len(chunks))]
            store = get_vector_store(embeddings)
            store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

            # 4. Update status
            doc.status = "completed"
            doc.chunk_count = len(chunks)
            await db.commit()
            reset_vector_store()

            logger.info(f"Document {doc.filename} processed: {len(chunks)} chunks")
            return {"document_id": document_id, "status": "completed", "chunks": len(chunks)}

        except Exception as e:
            logger.error(f"Error processing document {doc.filename}: {e}")
            doc.status = "failed"
            doc.error_message = str(e)
            await db.commit()
            raise
